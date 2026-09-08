"""Tests avancés — hors-ligne : healing, zones, cleaner, sémantique, one-click, sessions."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sniper.alerter import Alerter  # noqa: E402
from sniper.cleaner import clean_html_to_text, compression_ratio  # noqa: E402
from sniper.healer import best_price, extract_zone, find_price_candidates, select_first, soup_of  # noqa: E402
from sniper.observe import build_observation  # noqa: E402
from sniper.rules import Signal  # noqa: E402
from sniper.semantic import filter_signals, heuristic_pass  # noqa: E402
from sniper.sessions import load_session_cookies, save_session_file  # noqa: E402
from sniper.stealth import impersonate_for, profile_headers, proxy_for  # noqa: E402
from sniper.store import Store  # noqa: E402

HTML = """
<html><head><script>var x=1;</script><style>.a{color:red}</style></head>
<body><nav>Menu Accueil Contact</nav>
<div class="pub">PROMO casino !!! compteur 12345</div>
<div id="product">
  <h1>Groupe électrogène 6.5 kVA insonorisé</h1>
  <span class="old-price">250 000 FCFA</span>
  <span class="price-current">185 000 FCFA</span>
  <p>Vendeur : +237 6 12 34 56 78 — Douala, Akwa</p>
  <button>Ajouter au panier</button>
