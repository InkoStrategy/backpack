# -*- coding: utf-8 -*-
"""
app/modules/database.py
SQLite database manager for Тактична ГІС.
Manages the NATO symbols catalog, missions, and placed symbols.
"""

import sqlite3
import json
import os
from datetime import datetime


# ─── Default symbols catalog ─────────────────────────────────────────────────
_SEED_SYMBOLS = [
    {
        "sidc": "10031000141211000000",
        "name_ua": "Мотопіхотний підрозділ (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "mechanized_infantry",
        "geom_type": "point",
        "keywords_ua": "піхота,мпб,мпр,мп взвод,мех,мотопіхот",
        "description_ua": "Мотопіхотний (механізований) підрозділ своїх військ",
    },
    {
        "sidc": "10061000141211000000",
        "name_ua": "Мотопіхотний підрозділ (ворог)",
        "category": "unit",
        "affiliation": "H",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "mechanized_infantry",
        "geom_type": "point",
        "keywords_ua": "піхота противника,пр-к піхота,ворог піхота",
        "description_ua": "Мотопіхотний підрозділ противника",
    },
    {
        "sidc": "10031000141213000000",
        "name_ua": "Танковий підрозділ (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "armor",
        "geom_type": "point",
        "keywords_ua": "танк,тбр,тб,тр,т взвод,бронетанков",
        "description_ua": "Танковий підрозділ своїх військ",
    },
    {
        "sidc": "10061000141213000000",
        "name_ua": "Танковий підрозділ (ворог)",
        "category": "unit",
        "affiliation": "H",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "armor",
        "geom_type": "point",
        "keywords_ua": "танки противника,бронетехніка ворога",
        "description_ua": "Танковий підрозділ противника",
    },
    {
        "sidc": "10031000141502000000",
        "name_ua": "Артилерійський підрозділ (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "artillery",
        "geom_type": "point",
        "keywords_ua": "артилерія,арт,гармата,гаубиця,рса,реактивна",
        "description_ua": "Артилерійський підрозділ своїх військ",
    },
    {
        "sidc": "10061000141502000000",
        "name_ua": "Артилерійський підрозділ (ворог)",
        "category": "unit",
        "affiliation": "H",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "artillery",
        "geom_type": "point",
        "keywords_ua": "артилерія противника,арт пр-к",
        "description_ua": "Артилерійський підрозділ противника",
    },
    {
        "sidc": "10031000160000000000",
        "name_ua": "Командний пункт (свій)",
        "category": "installation",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "command",
        "geom_type": "point",
        "keywords_ua": "кп,командний пункт,штаб,кнп",
        "description_ua": "Командний пункт своїх військ",
    },
    {
        "sidc": "10061000160000000000",
        "name_ua": "Командний пункт (ворог)",
        "category": "installation",
        "affiliation": "H",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "command",
        "geom_type": "point",
        "keywords_ua": "кп противника,штаб ворога",
        "description_ua": "Командний пункт противника",
    },
    {
        "sidc": "10031000160500000000",
        "name_ua": "Спостережний пункт (свій)",
        "category": "installation",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "observation",
        "geom_type": "point",
        "keywords_ua": "сп,спостережний пункт,нп,нпа",
        "description_ua": "Спостережний / наглядовий пункт",
    },
    {
        "sidc": "10031000141104000000",
        "name_ua": "Підрозділ ППО (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "air_defense",
        "geom_type": "point",
        "keywords_ua": "ппо,зенітний,зрк,стрілець",
        "description_ua": "Зенітний ракетний підрозділ своїх військ",
    },
    {
        "sidc": "10031000141207000000",
        "name_ua": "Інженерний підрозділ (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "engineer",
        "geom_type": "point",
        "keywords_ua": "інженерний,сапер,понтон,мостовий",
        "description_ua": "Інженерно-саперний підрозділ своїх військ",
    },
    {
        "sidc": "10031000161000000000",
        "name_ua": "Підрозділ тилу (свій)",
        "category": "unit",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "10",
        "entity_type": "logistics",
        "geom_type": "point",
        "keywords_ua": "тил,логістика,матзаб,мто",
        "description_ua": "Підрозділ матеріально-технічного забезпечення",
    },
    {
        "sidc": "10032500001501000000",
        "name_ua": "Рубіж (фазова лінія)",
        "category": "tactical_graphic",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "25",
        "entity_type": "phase_line",
        "geom_type": "line",
        "keywords_ua": "рубіж,фр,фазова лінія,фл",
        "description_ua": "Фазова лінія / рубіж",
    },
    {
        "sidc": "10032500001201000000",
        "name_ua": "Напрямок головного удару",
        "category": "tactical_graphic",
        "affiliation": "F",
        "echelon": "",
        "symbol_set": "25",
        "entity_type": "main_attack",
        "geom_type": "line",
        "keywords_ua": "нгу,напрямок,головний удар,напрямок удару",
        "description_ua": "Вісь / напрямок головного удару",
    },
]


