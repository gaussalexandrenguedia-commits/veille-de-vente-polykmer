"""Pont lecture-seule vers le module sniper (état temps réel).

Lit sniper/state/sniper.db (SQLite du runner) + watches.yaml pour enrichir.
Si le sniper ne tourne pas encore -> available=false + guide de démarrage.
"""
from __future__ import annotations

import json
import sqlite3
import time

from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/api/v1/sniper", tags=["sniper"])


def _lire_config() -> dict:
    try:
        import yaml
        with open(settings.SNIPER_CONFIG, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return {w["id"]: w for w in cfg.get("watches", [])}
    except Exception:
        return {}


def _connect():
    return sqlite3.connect(f"file:{settings.SNIPER_STATE_DB}?mode=ro", uri=True)


@router.get("/status")
def status():
    try:
        db = _connect()
    except Exception:
        return {"available": False, "hint": "runner_non_demarre"}
    try:
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "watch_state" not in tables:
            return {"available": False, "hint": "base_vide"}
        cfg = _lire_config()
        now = time.time()
        watches = []
        for wid, obs_json, updated in db.execute(
                "SELECT watch_id, obs_json, updated FROM watch_state"):
            try:
                obs = json.loads(obs_json)
            except ValueError:
                obs = {}
            w = cfg.get(wid, {})
            watches.append({
                "id": wid, "name": w.get("name", wid),
                "tier": w.get("tier", "?"), "interval": w.get("interval"),
                "ville": w.get("ville", ""), "url": w.get("url", ""),
                "price": obs.get("price"), "stock": obs.get("stock"),
                "seller_phone": bool(obs.get("seller_phone")),
                "zone_ok": obs.get("zone_ok"), "selector_used": obs.get("selector_used"),
                "updated_ago_s": int(now - updated),
            })
        signaux = 0
        if "signals_vus" in tables:
            signaux = db.execute("SELECT COUNT(*) FROM signals_vus WHERE created > ?",
                                 (now - 86400,)).fetchone()[0]
        cooldowns = 0
        if "cooldowns" in tables:
            cooldowns = db.execute("SELECT COUNT(*) FROM cooldowns WHERE last_alert > ?",
                                   (now - 3600,)).fetchone()[0]
        return {"available": True, "watches": sorted(watches, key=lambda x: x["id"]),
                "signaux_24h": signaux, "cooldowns_actifs": cooldowns,
                "config_connue": bool(cfg)}
    finally:
        db.close()


@router.get("/selectors/{watch_id}")
def selectors(watch_id: str):
    try:
        db = _connect()
    except Exception:
        return []
    try:
        rows = db.execute(
            """SELECT selector, ok, fail FROM selector_stats
               WHERE watch_id=? ORDER BY ok DESC, fail ASC""", (watch_id,)).fetchall()
        return [{"selector": s, "ok": o, "fail": f} for s, o, f in rows]
    except Exception:
        return []
    finally:
        db.close()
