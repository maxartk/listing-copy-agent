"""Tiny SQLite cache so repeated runs do not pay twice."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Dict, Optional

DEFAULT_PATH = Path(".listing_cache.sqlite")


class CopyCache:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS copy (key TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )
        self.conn.commit()

    @staticmethod
    def make_key(row: Dict[str, str], provider: str) -> str:
        basis = "|".join(
            [provider, row.get("sku", ""), row.get("name", ""), row.get("category", ""), row.get("attributes", "")]
        )
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, str]]:
        row = self.conn.execute("SELECT payload FROM copy WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, payload: Dict[str, str]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO copy (key, payload) VALUES (?, ?)",
            (key, json.dumps(payload, ensure_ascii=False)),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
