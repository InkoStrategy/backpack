#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тактична ГІС - Military GIS Desktop Application
Entry point

Usage:
    python main.py
"""

import sys
import os

# Ensure the app package is importable from any working directory
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# PyQt6 WebEngine must be initialised before QApplication on some platforms
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox")


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("Тактична ГІС")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TacGIS")

    # Default font
    font = QFont("Segoe UI", 13)
    app.setFont(font)

    # High-DPI support
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    from app.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
