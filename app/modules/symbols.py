# -*- coding: utf-8 -*-
"""
app/modules/symbols.py
NATO Symbol manager for Тактична ГІС.
Handles SIDC generation, echelon encoding, and milsymbol.js option building.
"""

import re
from app.config import ECHELONS, UNIT_TYPES, COLOR_FRIENDLY, COLOR_HOSTILE, COLOR_NEUTRAL, COLOR_UNKNOWN


# APP-6D SIDC affiliation codes at position 2-3 (0-indexed)
_AFFILIATION_MAP = {
    "F": "03",   # Friend
    "H": "06",   # Hostile
    "N": "04",   # Neutral
    "U": "01",   # Unknown
}

# Echelon code → milsymbol echelon string
_ECHELON_MILSYMBOL = {
    "11": "Squad",
    "12": "Section",
    "13": "Platoon",
    "14": "Company",
    "15": "Battalion",
    "16": "Regiment",
    "17": "Brigade",
    "18": "Division",
    "19": "Corps",
    "20": "Army",
}

# Affiliation keyword sets for Ukrainian text
_FRIEND_KEYWORDS = {
    "свій", "своїх", "своя", "своє", "наш", "наша", "наше", "наші",
    "власн", "підрозділ", "батальйон", "бригада", "армія",
    "зсу", "зброй", "збройн",
}
_HOSTILE_KEYWORDS = {
    "противник", "пр-к", "пр.", "ворог", "ворожий", "ворожа",
    "ворожого", "ворожих", "окупант", "агресор", "рф", "рос",
}


class NATOSymbolManager:
    """Manager for NATO APP-6D symbols."""

    def __init__(self, database):
        self._db = database
        self._catalog_cache = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_sidc_for_unit(self, unit_text: str, affiliation: str = "U") -> str:
        """
        Heuristic: match unit_text against catalog keywords to find the best SIDC.
        Falls back to a generic infantry SIDC with the given affiliation.
        """
        if not unit_text:
            return self._default_sidc(affiliation)

        catalog = self._get_catalog()
        text_lower = unit_text.lower()

        # Filter by affiliation first, then score by keywords
        candidates = [s for s in catalog if s.get("affiliation") == affiliation]
        if not candidates:
            candidates = catalog

        best_score = 0
        best_sidc = self._default_sidc(affiliation)

        for sym in candidates:
            keywords = sym.get("keywords_ua", "").lower()
            name = sym.get("name_ua", "").lower()
            haystack = keywords + " " + name
            score = 0
            for kw in keywords.split(","):
                kw = kw.strip()
                if kw and kw in text_lower:
                    score += 2
            # Also check unit type mapping
            for ua_kw, _ in UNIT_TYPES.items():
                if ua_kw in text_lower and ua_kw in haystack:
                    score += 1
            if score > best_score:
                best_score = score
                best_sidc = sym["sidc"]

        return best_sidc

    def generate_milsymbol_options(self, sidc: str, echelon: str = "", size: int = 60) -> dict:
        """
        Return a dict of options suitable for milsymbol.js Symbol constructor.
        """
        options: dict = {
            "size": size,
            "infoFields": False,
        }
        if echelon:
            echelon_name = _ECHELON_MILSYMBOL.get(echelon, "")
            if echelon_name:
                options["echelon"] = echelon_name
        return options

    def build_sidc_with_echelon(self, base_sidc: str, echelon_code: str) -> str:
        """
        Insert echelon code into SIDC at the correct position.
        In APP-6D, the 2-character echelon modifier occupies positions 8-9 (0-indexed).
        """
        if len(base_sidc) != 20:
            return base_sidc
        if not echelon_code:
            return base_sidc
        # Echelon is encoded at characters index 8-9
        ec = echelon_code.zfill(2)
        return base_sidc[:8] + ec + base_sidc[10:]

    def affiliation_from_text(self, text: str) -> str:
        """Detect F/H/N/U from Ukrainian text."""
        text_lower = text.lower()
        hostile_score = sum(1 for kw in _HOSTILE_KEYWORDS if kw in text_lower)
        friend_score = sum(1 for kw in _FRIEND_KEYWORDS if kw in text_lower)
        if hostile_score > friend_score:
            return "H"
        if friend_score > 0:
            return "F"
        return "U"

    def echelon_from_text(self, text: str) -> str:
        """Detect echelon code from Ukrainian text."""
        text_lower = text.lower()
        for ua_name, code in ECHELONS.items():
            if ua_name in text_lower:
                return code
        return ""

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_catalog(self) -> list:
        if self._catalog_cache is None:
            self._catalog_cache = self._db.get_symbols_catalog()
        return self._catalog_cache

    def _default_sidc(self, affiliation: str) -> str:
        """Return a generic infantry SIDC for the given affiliation."""
        affil_codes = {
            "F": "10031000141211000000",
            "H": "10061000141211000000",
            "N": "10041000141211000000",
            "U": "10011000141211000000",
        }
        return affil_codes.get(affiliation, "10011000141211000000")

    @staticmethod
    def color_for_affiliation(affiliation: str) -> str:
        """Return NATO color hex string for an affiliation code."""
        return {
            "F": COLOR_FRIENDLY,
            "H": COLOR_HOSTILE,
            "N": COLOR_NEUTRAL,
            "U": COLOR_UNKNOWN,
        }.get(affiliation, COLOR_UNKNOWN)
