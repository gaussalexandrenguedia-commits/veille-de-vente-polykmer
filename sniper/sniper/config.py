"""Chargement de watches.yaml (+ substitution ${ENV_VAR})."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

ENV_RE = re.compile(r"\$\{([A-Za-z0-9_]+)\}")
TIERS_DEFAUT = {"hot": 30, "warm": 300, "cold": 3600}


def _subst(obj):
    if isinstance(obj, str):
        return ENV_RE.sub(lambda m: os.getenv(m.group(1), ""), obj)
    if isinstance(obj, dict):
        return {k: _subst(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v) for v in obj]
    return obj


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = _subst(yaml.safe_load(f) or {})
    cfg.setdefault("global", {})
    g = cfg["global"]
    g.setdefault("default_cooldown", 300)
    g.setdefault("dedup_ttl", 86400)
    g.setdefault("state_db", "state/sniper.db")
    g.setdefault("max_parallel", 10)
    g.setdefault("min_interval_per_domain", 15)
    for w in cfg.get("watches", []):
        if not w.get("interval"):
            w["interval"] = 0 if w.get("type") == "webhook" else TIERS_DEFAUT.get(w.get("tier", "warm"), 300)
        # garde-fou anti-ban : jamais plus vite que le minimum par domaine
        if w.get("type") in ("api_json", "html", "playwright") and 0 < w["interval"] < g["min_interval_per_domain"]:
            w["interval"] = g["min_interval_per_domain"]
        w.setdefault("rules", [])
        w.setdefault("actions", {"telegram": True, "apprise": False, "post_api": False})
        w.setdefault("ville", "Douala")
    return cfg
