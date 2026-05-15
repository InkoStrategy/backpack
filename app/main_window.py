# -*- coding: utf-8 -*-
"""
app/main_window.py
Main application window for Тактична ГІС.
"""

import os
import json

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTextEdit, QPushButton, QToolBar, QStatusBar, QLabel,
    QFileDialog, QMessageBox, QFrame, QGroupBox, QListWidget,
    QListWidgetItem, QProgressBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QFont


# ─── Background parser thread ─────────────────────────────────────────────────

class ParserThread(QThread):
    """Run CombatOrderParser.parse() in a background thread."""

    result_ready = pyqtSignal(object)   # ParseResult
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, text: str, parser):
        super().__init__()
        self.text = text
        self.parser = parser

    def run(self):
        try:
            self.progress.emit(20)
            result = self.parser.parse(self.text)
            self.progress.emit(100)
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ─── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()

        # ── Import config ──────────────────────────────────────────────────
        from app.config import (
            APP_NAME, APP_VERSION,
            WINDOW_WIDTH, WINDOW_HEIGHT,
            TEXT_PANEL_WIDTH, MAP_PANEL_WIDTH,
            TOOLBAR_HEIGHT, STATUSBAR_HEIGHT,
            FONT_FAMILY, FONT_SIZE_BASE,
            DB_PATH, DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM,
            ICON_SIZE, STYLES_DIR,
        )

        # ── Subsystems ─────────────────────────────────────────────────────
        from app.modules.database import Database
        from app.modules.parser import CombatOrderParser
        from app.modules.symbols import NATOSymbolManager
        from app.modules.exporter import MapExporter

        self.db = Database(DB_PATH)
        self.db.initialize()
        self.parser = CombatOrderParser()
        self.symbol_manager = NATOSymbolManager(self.db)
        self.exporter = MapExporter()

        self._current_theme: str = "dark"
        self._current_mission_id = None
        self._parse_result = None
        self._parser_thread: ParserThread | None = None

        # ── Window geometry ────────────────────────────────────────────────
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(1024, 640)

        screen = self.screen().geometry()
        self.move(
            max(0, (screen.width() - WINDOW_WIDTH) // 2),
            max(0, (screen.height() - WINDOW_HEIGHT) // 2),
        )

        # ── Theme ──────────────────────────────────────────────────────────
        self._load_theme("dark")

        # ── Build UI ───────────────────────────────────────────────────────
        self._icon_size = ICON_SIZE
        self._build_toolbar(TOOLBAR_HEIGHT, ICON_SIZE)
        self._build_central_widget(TEXT_PANEL_WIDTH, MAP_PANEL_WIDTH, FONT_FAMILY, FONT_SIZE_BASE)
        self._build_statusbar(STATUSBAR_HEIGHT)

        # Defer initial map view so WebEngine has time to load
        QTimer.singleShot(800, lambda: self.map_widget.set_view(DEFAULT_LAT, DEFAULT_LON, DEFAULT_ZOOM))

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _load_theme(self, theme_name: str):
        from app.config import STYLES_DIR
        qss_path = os.path.join(STYLES_DIR, f"{theme_name}.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as fh:
                self.setStyleSheet(fh.read())
        self._current_theme = theme_name

    # ── Toolbar ────────────────────────────────────────────────────────────────

    def _build_toolbar(self, height: int, icon_size: int):
        tb = self.addToolBar("Головна панель")
        tb.setMovable(False)
        tb.setIconSize(QSize(icon_size, icon_size))
        tb.setFixedHeight(height)
        tb.setObjectName("mainToolBar")

        def act(label: str, tip: str, shortcut: str = "") -> QAction:
            a = QAction(label, self)
            a.setToolTip(tip)
            if shortcut:
                a.setShortcut(shortcut)
            return a

        # Open file
        a_open = act("📂 Відкрити БР", "Завантажити файл бойового розпорядження")
        a_open.triggered.connect(self._load_order_file)
        tb.addAction(a_open)

        # Parse
        a_parse = act("⚡ Аналізувати", "Розпізнати координати та підрозділи", "Ctrl+Return")
        a_parse.triggered.connect(self._parse_order)
        tb.addAction(a_parse)

        tb.addSeparator()

        # Clear map
        a_clear = act("🗑 Очистити карту", "Видалити всі символи з карти")
        a_clear.triggered.connect(self._clear_map)
        tb.addAction(a_clear)

        # Fit symbols
        a_fit = act("⊕ По символах", "Показати всі символи на карті")
        a_fit.triggered.connect(lambda: self.map_widget.fit_symbols())
        tb.addAction(a_fit)

        tb.addSeparator()

        # Export PNG
        a_png = act("🖼 PNG", "Зберегти карту як PNG зображення")
        a_png.triggered.connect(self._export_png)
        tb.addAction(a_png)

        # Export KML
        a_kml = act("📍 KML", "Експортувати символи у KML файл")
        a_kml.triggered.connect(self._export_kml)
        tb.addAction(a_kml)

        # Export PDF
        a_pdf = act("📄 PDF", "Зберегти звіт у PDF")
        a_pdf.triggered.connect(self._export_pdf)
        tb.addAction(a_pdf)

        tb.addSeparator()

        # Theme toggle
        self.act_theme = act("☀ День", "Перемкнути тему (день/ніч)", "Ctrl+T")
        self.act_theme.triggered.connect(self._toggle_theme)
        tb.addAction(self.act_theme)

    # ── Central widget ─────────────────────────────────────────────────────────

    def _build_central_widget(self, text_width: int, map_width: int,
                               font_family: str, font_size: int):
        from app.modules.map_widget import MapWidget

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(3)
        root_layout.addWidget(self.splitter)

        # Left panel
        left = self._build_left_panel(font_family, font_size)
        self.splitter.addWidget(left)

        # Map
        self.map_widget = MapWidget()
        self.splitter.addWidget(self.map_widget)

        # Golden-ratio proportions
        self.splitter.setSizes([text_width, map_width])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        # Connect map signals
        self.map_widget.map_clicked.connect(self._on_map_clicked)

    # ── Left panel ─────────────────────────────────────────────────────────────

    def _build_left_panel(self, font_family: str, font_size: int) -> QFrame:
        from app.config import BUTTON_HEIGHT

        panel = QFrame()
        panel.setObjectName("leftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 4, 8)
        layout.setSpacing(8)

        # Header label
        header = QLabel("БОЙОВЕ РОЗПОРЯДЖЕННЯ")
        header.setObjectName("panelHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Text editor
        self.order_text = QTextEdit()
        self.order_text.setObjectName("orderText")
        self.order_text.setPlaceholderText(
            "Вставте текст бойового розпорядження або відкрийте файл...\n\n"
            "Приклад:\n"
            "1-й мехбатальйон наступає на рубіж квадрат 343567.\n"
            "Противник в районі кв. 356589.\n"
            "Розмежувальна лінія: 334556 – 345678.\n"
            "Напрямок головного удару: 334556 – 367589.\n"
            "Час початку: Ч+2 або 06:00."
        )
        self.order_text.setFont(QFont(font_family, font_size))
        layout.addWidget(self.order_text, stretch=5)

        # Main action button
        btn_parse = QPushButton("⚡  АНАЛІЗУВАТИ ТЕКСТ  (Ctrl+Enter)")
        btn_parse.setObjectName("primaryButton")
        btn_parse.setFixedHeight(BUTTON_HEIGHT * 2)
        btn_parse.clicked.connect(self._parse_order)
        layout.addWidget(btn_parse)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Results group
        results_group = QGroupBox("Результати аналізу")
        results_group.setObjectName("resultsGroup")
        rg_layout = QVBoxLayout(results_group)
        rg_layout.setContentsMargins(4, 8, 4, 4)
        rg_layout.setSpacing(4)

        self.results_label = QLabel("Очікування аналізу…")
        self.results_label.setObjectName("resultsLabel")
        self.results_label.setWordWrap(True)
        rg_layout.addWidget(self.results_label)

        self.symbols_list = QListWidget()
        self.symbols_list.setObjectName("symbolsList")
        self.symbols_list.itemDoubleClicked.connect(self._on_symbol_list_dblclick)
        rg_layout.addWidget(self.symbols_list)

        btn_apply = QPushButton("🗺  Нанести на карту")
        btn_apply.setObjectName("secondaryButton")
        btn_apply.setFixedHeight(BUTTON_HEIGHT)
        btn_apply.clicked.connect(self._apply_to_map)
        rg_layout.addWidget(btn_apply)

        layout.addWidget(results_group, stretch=3)

        return panel

    # ── Status bar ─────────────────────────────────────────────────────────────

    def _build_statusbar(self, height: int):
        sb = QStatusBar()
        sb.setFixedHeight(height)
        self.setStatusBar(sb)

        self.status_label = QLabel("Готово")
        sb.addWidget(self.status_label)

        sb.addPermanentWidget(QLabel("|"))

        self.coord_label = QLabel("Координати: —")
        sb.addPermanentWidget(self.coord_label)

        sb.addPermanentWidget(QLabel("|"))

        self.symbol_count_label = QLabel("Символів: 0")
        sb.addPermanentWidget(self.symbol_count_label)

    # ── File operations ────────────────────────────────────────────────────────

    def _load_order_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Відкрити бойове розпорядження", "",
            "Текстові файли (*.txt *.rtf);;Всі файли (*)",
        )
        if not path:
            return
        for encoding in ("utf-8", "cp1251", "latin-1"):
            try:
                with open(path, "r", encoding=encoding) as fh:
                    self.order_text.setPlainText(fh.read())
                self.status_label.setText(f"Завантажено: {os.path.basename(path)}")
                return
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                QMessageBox.critical(self, "Помилка", f"Не вдалося відкрити файл:\n{exc}")
                return
        QMessageBox.critical(self, "Помилка", "Не вдалося визначити кодування файлу.")

    # ── Parsing ────────────────────────────────────────────────────────────────

    def _parse_order(self):
        text = self.order_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Попередження", "Введіть текст бойового розпорядження.")
            return

        # Prevent double-click launching two threads
        if self._parser_thread and self._parser_thread.isRunning():
            return

        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.status_label.setText("Аналіз тексту…")
        self.symbols_list.clear()
        self.results_label.setText("Обробка…")

        self._parser_thread = ParserThread(text, self.parser)
        self._parser_thread.result_ready.connect(self._on_parse_complete)
        self._parser_thread.error.connect(self._on_parse_error)
        self._parser_thread.progress.connect(self.progress_bar.setValue)
        self._parser_thread.start()

    def _on_parse_complete(self, result):
        self._parse_result = result
        self.progress_bar.hide()

        summary = result.summary()
        self.results_label.setText(summary)
        self.status_label.setText(f"Аналіз завершено. {summary}")

        # Populate list widget
        self.symbols_list.clear()

        for unit in result.units:
            icon = "🔵" if unit.get("affiliation") == "F" else "🔴"
            item = QListWidgetItem(f"{icon} {unit.get('name', 'Підрозділ')}")
            item.setData(Qt.ItemDataRole.UserRole, unit)
            self.symbols_list.addItem(item)

        for coord in result.coordinates:
            ctx = coord.get("context", coord.get("raw", ""))
            item = QListWidgetItem(f"📍 {ctx[:55]}")
            item.setData(Qt.ItemDataRole.UserRole, coord)
            self.symbols_list.addItem(item)

        for boundary in result.boundaries:
            item = QListWidgetItem(f"━━ {boundary.get('name', 'Розмежувальна лінія')}")
            item.setData(Qt.ItemDataRole.UserRole, boundary)
            self.symbols_list.addItem(item)

        for attack in result.attack_directions:
            item = QListWidgetItem(f"➡ {attack.get('name', 'Напрямок удару')}")
            item.setData(Qt.ItemDataRole.UserRole, attack)
            self.symbols_list.addItem(item)

    def _on_parse_error(self, error: str):
        self.progress_bar.hide()
        self.status_label.setText(f"Помилка аналізу: {error}")
        QMessageBox.critical(self, "Помилка аналізу", error)

    # ── Apply to map ───────────────────────────────────────────────────────────

    def _apply_to_map(self):
        if not self._parse_result:
            QMessageBox.information(self, "Інформація",
                                    "Спочатку виконайте аналіз тексту.")
            return

        placed_coords: set = set()
        count = 0

        # Units with known coordinates
        for unit in self._parse_result.units:
            coord = unit.get("coord")
            if not coord:
                continue
            lat, lng = coord
            key = (round(lat, 5), round(lng, 5))
            if key in placed_coords:
                continue
            placed_coords.add(key)

            affil = unit.get("affiliation", "U")
            sidc = self.symbol_manager.get_sidc_for_unit(unit.get("name", ""), affil)
            echelon = unit.get("echelon", "")
            self.map_widget.add_symbol(sidc, lat, lng, unit.get("name", ""), echelon)
            count += 1

        # Standalone coordinates
        for coord_data in self._parse_result.coordinates:
            lat = coord_data.get("lat")
            lng = coord_data.get("lng")
            if lat is None or lng is None:
                continue
            key = (round(lat, 5), round(lng, 5))
            if key in placed_coords:
                continue
            placed_coords.add(key)

            affil = coord_data.get("affiliation", "U")
            sidc_map = {
                "F": "10031000141211000000",
                "H": "10061000141211000000",
                "N": "10041000141211000000",
                "U": "10011000141211000000",
            }
            sidc = sidc_map.get(affil, "10011000141211000000")
            label = coord_data.get("context", coord_data.get("raw", ""))[:40]
            self.map_widget.add_symbol(sidc, lat, lng, label)
            count += 1

        if count > 0:
            self.map_widget.fit_symbols()
            self.symbol_count_label.setText(f"Символів: {count}")
            self.status_label.setText(f"Нанесено {count} символів на карту")
        else:
            QMessageBox.information(
                self, "Результат",
                "Не вдалося визначити координати для нанесення.\n"
                "Перевірте формат координат у тексті.\n\n"
                "Підтримувані формати:\n"
                "• Шестизначні військові координати: 343567\n"
                "• Восьмизначні: 34345678\n"
                "• Координати WGS-84: 49.1234, 32.5678",
            )

    # ── Map ────────────────────────────────────────────────────────────────────

    def _clear_map(self):
        self.map_widget.clear_symbols()
        self.symbol_count_label.setText("Символів: 0")
        self.status_label.setText("Карту очищено")

    def _on_map_clicked(self, lat: float, lng: float):
        self.coord_label.setText(f"Координати: {lat:.5f}, {lng:.5f}")

    def _on_symbol_list_dblclick(self, item: QListWidgetItem):
        """Double-click on a list item → zoom map to that position."""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        lat = None
        lng = None

        # Unit entry
        if "coord" in data and data["coord"]:
            lat, lng = data["coord"]

        # Coordinate entry
        elif "lat" in data and "lng" in data:
            lat = data["lat"]
            lng = data["lng"]

        # Boundary / attack direction — go to first point
        elif "points" in data and data["points"]:
            pt = data["points"][0]
            lat, lng = (pt[0], pt[1]) if isinstance(pt, (list, tuple)) else (pt.get("lat"), pt.get("lng"))

        if lat is not None and lng is not None:
            self.map_widget.set_view(lat, lng, 14)

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        if self._current_theme == "dark":
            self._load_theme("light")
            self.act_theme.setText("🌙 Ніч")
            self.map_widget.set_theme("light")
        else:
            self._load_theme("dark")
            self.act_theme.setText("☀ День")
            self.map_widget.set_theme("dark")

    # ── Export ─────────────────────────────────────────────────────────────────

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти карту як PNG", "tactical_map.png",
            "PNG зображення (*.png)",
        )
        if path:
            ok = self.exporter.export_png(self.map_widget, path)
            if ok:
                self.status_label.setText(f"PNG збережено: {path}")
            else:
                QMessageBox.warning(self, "Попередження", "Не вдалося зберегти PNG.")

    def _export_kml(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Експорт у KML", "tactical_symbols.kml",
            "KML файл (*.kml)",
        )
        if path:
            symbols = list(self.map_widget.get_symbols().values())
            ok = self.exporter.export_kml(symbols, path)
            if ok:
                self.status_label.setText(f"KML збережено: {path} ({len(symbols)} символів)")
            else:
                QMessageBox.warning(self, "Попередження", "Не вдалося зберегти KML.")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти звіт PDF", "tactical_report.pdf",
            "PDF файл (*.pdf)",
        )
        if path:
            symbols = list(self.map_widget.get_symbols().values())
            ok = self.exporter.export_pdf(self.map_widget, symbols, path)
            if ok:
                self.status_label.setText(f"PDF збережено: {path}")
            else:
                QMessageBox.warning(self, "Попередження", "Не вдалося зберегти PDF.")

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        if self._parser_thread and self._parser_thread.isRunning():
            self._parser_thread.quit()
            self._parser_thread.wait(2000)
        try:
            self.db.close()
        except Exception:
            pass
        event.accept()
