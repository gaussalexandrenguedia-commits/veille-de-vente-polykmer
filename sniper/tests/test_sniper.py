"""Tests sniper — 100 % hors-ligne (extracteurs, règles, store, config)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sniper.config import load_config  # noqa: E402
from sniper.extractors import (extract_regex, json_path, normalize_stock,  # noqa: E402
                               parse_prix_xaf)
from sniper.rules import evaluate  # noqa: E402
from sniper.store import Store  # noqa: E402

WATCH = {"id": "test", "name": "Test", "ville": "Douala", "rules": [
    {"type": "drop_pct", "value": 10},
    {"type": "below", "value": 25000},
    {"type": "back_in_stock"},
    {"type": "keyword", "pattern": "starlink"},
    {"type": "new_items"},
]}


def test_parse_prix():
    assert parse_prix_xaf("32 500 FCFA") == 32500
    assert parse_prix_xaf("1\u00a0750 XAF") == 1750
    assert parse_prix_xaf("Prix : 185.000 F CFA") == 185000
    assert parse_prix_xaf(28000) == 28000
    assert parse_prix_xaf("gratuit") is None


def test_json_path():
    data = {"data": {"items": [{"id": "a", "prix": 100}]}, "ok": True}
    assert json_path(data, "data.items.0.prix") == 100
    assert json_path(data, "ok") is True


def test_regex():
    assert extract_regex("Prix : 32 500 FCFA", r"([\d\s]+)\s*FCFA").strip() == "32 500"
    assert extract_regex("rien ici", r"FCFA") is None


def test_stock():
    assert normalize_stock("inStock") is True
    assert normalize_stock("rupture") is False
    assert normalize_stock(1) is True
    assert normalize_stock(None) is None


def test_drop_pct():
    sigs = evaluate(WATCH, {"price": 25000.0, "text": "", "hash": "b"},
                    {"price": 30000.0, "text": "", "hash": "a"})
    regles = {s.rule for s in sigs}
    assert "drop_pct" in regles  # -16.7 %
    assert any(s.severity == "rouge" for s in sigs if s.rule == "drop_pct")


def test_pas_de_faux_positif_drop():
    sigs = evaluate(WATCH, {"price": 29000.0, "text": "", "hash": "b"},
                    {"price": 30000.0, "text": "", "hash": "a"})
    assert "drop_pct" not in {s.rule for s in sigs}  # -3.3 % < 10 %


def test_below_et_back_in_stock():
    sigs = evaluate(WATCH, {"price": 24000.0, "stock": True, "text": "", "hash": "x"},
                    {"price": 26000.0, "stock": False, "text": "", "hash": "y"})
    assert {"below", "back_in_stock"} <= {s.rule for s in sigs}


def test_keyword_et_new_items():
    prev = {"text": "arrivage téléviseurs", "items": ["tv32"], "hash": "a"}
    obs = {"text": "arrivage Starlink et téléviseurs", "items": ["tv32", "starlink-v2"], "hash": "b"}
    regles = {s.rule for s in evaluate(WATCH, obs, prev)}
    assert {"keyword", "new_item"} <= regles


def test_premier_passage_sans_historique():
    # Pas de prev -> pas de drop/new_items (amorçage), mais below fonctionne
    sigs = evaluate(WATCH, {"price": 20000.0, "items": ["a"], "text": "x", "hash": "h"}, None)
    assert {s.rule for s in sigs} == {"below"}


def test_store_dedup_et_cooldown():
    st = Store()
    assert st.is_duplicate("sig1") is False
    assert st.is_duplicate("sig1") is True   # 2e fois = doublon
    assert st.cooldown_ok("w:r", 300) is True
    st.mark_alert("w:r")
    assert st.cooldown_ok("w:r", 300) is False
    assert st.cooldown_ok("w:r", 0) is True  # cooldown 0 = toujours OK
    st.set_state("w", {"price": 10})
    assert st.get_state("w") == {"price": 10}


def test_config_charge_et_garde_fou(tmp_path):
    p = tmp_path / "w.yaml"
    p.write_text(yaml.safe_dump({
        "global": {"min_interval_per_domain": 15},
        "watches": [
            {"id": "a", "type": "html", "tier": "hot", "interval": 2, "url": "https://x"},
            {"id": "b", "type": "webhook"},
        ]}), encoding="utf-8")
    cfg = load_config(p)
    by_id = {w["id"]: w for w in cfg["watches"]}
    assert by_id["a"]["interval"] == 15  # remonté au garde-fou anti-ban
    assert by_id["b"]["interval"] == 0   # webhook = jamais pollé
