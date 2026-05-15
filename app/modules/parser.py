# -*- coding: utf-8 -*-
"""
app/modules/parser.py
Parser for Ukrainian military combat orders (Бойові розпорядження).
Extracts coordinates, units, boundaries, attack directions, and time references.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

try:
    from pyproj import Transformer
    _TRANSFORMER = Transformer.from_crs("EPSG:32636", "EPSG:4326", always_xy=True)
    _HAS_PYPROJ = True
except Exception:
    _HAS_PYPROJ = False


# ─── Regex patterns ──────────────────────────────────────────────────────────

# 6/8/10-digit grid with optional letter prefix (zone letter)
_GRID_RE = re.compile(
    r'\b([A-ZА-ЯҐЄІЇа-яґєії]{0,2}?)(\d{3})(\d{3})\b'   # 6-digit
    r'|\b([A-ZА-ЯҐЄІЇа-яґєії]{0,2}?)(\d{4})(\d{4})\b'   # 8-digit
    r'|\b([A-ZА-ЯҐЄІЇа-яґєії]{0,2}?)(\d{5})(\d{5})\b',  # 10-digit
    re.UNICODE,
)

# Explicit keyword + grid
_KEYWORD_GRID_RE = re.compile(
    r'(?:координати?|к-ти?|квадрат|кв\.?|рай-н|район)\s*[:\s]'
    r'([A-ZА-ЯҐЄІЇа-яґєії]{0,2}\d{6,10})',
    re.IGNORECASE | re.UNICODE,
)

# WGS-84 decimal or DMS
_WGS84_RE = re.compile(
    r'(\d{1,2}[.,]\d{4,8})\s*[°\s]*[NПн]?\s*[,;/]\s*'
    r'(\d{2,3}[.,]\d{4,8})\s*[°\s]*[EСсEe]?',
    re.UNICODE,
)

# Boundary line
_BOUNDARY_RE = re.compile(
    r'(?:розмежувальн[аяої]+\s+лін[іия][іяю]?|роз\.\s*лін\.?)'
    r'[:\s]+(.+?)(?=\n|\.|;|$)',
    re.IGNORECASE | re.UNICODE | re.MULTILINE,
)

# Attack direction
_ATTACK_DIR_RE = re.compile(
    r'(?:напрям(?:ок)?\s+(?:головного\s+)?удару|нгу)'
    r'[:\s]+(.+?)(?=\n|\.|;|$)',
    re.IGNORECASE | re.UNICODE | re.MULTILINE,
)

# Enemy position — "противник … квадрат XXYYYY"
_ENEMY_POS_RE = re.compile(
    r'(?:противник|пр-к|пр\.)[^\n.;]{0,80}'
    r'(?:район|рубіж|позиці[їяі]|квадрат|кв\.)[:\s]*'
    r'([A-ZА-ЯҐЄІЇа-яґєії]{0,2}\d{6,10})',
    re.IGNORECASE | re.UNICODE,
)

# Friendly unit with position
_UNIT_POS_RE = re.compile(
    r'(\d+[-\s]?(?:й|ий|а|я|е)?[-\s]?'
    r'(?:мех|мп|тб|тр|арт|пдб|дшб|рота|батальйон|бригада|взвод|дивізіон|батарея|зрдн|зрдб)'
    r'[^\n.;]{0,60}?)'
    r'(?:займа[єє]|зосереджу|перебуває?|наступа[єє]|виходить?|висувається?)'
    r'[^\n.;]{0,40}?'
    r'(?:район|рубіж|позиці[їяі]|квадрат|кв\.)[:\s]*'
    r'([A-ZА-ЯҐЄІЇа-яґєії]{0,2}\d{6,10})',
    re.IGNORECASE | re.UNICODE,
)

# Time — Ч±N
_TIME_CH_RE = re.compile(r'Ч\s*([+-])\s*(\d+)', re.UNICODE)
# Time — HH:MM or HH.MM
_TIME_CLOCK_RE = re.compile(r'\b(\d{1,2})[.:](\d{2})\b')

# Keywords for affiliation detection
_HOSTILE_WORDS = re.compile(
    r'противник|пр-к|пр\.|ворог|окупант|ворожий|ворожа|ворожі|неприятель',
    re.IGNORECASE | re.UNICODE,
)
_FRIENDLY_WORDS = re.compile(
    r'\bнаш[іаиоу]?\b|\bсво[їєіяю]\b|\bпідрозділ\b|\bрота\b|\bбатальйон\b'
    r'|\bбригада\b|\bвзвод\b',
    re.IGNORECASE | re.UNICODE,
)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ParseResult:
    coordinates: list = field(default_factory=list)
    units: list = field(default_factory=list)
    boundaries: list = field(default_factory=list)
    attack_directions: list = field(default_factory=list)
    times: list = field(default_factory=list)
    raw_text: str = ""

    @property
    def has_data(self) -> bool:
        return bool(self.coordinates or self.units or self.boundaries or self.attack_directions)

    def summary(self) -> str:
        parts = []
        if self.units:
            parts.append(f"Підрозділів: {len(self.units)}")
        if self.coordinates:
            parts.append(f"Координат: {len(self.coordinates)}")
        if self.boundaries:
            parts.append(f"Розм. ліній: {len(self.boundaries)}")
        if self.attack_directions:
            parts.append(f"Напрямків: {len(self.attack_directions)}")
        if self.times:
            parts.append(f"Часових відміток: {len(self.times)}")
        return " | ".join(parts) if parts else "Розпізнаних елементів не знайдено"


# ─── Parser ───────────────────────────────────────────────────────────────────

class CombatOrderParser:
    """Parses Ukrainian military combat order text into structured data."""

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, text: str) -> ParseResult:
        result = ParseResult(raw_text=text)
        result.units = self._extract_units(text)
        result.coordinates = self._extract_standalone_coords(text, result.units)
        result.boundaries = self._extract_boundaries(text)
        result.attack_directions = self._extract_attack_directions(text)
        result.times = self._extract_times(text)
        return result

    # ── Internal extractors ───────────────────────────────────────────────────

    def _extract_units(self, text: str) -> list:
        units = []
        seen_coords = set()

        # Hostile units
        for m in _ENEMY_POS_RE.finditer(text):
            grid_str = m.group(1)
            latlon = self._grid_to_latlon(grid_str)
            if latlon and grid_str not in seen_coords:
                seen_coords.add(grid_str)
                ctx = text[max(0, m.start() - 20):m.end() + 20]
                units.append({
                    "name": "Противник",
                    "affiliation": "H",
                    "type": self._guess_unit_type(ctx, "H"),
                    "echelon": self._echelon_from_text(ctx),
                    "coord": latlon,
                    "raw_coord": grid_str,
                    "context": ctx.strip(),
                })

        # Friendly units
        for m in _UNIT_POS_RE.finditer(text):
            unit_name = m.group(1).strip()
            grid_str = m.group(2)
            latlon = self._grid_to_latlon(grid_str)
            if latlon and grid_str not in seen_coords:
                seen_coords.add(grid_str)
                units.append({
                    "name": unit_name,
                    "affiliation": "F",
                    "type": self._guess_unit_type(unit_name, "F"),
                    "echelon": self._echelon_from_text(unit_name),
                    "coord": latlon,
                    "raw_coord": grid_str,
                    "context": unit_name,
                })

        return units

    def _extract_standalone_coords(self, text: str, already_placed: list) -> list:
        """Extract grids not already captured as unit positions."""
        placed_raw = {u["raw_coord"] for u in already_placed}
        coords = []
        seen = set()

        # Keyword-prefixed grids take priority
        for m in _KEYWORD_GRID_RE.finditer(text):
            grid_str = m.group(1)
            if grid_str in seen or grid_str in placed_raw:
                continue
            latlon = self._grid_to_latlon(grid_str)
            if latlon:
                seen.add(grid_str)
                ctx = text[max(0, m.start() - 30):m.end() + 30].strip()
                affil = self._affiliation_from_context(ctx)
                coords.append({
                    "type": "grid",
                    "raw": grid_str,
                    "lat": latlon[0],
                    "lng": latlon[1],
                    "affiliation": affil,
                    "context": ctx,
                })

        # Bare grids
        for m in _GRID_RE.finditer(text):
            # Determine which group matched (6/8/10-digit)
            if m.group(2) and m.group(3):
                grid_str = (m.group(1) or "") + m.group(2) + m.group(3)
            elif m.group(5) and m.group(6):
                grid_str = (m.group(4) or "") + m.group(5) + m.group(6)
            elif m.group(8) and m.group(9):
                grid_str = (m.group(7) or "") + m.group(8) + m.group(9)
            else:
                continue

            digits_only = re.sub(r'\D', '', grid_str)
            if digits_only in seen or grid_str in seen or grid_str in placed_raw:
                continue
            if len(digits_only) not in (6, 8, 10):
                continue

            latlon = self._grid_to_latlon(grid_str)
            if latlon:
                seen.add(digits_only)
                ctx = text[max(0, m.start() - 40):m.end() + 40].strip()
                affil = self._affiliation_from_context(ctx)
                coords.append({
                    "type": "grid",
                    "raw": grid_str,
                    "lat": latlon[0],
                    "lng": latlon[1],
                    "affiliation": affil,
                    "context": ctx,
                })

        # WGS-84 decimal pairs
        for m in _WGS84_RE.finditer(text):
            try:
                lat = float(m.group(1).replace(",", "."))
                lng = float(m.group(2).replace(",", "."))
                if 44 <= lat <= 53 and 22 <= lng <= 40:
                    key = f"{lat:.4f},{lng:.4f}"
                    if key not in seen:
                        seen.add(key)
                        ctx = text[max(0, m.start() - 30):m.end() + 30].strip()
                        coords.append({
                            "type": "wgs84",
                            "raw": m.group(0),
                            "lat": round(lat, 6),
                            "lng": round(lng, 6),
                            "affiliation": self._affiliation_from_context(ctx),
                            "context": ctx,
                        })
            except ValueError:
                continue

        return coords

    def _extract_boundaries(self, text: str) -> list:
        boundaries = []
        for m in _BOUNDARY_RE.finditer(text):
            raw = m.group(1).strip()
            points = self._parse_coord_sequence(raw)
            boundaries.append({
                "name": "Розмежувальна лінія",
                "raw": raw,
                "points": points,
            })
        return boundaries

    def _extract_attack_directions(self, text: str) -> list:
        directions = []
        for m in _ATTACK_DIR_RE.finditer(text):
            raw = m.group(1).strip()
            points = self._parse_coord_sequence(raw)
            if len(points) >= 2:
                directions.append({
                    "name": "Напрямок головного удару",
                    "raw": raw,
                    "from_coord": points[0],
                    "to_coord": points[-1],
                    "points": points,
                })
            elif points:
                directions.append({
                    "name": "Напрямок головного удару",
                    "raw": raw,
                    "from_coord": points[0],
                    "to_coord": None,
                    "points": points,
                })
        return directions

    def _extract_times(self, text: str) -> list:
        times = []
        for m in _TIME_CH_RE.finditer(text):
            sign = m.group(1)
            val = int(m.group(2))
            times.append({"type": "Ч", "sign": sign, "hours": val,
                          "display": f"Ч{sign}{val}"})
        for m in _TIME_CLOCK_RE.finditer(text):
            h, mn = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mn <= 59:
                times.append({"type": "clock", "hour": h, "minute": mn,
                              "display": f"{h:02d}:{mn:02d}"})
        return times

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _grid_to_latlon(self, grid_str: str) -> Optional[tuple]:
        """Convert a Ukrainian military grid reference to (lat, lng).

        Ukrainian topographic grids use the Gauss-Krüger system (6° zones).
        Zone 5 (central meridian 27°E, false easting 5_500_000) covers
        most of western Ukraine; zone 6 (33°E, false easting 6_500_000)
        covers central/eastern Ukraine.

        For the MVP we use a pragmatic heuristic: interpret the grid digits
        as kilometre-scale offsets and anchor them inside Ukraine via
        UTM zone 36N (EPSG:32636), which covers 30°–36°E.
        """
        digits = re.sub(r'\D', '', grid_str)
        n = len(digits)
        if n not in (6, 8, 10):
            return None

        half = n // 2
        try:
            e_raw = int(digits[:half])
            n_raw = int(digits[half:])
        except ValueError:
            return None

        # Scale to metres
        scale = {6: 1000, 8: 100, 10: 1}[n]
        easting = e_raw * scale + scale // 2
        northing = n_raw * scale + scale // 2

        # Anchor within Ukrainian extents (UTM 36N)
        # Easting valid range in zone 36N for Ukraine: ~250 000 – 750 000 m
        # Northing valid range for Ukraine: ~5 400 000 – 5 800 000 m
        if easting < 100_000:
            easting += 300_000
        if northing < 1_000_000:
            northing += 5_400_000

        if not _HAS_PYPROJ:
            # Fallback: very rough linear approximation for zone 36N
            lat = 44.0 + (northing - 5_400_000) / 111_320
            lng = 30.0 + (easting - 500_000) / (111_320 * 0.669)
            if 44 <= lat <= 53 and 22 <= lng <= 40:
                return (round(lat, 6), round(lng, 6))
            return None

        try:
            lng, lat = _TRANSFORMER.transform(easting, northing)
            if 44 <= lat <= 53 and 22 <= lng <= 40:
                return (round(lat, 6), round(lng, 6))
        except Exception:
            pass
        return None

    def _parse_coord_sequence(self, text: str) -> list:
        """Extract a sequence of (lat, lng) tuples from a dash-separated string."""
        points = []
        segments = re.split(r'\s*[-–—]\s*', text)
        for seg in segments:
            m = _GRID_RE.search(seg)
            if m:
                if m.group(2):
                    g = (m.group(1) or "") + m.group(2) + m.group(3)
                elif m.group(5):
                    g = (m.group(4) or "") + m.group(5) + m.group(6)
                else:
                    g = (m.group(7) or "") + m.group(8) + m.group(9)
                ll = self._grid_to_latlon(g)
                if ll:
                    points.append(ll)
        return points

    # ── Classification helpers ────────────────────────────────────────────────

    def _affiliation_from_context(self, ctx: str) -> str:
        if _HOSTILE_WORDS.search(ctx):
            return "H"
        if _FRIENDLY_WORDS.search(ctx):
            return "F"
        return "U"

    def _guess_unit_type(self, text: str, affiliation: str) -> str:
        from app.config import UNIT_TYPES
        text_lower = text.lower()
        for kw, utype in UNIT_TYPES.items():
            if kw in text_lower:
                return utype
        return "infantry"

    def _echelon_from_text(self, text: str) -> str:
        from app.config import ECHELONS
        text_lower = text.lower()
        for name, code in ECHELONS.items():
            if name in text_lower:
                return code
        return ""
