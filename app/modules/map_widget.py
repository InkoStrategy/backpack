# -*- coding: utf-8 -*-
"""
app/modules/map_widget.py
Leaflet + milsymbol map widget backed by QWebEngineView.
Python ↔ JavaScript communication via QWebChannel.
"""

import json
import os

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from app.config import TEMPLATES_DIR


class MapBridge(QObject):
    """Exposes Python slots/signals to the Leaflet JavaScript environment."""

    # Signals emitted when JS calls the corresponding slot
    mapClickedSignal = pyqtSignal(float, float)
    symbolMovedSignal = pyqtSignal(str, float, float)
    symbolSelectedSignal = pyqtSignal(str)

    # ── Slots called from JavaScript ──────────────────────────────────────────

    @pyqtSlot(float, float)
    def onMapClicked(self, lat: float, lng: float):
        self.mapClickedSignal.emit(lat, lng)

    @pyqtSlot(str, float, float)
    def onSymbolMoved(self, symbol_id: str, lat: float, lng: float):
        self.symbolMovedSignal.emit(symbol_id, lat, lng)

    @pyqtSlot(str)
    def onSymbolSelected(self, symbol_id: str):
        self.symbolSelectedSignal.emit(symbol_id)


class MapWidget(QWidget):
    """
    Leaflet-based interactive tactical map widget.

    Signals
    -------
    map_clicked(lat, lng)        – user clicked an empty area of the map
    symbol_moved(id, lat, lng)   – user dragged a symbol to a new position
    symbol_selected(id)          – user clicked on a symbol
    """

    map_clicked = pyqtSignal(float, float)
    symbol_moved = pyqtSignal(str, float, float)
    symbol_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._symbols: dict[str, dict] = {}
        self._counter = 0
        self._init_ui()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.view = QWebEngineView()
        layout.addWidget(self.view)

        # WebChannel bridge
        self.channel = QWebChannel()
        self.bridge = MapBridge()
        self.channel.registerObject("pyBridge", self.bridge)
        self.view.page().setWebChannel(self.channel)

        # Forward bridge signals
        self.bridge.mapClickedSignal.connect(self.map_clicked)
        self.bridge.symbolMovedSignal.connect(self._on_symbol_moved)
        self.bridge.symbolSelectedSignal.connect(self.symbol_selected)

        # Load map template
        map_path = os.path.join(TEMPLATES_DIR, "map.html")
        if os.path.exists(map_path):
            self.view.setUrl(QUrl.fromLocalFile(map_path))
        else:
            self.view.setHtml(
                "<body style='background:#1a1a2e;color:#fff;font-family:sans-serif;"
                "display:flex;align-items:center;justify-content:center;height:100vh'>"
                "<p>Помилка: файл карти не знайдено.<br>"
                f"Очікується: {map_path}</p></body>"
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def add_symbol(self, sidc: str, lat: float, lng: float,
                   label: str = "", echelon: str = "", notes: str = "") -> str:
        """Place a NATO symbol on the map. Returns the internal symbol id."""
        self._counter += 1
        symbol_id = f"sym_{self._counter}"
        data = {
            "id": symbol_id,
            "sidc": sidc,
            "lat": lat,
            "lng": lng,
            "label": label,
            "echelon": echelon,
            "notes": notes,
        }
        self._symbols[symbol_id] = data
        js = f"if(typeof addSymbol === 'function') addSymbol({json.dumps(data)});"
        self.view.page().runJavaScript(js)
        return symbol_id

    def remove_symbol(self, symbol_id: str):
        """Remove a symbol from the map."""
        self._symbols.pop(symbol_id, None)
        self.view.page().runJavaScript(
            f"if(typeof removeSymbol === 'function') removeSymbol({json.dumps(symbol_id)});"
        )

    def clear_symbols(self):
        """Remove all symbols from the map."""
        self._symbols.clear()
        self._counter = 0
        self.view.page().runJavaScript(
            "if(typeof clearAllSymbols === 'function') clearAllSymbols();"
        )

    def set_view(self, lat: float, lng: float, zoom: int = 12):
        """Pan and zoom the map to (lat, lng)."""
        self.view.page().runJavaScript(
            f"if(typeof map !== 'undefined') map.setView([{lat}, {lng}], {zoom});"
        )

    def fit_symbols(self):
        """Fit the map view to show all placed symbols."""
        self.view.page().runJavaScript(
            "if(typeof fitAllSymbols === 'function') fitAllSymbols();"
        )

    def set_theme(self, theme: str):
        """Switch tile layer theme: 'dark' | 'light' | 'topo'."""
        self.view.page().runJavaScript(
            f"if(typeof setMapTheme === 'function') setMapTheme({json.dumps(theme)});"
        )

    def get_symbols(self) -> dict:
        """Return a copy of the current symbols dict."""
        return dict(self._symbols)

    def screenshot(self, callback):
        """Capture the map as a QImage and pass it to callback(QImage)."""
        self.view.grab()  # basic grab; for async use QWebEnginePage.toHtml

    # ── Internal slots ────────────────────────────────────────────────────────

    def _on_symbol_moved(self, symbol_id: str, lat: float, lng: float):
        if symbol_id in self._symbols:
            self._symbols[symbol_id]["lat"] = lat
            self._symbols[symbol_id]["lng"] = lng
        self.symbol_moved.emit(symbol_id, lat, lng)
