"""SQLite saqlash: nomzodlar va o'chirilganlar jurnali."""
from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
    user_id  INTEGER PRIMARY KEY,
    username TEXT,
    score    INTEGER NOT NULL,
    reasons  TEXT,
    access_hash INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS removed (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    reasons    TEXT,
    removed_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    # --- nomzodlar ---------------------------------------------------
    def replace_candidates(self, rows: list[tuple[int, str, int, str, int]]) -> None:
        """rows: (user_id, username, score, reasons, access_hash)"""
        with self.conn:
            self.conn.execute("DELETE FROM candidates")
            self.conn.executemany(
                "INSERT OR REPLACE INTO candidates "
                "(user_id, username, score, reasons, access_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )

    def pending(self, limit: int) -> list[tuple[int, str, int, str, int]]:
        cur = self.conn.execute(
            """SELECT user_id, username, score, reasons, access_hash FROM candidates
               WHERE user_id NOT IN (SELECT user_id FROM removed)
               ORDER BY score DESC, user_id LIMIT ?""",
            (limit,),
        )
        return cur.fetchall()

    def pending_count(self) -> int:
        cur = self.conn.execute(
            """SELECT COUNT(*) FROM candidates
               WHERE user_id NOT IN (SELECT user_id FROM removed)"""
        )
        return cur.fetchone()[0]

    # --- o'chirilganlar ----------------------------------------------
    def removed_ids(self) -> set[int]:
        return {r[0] for r in self.conn.execute("SELECT user_id FROM removed")}

    def mark_removed(self, user_id: int, username: str, reasons: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO removed VALUES (?, ?, ?, ?)",
                (user_id, username, reasons, _now()),
            )

    def removed_today(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM removed WHERE substr(removed_at, 1, 10) = ?",
            (today,),
        )
        return cur.fetchone()[0]

    def removed_total(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM removed").fetchone()[0]

    # --- hisobot -----------------------------------------------------
    def export_candidates_csv(self, path: Path) -> int:
        rows = self.pending(10**9)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "username", "ball", "sabablar"])
            writer.writerows(r[:4] for r in rows)
        return len(rows)