</div>
<footer>© 2026 date du jour</footer></body></html>
"""

WATCH = {"id": "gene", "name": "Groupe électrogène", "ville": "Douala",
         "url": "https://example.com/annonce/123",
         "extract": {
             "zone_css_chain": [".inexistant", "#product"],
             "price_css_chain": [".product-price", ".price-current"],
             "stock_present": "ajouter au panier",
             "seller_phone_regex": r"(\+237[\d\s]{9,})",
         }}


class FakeResult:
    def __init__(self, text="", json=None):
        self.text, self.json = text, json


# ── 1. Sélecteurs auto-réparables ───────────────────────────────
def test_healing_chain():
    soup = soup_of(HTML)
    used, txt = select_first(soup, [".product-price", ".price-current"])
    assert used == ".price-current" and "185 000" in txt
    # sélecteur invalide -> ignoré, pas de crash
    used, txt = select_first(soup, ["[[[", ".price-current"])
    assert used == ".price-current"


def test_selector_stats():
    st = Store()
    st.record_selector("w", ".a", False)
    st.record_selector("w", ".a", False)
    st.record_selector("w", ".b", True)
    rep = st.selector_report("w")
    assert rep[0]["selector"] == ".b" and rep[0]["ok"] == 1
    assert rep[1]["fail"] == 2


def test_semantic_price_fallback():
    # sans aucun sélecteur valide, le repli trouve 185 000 (proche du titre, avec unité)
    assert best_price("Groupe électrogène 6.5 kVA insonorisé, prix total 185 000 FCFA") == 185000
    cands = find_price_candidates("vieux modèle 2019, prix 32 500 FCFA")
    assert cands[0][0] == 32500  # l'année 2019 est déclassée


# ── 2. Zones DOM ────────────────────────────────────────────────
def test_zone_extraction():
    used, zone = extract_zone(soup_of(HTML), [".inexistant", "#product"])
    assert used == "#product" and "185 000" in zone and "casino" not in zone


def test_zone_elimine_fausses_alertes():
    """Un changement hors zone ne modifie pas le hash observé."""
    o1 = build_observation(WATCH, FakeResult(HTML), Store())
    html2 = HTML.replace("compteur 12345", "compteur 99999").replace("date du jour", "8 sept")
    o2 = build_observation(WATCH, FakeResult(html2), Store())
    assert o1["zone_ok"] and o1["hash"] == o2["hash"]
    html3 = HTML.replace("185 000 FCFA", "175 000 FCFA")  # changement DANS la zone
    o3 = build_observation(WATCH, FakeResult(html3), Store())
    assert o3["hash"] != o1["hash"] and o3["price"] == 175000


def test_observation_complete():
    st = Store()
    obs = build_observation(WATCH, FakeResult(HTML), st)
    assert obs["price"] == 185000
    assert obs["stock"] is True
    assert obs["seller_phone"] == "+237612345678"
    assert obs["selector_used"] == ".price-current"
    assert len(st.selector_report("gene")) >= 2


# ── 3. Nettoyage HTML ───────────────────────────────────────────
def test_cleaner():
    txt = clean_html_to_text(HTML)
    assert "185 000 FCFA" in txt and "var x=1" not in txt and "Menu" not in txt
    assert compression_ratio(HTML) < 0.5  # volume fortement réduit


# ── 4. Filtre sémantique heuristique ────────────────────────────
CRIT = {"must_include": ["groupe électrogène"],
        "must_exclude": ["pièces détachées", "réparation"],
        "numeric": [{"pattern": r"([\d.,]+)\s*kva", "op": ">=", "value": 5}],
        "max_price": 200000}


def _sig(title="Baisse"):
    return Signal("gene", "drop_pct", title, detail={"prix": 185000})


def test_semantic_pass():
    obs = {"price": 185000, "text": "Groupe électrogène 6.5 kVA insonorisé, 185 000 FCFA"}
    ok, raison = heuristic_pass(CRIT, obs, _sig())
    assert ok, raison


def test_semantic_block_puissance():
    obs = {"price": 150000, "text": "Groupe électrogène 2.5 kVA essence"}
    ok, raison = heuristic_pass(CRIT, obs, _sig())
    assert not ok and "2.5" in raison


def test_semantic_block_prix_et_exclu():
    assert not heuristic_pass(CRIT, {"price": 210000, "text": "Groupe électrogène 8 kVA"}, _sig())[0]
    assert not heuristic_pass(
        CRIT, {"price": 50000, "text": "Pièces détachées groupe électrogène"}, _sig())[0]


def test_semantic_gate_applies_to():
    w = {"id": "gene", "ville": "Douala", "semantic": {
        "backend": "heuristic", "criteria": CRIT, "applies_to": ["drop_pct"]}}
    obs = {"price": 150000, "text": "Groupe électrogène 2.5 kVA"}
    sigs = [Signal("gene", "drop_pct", "Baisse"), Signal("gene", "changed", "Modif")]
    out = asyncio.run(filter_signals(w, obs, sigs))
    assert [s.rule for s in out] == ["changed"]  # drop filtré, changed hors scope


# ── 5. Boutons one-click ────────────────────────────────────────
def test_actions_card_whatsapp():
    al = Alerter({"telegram": {"dashboard_url": "http://dash:8501"}})
    w = {"id": "g", "name": "Gene 6.5kVA", "ville": "Douala", "url": "https://ex.com/a",
         "actions_card": {
             "wa_text": "Bonjour, '{watch}' à {prix} XAF m'intéresse. Dispo ?",
             "buttons": [
                 {"label": "💬 WhatsApp vendeur", "requires": "seller_phone",
                  "url": "https://wa.me/{seller_phone_digits}?text={wa_text}"},
                 {"label": "🔗 Voir", "url": "{url}"}]}}
    sig = Signal("g", "below", "Sous seuil", detail={"prix": 185000, "seller_phone": "+237 6 12 34 56 78"})
    kb = al.keyboard(w, sig)["inline_keyboard"]
    assert kb[0][0]["url"].startswith("https://wa.me/237612345678?text=Bonjour")
    assert "%20" in kb[0][0]["url"] or "%27" in kb[0][0]["url"]  # texte encodé
    assert any("Dashboard" in b["text"] for row in kb for b in row)
    # sans numéro : bouton WhatsApp masqué, pas de lien cassé
    sig2 = Signal("g", "below", "Sous seuil", detail={"prix": 185000})
    kb2 = al.keyboard(w, sig2)["inline_keyboard"]
    assert all("WhatsApp" not in b["text"] for row in kb2 for b in row)


# ── 6. Sessions & stealth ───────────────────────────────────────
def test_session_roundtrip(tmp_path):
    p = str(tmp_path / "fb.json")
    save_session_file(p, "facebook.com", [{"name": "c_user", "value": "123"}])
    assert load_session_cookies(p) == {"c_user": "123"}
    assert load_session_cookies(str(tmp_path / "absent.json")) == {}


def test_stealth_rotation():
    w = {"stealth": {"profile": "rotate"}}
    assert "Pixel" not in profile_headers(w, 0)["User-Agent"]
    assert "Pixel" in profile_headers(w, 1)["User-Agent"]
    assert profile_headers({"stealth": {"profile": "off"}}, 0) == {}
    g, w2 = {"proxies": ["p1", "p2"]}, {"stealth": {}}
    assert proxy_for(g, w2, 0) == "p1" and proxy_for(g, w2, 3) == "p2"
    assert proxy_for({}, {}, 0) is None
    assert impersonate_for({"stealth": {"impersonate": "chrome124"}}) == "chrome124"
