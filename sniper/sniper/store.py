"""État persistant SQLite : dernières observations, dédup, cooldowns."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS watch_state (
  watch_id TEXT PRIMARY KEY, obs_json TEXT NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS signals_vus (
  sig_hash TEXT PRIMARY KEY, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS cooldowns (
  cle TEXT PRIMARY KEY, last_alert REAL NOT NULL);
"""


class Store:
    def __init__(self, path: str = ":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    # ── observations ──
    def get_state(self, watch_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT obs_json FROM watch_state WHERE watch_id=?", (watch_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def set_state(self, watch_id: str, obs: dict) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO watch_state VALUES (?,?,?)",
            (watch_id, json.dumps(obs, ensure_ascii=False), time.time()))
        self.db.commit()

    # ── déduplication : True = déjà vu (dans TTL), sinon enregistre et False ──
    def is_duplicate(self, sig_hash: str, ttl_s: int = 86400) -> bool:
        now = time.time()
        row = self.db.execute(
            "SELECT created FROM signals_vus WHERE sig_hash=?", (sig_hash,)).fetchone()
        if row and now - row[0] < ttl_s:
            return True
        self.db.execute("INSERT OR REPLACE INTO signals_vus VALUES (?,?)", (sig_hash, now))
        self.db.execute("DELETE FROM signals_vus WHERE created < ?", (now - ttl_s,))
        self.db.commit()
        return False

    # ── cooldowns anti-spam ──
    def cooldown_ok(self, cle: str, cooldown_s: int) -> bool:
        row = self.db.execute("SELECT last_alert FROM cooldowns WHERE cle=?", (cle,)).fetchone()
        return (not row) or (time.time() - row[0] >= cooldown_s)

    def mark_alert(self, cle: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO cooldowns VALUES (?,?)", (cle, time.time()))
        self.db.commit()
