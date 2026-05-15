# -*- coding: utf-8 -*-
"""
app/modules/exporter.py
Export functionality for Тактична ГІС.
Supports PNG screenshot, KML export, and basic PDF generation.
"""

import os
import json
from datetime import datetime


class MapExporter:
    """Handles exporting the map and placed symbols to various formats."""

    # ── PNG export ────────────────────────────────────────────────────────────

    def export_png(self, map_widget, filepath: str, dpi: int = 300) -> bool:
        """
        Capture the map widget as a PNG image.
        Uses QWebEngineView's grab() method for a quick screenshot.
        Returns True on success, False on failure.
        """
        try:
            from PyQt6.QtCore import QSize
            from PyQt6.QtGui import QPixmap

            # Grab the entire web view as a pixmap
            pixmap = map_widget.view.grab()
            if pixmap.isNull():
                return False

            # Scale for higher DPI if requested (screen is typically 96 dpi)
            if dpi > 96:
                scale = dpi / 96.0
                new_size = QSize(
                    int(pixmap.width() * scale),
                    int(pixmap.height() * scale),
                )
                pixmap = pixmap.scaled(
                    new_size,
                    __import__('PyQt6.QtCore', fromlist=['Qt']).Qt.AspectRatioMode.KeepAspectRatio,
                    __import__('PyQt6.QtCore', fromlist=['Qt']).Qt.TransformationMode.SmoothTransformation,
                )

            saved = pixmap.save(filepath, "PNG")
            return saved
        except Exception as exc:
            print(f"[Exporter] PNG export error: {exc}")
            return False

    # ── KML export ────────────────────────────────────────────────────────────

    def export_kml(self, placed_symbols: list, filepath: str) -> bool:
        """
        Export a list of placed symbol dicts to a KML file using simplekml.
        Each symbol becomes a Placemark with name, coordinates, and description.
        Returns True on success.
        """
        try:
            import simplekml

            kml = simplekml.Kml(name="Тактична ГІС — Місія")
            kml.document.description = (
                f"Експортовано: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
            )

            # Style folders by affiliation
            friendly_folder = kml.newfolder(name="Свої підрозділи")
            hostile_folder = kml.newfolder(name="Противник")
            other_folder = kml.newfolder(name="Інші")

            for sym in placed_symbols:
                lat = sym.get("lat")
                lng = sym.get("lng")
                if lat is None or lng is None:
                    continue

                label = sym.get("label") or sym.get("sidc", "Symbol")
                sidc = sym.get("sidc", "")
                notes = sym.get("notes", "")
                affiliation = sym.get("affiliation", "U")

                # Infer affiliation from SIDC if not set
                if not affiliation or affiliation == "U":
                    std_id = int(sidc[2:4]) if len(sidc) >= 4 and sidc[2:4].isdigit() else 0
                    if std_id == 3:
                        affiliation = "F"
                    elif std_id == 6:
                        affiliation = "H"

                # Select folder and icon color
                if affiliation == "F":
                    folder = friendly_folder
                    icon_color = simplekml.Color.blue
                elif affiliation == "H":
                    folder = hostile_folder
                    icon_color = simplekml.Color.red
                else:
                    folder = other_folder
                    icon_color = simplekml.Color.yellow

                pnt = folder.newpoint(name=label, coords=[(lng, lat)])
                pnt.description = (
                    f"SIDC: {sidc}\n"
                    f"Ешелон: {sym.get('echelon', '')}\n"
                    f"Нотатки: {notes}"
                )

                # Style the placemark
                pnt.style.iconstyle.color = icon_color
                pnt.style.iconstyle.scale = 1.2
                pnt.style.iconstyle.icon.href = (
                    "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
                )
                pnt.style.labelstyle.color = simplekml.Color.white
                pnt.style.labelstyle.scale = 0.8

            kml.save(filepath)
            return True
        except Exception as exc:
            print(f"[Exporter] KML export error: {exc}")
            return False

    # ── PDF export ────────────────────────────────────────────────────────────

    def export_pdf(self, map_widget, placed_symbols: list, filepath: str) -> bool:
        """
        Generate a basic PDF report containing a map screenshot and symbol table.
        Uses reportlab for PDF generation.
        Returns True on success.
        """
        try:
            import tempfile
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import cm
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Image, Paragraph, Spacer, Table, TableStyle
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            # Save map screenshot to temp file
            tmp_png = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_png.close()
            self.export_png(map_widget, tmp_png.name, dpi=150)

            doc = SimpleDocTemplate(
                filepath,
                pagesize=landscape(A4),
                rightMargin=1.5 * cm,
                leftMargin=1.5 * cm,
                topMargin=1.5 * cm,
                bottomMargin=1.5 * cm,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "TacTitle",
                parent=styles["Title"],
                fontSize=16,
                textColor=colors.HexColor("#003399"),
                spaceAfter=0.3 * cm,
            )
            normal_style = styles["Normal"]
            normal_style.fontSize = 9

            story = []

            # Title
            story.append(Paragraph("Тактична карта — звіт місії", title_style))
            story.append(Paragraph(
                f"Дата: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')} | "
                f"Символів: {len(placed_symbols)}",
                normal_style,
            ))
            story.append(Spacer(1, 0.4 * cm))

            # Map image (use most of the page width)
            page_w = landscape(A4)[0] - 3 * cm
            if os.path.exists(tmp_png.name) and os.path.getsize(tmp_png.name) > 0:
                img = Image(tmp_png.name, width=page_w * 0.65, height=page_w * 0.65 * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.4 * cm))

            # Symbols table
            if placed_symbols:
                story.append(Paragraph("Перелік нанесених символів", styles["Heading2"]))
                story.append(Spacer(1, 0.2 * cm))

                header = ["#", "Позначення", "SIDC", "Шир.", "Довг.", "Ешелон", "Нотатки"]
                table_data = [header]
                for i, sym in enumerate(placed_symbols, 1):
                    table_data.append([
                        str(i),
                        sym.get("label", "")[:30],
                        sym.get("sidc", ""),
                        f"{sym.get('lat', 0):.5f}",
                        f"{sym.get('lng', 0):.5f}",
                        sym.get("echelon", ""),
                        sym.get("notes", "")[:40],
                    ])

                col_widths = [0.8*cm, 4*cm, 4.5*cm, 2.5*cm, 2.5*cm, 2*cm, 5*cm]
                tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003399")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.HexColor("#f0f4ff"), colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#99aacc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]))
                story.append(tbl)

            doc.build(story)

            # Cleanup temp file
            try:
                os.unlink(tmp_png.name)
            except OSError:
                pass

            return True
        except Exception as exc:
            print(f"[Exporter] PDF export error: {exc}")
            return False
