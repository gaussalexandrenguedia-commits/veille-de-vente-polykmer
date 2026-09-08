"""Tests parsing scrapers — hors-ligne, sur fixtures HTML réalistes.

Si Jumia/CoinAfrique changent leur HTML, ces tests échouent et indiquent
quoi ajuster AVANT de relancer une collecte réelle.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coinafrique import parse_coin_html  # noqa: E402
from jumia_cm import BASE, parse_jumia_html  # noqa: E402

FIX = Path(__file__).parent


def test_jumia_fixture():
    offres = parse_jumia_html((FIX / "fixtures_jumia.html").read_text())
    assert len(offres) == 2
    assert offres[0]["titre"] == "Congélateur Hisense 200L"
    assert offres[0]["prix"] == 175000
    assert offres[0]["ancien_prix"] == 195000
    assert offres[0]["url"].startswith(BASE)
    assert offres[1]["prix"] == 52500
    assert offres[1]["ancien_prix"] is None


def test_jumia_repli_generique():
    offres = parse_jumia_html('<a href="/catalog/x.html">TV TCL 32 pouces 95000 FCFA</a>')
    assert len(offres) == 1 and offres[0]["prix"] == 95000


def test_coin_fixture():
    offres = parse_coin_html((FIX / "fixtures_coin.html").read_text(), "douala")
    assert len(offres) == 2
    assert offres[0]["prix"] == 140000
    assert offres[0]["url"].startswith("https://www.coinafrique.com")
    assert offres[1]["prix"] == 27500


def test_coin_vide():
    assert parse_coin_html("<html><body>aucune annonce</body></html>") == []
    assert parse_jumia_html("<html></html>") == []
