# -*- coding: utf-8 -*-
"""
app/config.py
Global configuration constants for Тактична ГІС.
All dimensions follow the golden ratio (PHI = 1.6180339887).
"""

import os

# ─── Golden Ratio ────────────────────────────────────────────────────────────
PHI = 1.6180339887

# ─── Application metadata ────────────────────────────────────────────────────
APP_NAME = "Тактична ГІС"
APP_VERSION = "1.0.0"

# ─── Window dimensions (golden ratio: 1440 / PHI ≈ 890) ─────────────────────
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 890

# Panel widths split by golden ratio: total * 1/(1+PHI) and total * PHI/(1+PHI)
TEXT_PANEL_WIDTH = 550   # 1440 * 1/(1+PHI) ≈ 550
MAP_PANEL_WIDTH = 890    # 1440 * PHI/(1+PHI) ≈ 890

# Toolbar / status bar
TOOLBAR_HEIGHT = 55
STATUSBAR_HEIGHT = 34    # 55 / PHI ≈ 34
BUTTON_HEIGHT = 34

# Icon size inside toolbar
ICON_SIZE = 20

# ─── Typography ──────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"
FONT_SIZE_BASE = 13
FONT_SIZE_LARGE = 21     # 13 * PHI ≈ 21
FONT_SIZE_SMALL = 8

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(BASE_DIR, "resources")
STYLES_DIR = os.path.join(RESOURCES_DIR, "styles")
TEMPLATES_DIR = os.path.join(RESOURCES_DIR, "templates")
DATA_DIR = os.path.join(BASE_DIR, "data")
TILES_DIR = os.path.join(DATA_DIR, "tiles")
DB_PATH = os.path.join(DATA_DIR, "tacgis.db")

# ─── Map defaults (centre of Ukraine) ────────────────────────────────────────
DEFAULT_LAT = 49.0
DEFAULT_LON = 31.0
DEFAULT_ZOOM = 8

# ─── NATO Affiliation colours (APP-6D) ───────────────────────────────────────
COLOR_FRIENDLY = "#005CE6"   # NATO Blue
COLOR_HOSTILE = "#FF0000"    # NATO Red
COLOR_NEUTRAL = "#00A651"    # NATO Green
COLOR_UNKNOWN = "#FFFF00"    # NATO Yellow

# ─── Echelons (Ukrainian name → APP-6 code) ──────────────────────────────────
ECHELONS = {
    "відділення":   "11",   # Squad
    "взвод":        "13",   # Platoon
    "рота":         "14",   # Company
    "батальйон":    "15",   # Battalion
    "полк":         "16",   # Regiment
    "бригада":      "17",   # Brigade
    "дивізія":      "18",   # Division
    "корпус":       "19",   # Corps
    "армія":        "20",   # Army
    # abbreviations
    "мпв":          "13",
    "мпр":          "14",
    "мпб":          "15",
    "тр":           "14",
    "тб":           "15",
    "тбр":          "17",
    "дшб":          "15",
    "пдб":          "15",
    "арт д-н":      "15",
    "д-н":          "15",
}

# ─── Unit type keywords for parser (Ukrainian → APP-6 entity type hint) ──────
UNIT_TYPES = {
    # Infantry / Mechanised
    "піхота":           "infantry",
    "мех":              "mechanized_infantry",
    "мп":               "mechanized_infantry",
    "мпб":              "mechanized_infantry",
    "мпр":              "mechanized_infantry",
    "мотопіхот":        "mechanized_infantry",
    # Armour
    "танк":             "armor",
    "тб":               "armor",
    "тр":               "armor",
    "тбр":              "armor",
    "бронетанков":      "armor",
    # Artillery
    "артилері":         "artillery",
    "арт":              "artillery",
    "гаубиц":           "artillery",
    "гармат":           "artillery",
    "реактивн":         "artillery",
    # Air Defence
    "ппо":              "air_defense",
    "зенітн":           "air_defense",
    "зрк":              "air_defense",
    # Engineer
    "інженерн":         "engineer",
    "сапер":            "engineer",
    "понтон":           "engineer",
    # Logistics
    "тил":              "logistics",
    "логістик":         "logistics",
    "мто":              "logistics",
    # Command
    "кп":               "command",
    "командн":          "command",
    "штаб":             "command",
    # Recon
    "розвідк":          "recon",
    "рвб":              "recon",
    # Airborne / Airmobile
    "дшб":              "airborne",
    "пдб":              "airborne",
    "десантн":          "airborne",
}
