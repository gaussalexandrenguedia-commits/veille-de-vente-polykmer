"""Tests Agent IA — 100 % hors-ligne (heuristiques + scoring + templates)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai_client import mask_key  # noqa: E402
from app.services.ai_parse import parse_heuristic  # noqa: E402
from app.services.ai_scoring import flags_fraude, verdict_ecart  # noqa: E402
from app.services.ai_write import message_template, wa_link  # noqa: E402


def test_parse_annonce_complete():
    r = parse_heuristic("Vs iphone 13 propre 350k kmer négo à dla 699123456")
    assert r["prix"] == 350000
    assert r["ville"] == "Douala"
    assert r["nego"] is True
    assert r["phone"] == "699123456"
    assert r["intention"] == "vente"
    assert "iphone" in (r["produit"] or "").lower()
    assert r["source"] == "heuristique"


def test_parse_kva_pas_un_prix():
    r = parse_heuristic("Je cherche groupe électrogène 5kva Yaoundé urgent")
    assert r["prix"] is None  # 5kva n'est pas 5 000 !
    assert r["intention"] == "achat"
    assert r["ville"] == "Yaoundé"


def test_parse_spam():
    r = parse_heuristic("Gagner 50000 FCFA par jour, cliquez ici investissement garanti")
    assert r["intention"] == "spam"


def test_verdicts():
    assert verdict_ecart(-35)[0] == "prioritaire"
    assert verdict_ecart(-15)[0] == "interessant"
    assert verdict_ecart(5)[0] == "marche"
    assert verdict_ecart(20)[0] == "cher"
    assert verdict_ecart(40)[0] == "tres_cher"


def test_fraude():
    assert "prix_anormalement_bas" in flags_fraude(50000, 200000, "iphone 13")
    assert "demande_avance" in flags_fraude(180000, 200000, "envoyez avance momo d'abord")
    assert flags_fraude(190000, 200000, "Congélateur Hisense 200L, garantie 6 mois, Akwa") == []


def test_message_et_wa():
    msg = message_template("iPhone 13", 350000, "Douala", 320000)
    assert "350 000" in msg and "320 000" in msg and "Douala" in msg
    lien = wa_link("699 12 34 56", "Bonjour")
    assert lien == "https://wa.me/237699123456?text=Bonjour"
    assert wa_link(None, "x") is None
    assert wa_link("123", "x") is None


def test_mask_key():
    assert mask_key("AQ.Ab8RN6LP12S4OIYuBGFNTfKV") == "AQ.Ab8…TfKV"
    assert mask_key("") == "***"


def test_prompt_fraude_format_safe():
    from app.services.ai_scoring import PROMPT_FRAUDE
    out = PROMPT_FRAUDE.format(texte="x", prix="1", mediane="2", ecart=-5, ville="Dla")
    assert '{"suspect"' in out


def test_message_ponctuation():
    msg = message_template("iPhone 13", 350000, "Douala", 320000)
    assert "Bonjour, votre" in msg and "  " not in msg


def test_produit_garde_reference():
    r = parse_heuristic("Vs iphone 13 propre 350k kmer négo à dla 699123456")
    assert r["produit"] and "iphone 13" in r["produit"].lower()