class Database:
    """SQLite database manager for TacGIS."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure the parent directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    # ── Schema ────────────────────────────────────────────────────────────────

    def initialize(self):
        """Create tables if they don't exist and seed the catalog."""
        self._create_tables()
        self._seed_catalog()

    def _create_tables(self):
        cur = self._conn.cursor()

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS symbols (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sidc          TEXT NOT NULL,
                name_ua       TEXT NOT NULL,
                category      TEXT NOT NULL DEFAULT 'unit',
                affiliation   TEXT NOT NULL DEFAULT 'U',
                echelon       TEXT NOT NULL DEFAULT '',
                symbol_set    TEXT NOT NULL DEFAULT '10',
                entity_type   TEXT NOT NULL DEFAULT '',
                geom_type     TEXT NOT NULL DEFAULT 'point',
                keywords_ua   TEXT NOT NULL DEFAULT '',
                description_ua TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS missions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                order_text  TEXT NOT NULL DEFAULT '',
                map_state   TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS placed_symbols (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id  INTEGER NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
                sidc        TEXT NOT NULL,
                lat         REAL NOT NULL,
                lng         REAL NOT NULL,
                label       TEXT NOT NULL DEFAULT '',
                echelon     TEXT NOT NULL DEFAULT '',
                affiliation TEXT NOT NULL DEFAULT 'U',
                notes       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL
            );
        """)
        self._conn.commit()

    def _seed_catalog(self):
        """Insert seed entries that are not already present (idempotent)."""
        cur = self._conn.cursor()
        for sym in _SEED_SYMBOLS:
            cur.execute(
                "SELECT id FROM symbols WHERE sidc = ? AND name_ua = ?",
                (sym["sidc"], sym["name_ua"]),
            )
            if cur.fetchone() is None:
                cur.execute(
                    """
                    INSERT INTO symbols
                        (sidc, name_ua, category, affiliation, echelon,
                         symbol_set, entity_type, geom_type, keywords_ua, description_ua)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sym["sidc"],
                        sym["name_ua"],
                        sym["category"],
                        sym["affiliation"],
                        sym["echelon"],
                        sym["symbol_set"],
                        sym["entity_type"],
                        sym["geom_type"],
                        sym["keywords_ua"],
                        sym["description_ua"],
                    ),
                )
        self._conn.commit()

    # ── Symbols catalog ───────────────────────────────────────────────────────

    def get_symbols_catalog(self) -> list:
        """Return all symbols from the catalog as a list of dicts."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM symbols ORDER BY category, name_ua")
        return [dict(row) for row in cur.fetchall()]

    def find_symbol_by_keywords(self, keywords: str) -> list:
        """
        Search catalog by a space/comma-separated keyword string.
        Returns a ranked list of matching symbol dicts.
        """
        tokens = [t.strip().lower() for t in keywords.replace(",", " ").split() if t.strip()]
        if not tokens:
            return []

        cur = self._conn.cursor()
        cur.execute("SELECT * FROM symbols")
        rows = [dict(r) for r in cur.fetchall()]

        scored = []
        for row in rows:
            haystack = (row["keywords_ua"] + " " + row["name_ua"]).lower()
            score = sum(1 for tok in tokens if tok in haystack)
            if score > 0:
                scored.append((score, row))

        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored]

    # ── Missions ──────────────────────────────────────────────────────────────

    def save_mission(self, name: str, order_text: str, map_state: dict) -> int:
        """Insert or update a mission. Returns the mission id."""
        cur = self._conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT INTO missions (name, created_at, order_text, map_state)
            VALUES (?, ?, ?, ?)
            """,
            (name, now, order_text, json.dumps(map_state, ensure_ascii=False)),
        )
        self._conn.commit()
        return cur.lastrowid

    def load_mission(self, mission_id: int) -> dict | None:
        """Load a single mission by id. Returns dict or None."""
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
        row = cur.fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            result["map_state"] = json.loads(result["map_state"])
        except (json.JSONDecodeError, TypeError):
            result["map_state"] = {}
        return result

    def list_missions(self) -> list:
        """Return a list of all missions (id, name, created_at)."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT id, name, created_at FROM missions ORDER BY created_at DESC"
        )
        return [dict(row) for row in cur.fetchall()]

    # ── Placed symbols ────────────────────────────────────────────────────────

    def save_placed_symbol(self, mission_id: int, symbol_data: dict) -> int:
        """Insert a placed symbol record. Returns its id."""
        cur = self._conn.cursor()
        now = datetime.utcnow().isoformat()
        cur.execute(
            """
            INSERT INTO placed_symbols
                (mission_id, sidc, lat, lng, label, echelon, affiliation, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mission_id,
                symbol_data.get("sidc", ""),
                symbol_data.get("lat", 0.0),
                symbol_data.get("lng", 0.0),
                symbol_data.get("label", ""),
                symbol_data.get("echelon", ""),
                symbol_data.get("affiliation", "U"),
                symbol_data.get("notes", ""),
                now,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_placed_symbols(self, mission_id: int) -> list:
        """Return all placed symbols for a mission."""
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM placed_symbols WHERE mission_id = ? ORDER BY created_at",
            (mission_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
