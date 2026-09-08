"""Extracteurs sans dépendances lourdes : prix XAF, JSON-path, regex, hash."""
from __future__ import annotations

import hashlib
import json
import re

PRIX_RE = re.compile(r"(\d[\d\s\u00a0\u202f.,]*)\s*(FCFA|XAF|F\s?CFA)?", re.I)


def parse_prix_xaf(txt: str | float | int | None) -> float | None:
    """'32 500 FCFA' -> 32500.0 — tolère espaces insécables et points milliers."""
    if txt is None:
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    m = PRIX_RE.search(str(txt).replace("\u00a0", " ").replace("\u202f", " "))
    if not m:
        return None
    chiffres = re.sub(r"[^\d]", "", m.group(1))
    if not chiffres:
        return None
    try:
        return float(chiffres)
    except ValueError:
        return None


def json_path(data, path: str):
    """Mini JSON-path pointé : 'data.items.0.price'. Lève KeyError si absent."""
    cur = data
    for seg in str(path).split("."):
        if isinstance(cur, list):
            cur = cur[int(seg)]
        elif isinstance(cur, dict):
            cur = cur[seg]
        else:
            raise KeyError(path)
    return cur


def extract_regex(text: str, pattern: str, group: int = 1) -> str | None:
    m = re.search(pattern, text, re.I | re.S)
    if not m:
        return None
    try:
        return m.group(group)
    except IndexError:
        return m.group(0)


def normalize_stock(value) -> bool | None:
    """True/False, 1/0, 'in_stock', 'inStock', 'en_stock' -> bool."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    v = str(value).strip().lower()
    if v in ("true", "1", "yes", "in_stock", "instock", "en_stock", "available", "disponible"):
        return True
    if v in ("false", "0", "no", "out_of_stock", "outofstock", "rupture", "unavailable", "indisponible"):
        return False
    return None


def page_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]


def to_json_preview(obj, limit: int = 20000) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)[:limit]
    except TypeError:
        return str(obj)[:limit]
