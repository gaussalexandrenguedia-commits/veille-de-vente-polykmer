"""Tests deals : scoring marché, statuts, dédup, depuis-texte."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base  # noqa: E402
from app.models import Opportunite, Produit  # noqa: E402
from app.seed import seed_all  # noqa: E402
from app.services.deals import (changer_statut, creer_deal,  # noqa: E402
                                creer_deal_depuis_texte, match_produit,
                                score_prix)


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    eng = create_engine(f"sqlite:///{tmp_path_factory.mktemp('deals')}/t.db")
    Base.metadata.create_all(eng)
    s = sessionmaker(bind=eng)()
    assert seed_all(s)["status"] == "seeded"
    yield s
    s.close()


def test_seed_cree_deals(db):
    assert db.query(Opportunite).count() >= 6


def test_score_prix_reel(db):
    congel = db.query(Produit).filter_by(sku="CONGEL-200L").first()
    sc = score_prix(db, congel.id, 145000, "Douala")
    assert sc["mediane"] and sc["ecart_pct"] < -10
    assert sc["verdict"] in ("prioritaire", "interessant")
    assert sc["score"] >= 70


def test_sans_ref(db):
    tv = db.query(Produit).filter_by(sku="TV-32").first()
    sc = score_prix(db, tv.id, 95000, "Douala")
    assert sc["verdict"] == "sans_ref"  # pas d'historique TV dans le seed


def test_statuts(db):
    d = creer_deal(db, titre="Test statut", prix=1000, ville="Douala")
    assert d.statut == "nouveau"
    assert changer_statut(db, d.id, "contacte").statut == "contacte"
    assert changer_statut(db, d.id, "conclu", notes="vendu").notes == "vendu"
    assert changer_statut(db, d.id, "nouveau").statut == "nouveau"  # rouverture
    with pytest.raises(ValueError):
        changer_statut(db, d.id, "perdu")
    with pytest.raises(LookupError):
        changer_statut(db, 999999, "conclu")


def test_dedupe_url(db):
    a = creer_deal(db, titre="A", prix=5000, ville="Douala",
                   preuve_url="https://ex.com/annonce/1")
    b = creer_deal(db, titre="B", prix=5000, ville="Douala",
                   preuve_url="https://ex.com/annonce/1")
    assert a.id == b.id  # même URL ouverte -> pas de doublon


def test_match_produit(db):
    assert match_produit(db, "Congélateur Hisense 200 L").sku == "CONGEL-200L"
    assert match_produit(db, "riz parfumé sac").sku == "RIZ-PARF-50KG"
    assert match_produit(db, "tecno spark 10").sku == "SMART-ENTRY"


def test_depuis_texte_local(db):
    d, parsed = creer_deal_depuis_texte(
        db, "Congélateur Hisense 200L sous carton 175 kolos Akwa last price 690112233",
        url="https://ex.com/gene-test")
    assert parsed["prix"] == 175000
    assert parsed["ville"] == "Douala" and parsed["quartier"] == "akwa"
    assert parsed["prix_ferme"] is True and parsed["etat"] == "neuf"
    assert parsed["phone"] == "690112233"
    assert d.ville == "Douala" and d.phone == "690112233"
    assert d.produit_id is not None  # matché via mot-clé congel
    assert d.ecart_pct is not None


def test_collecte_match_titre_sans_sku(db):
    """Régression : les scrapers n'envoient pas de SKU — le matching par
    titre doit quand même créer relevé + deal auto."""
    from app.services.collecte import stocker_offres
    res = stocker_offres(db, [{
        "source": "Jumia Cameroun", "produit": None, "prix": 139000,
        "ancien_prix": 195000, "ville": "Douala",
        "titre": "Congélateur Hisense 200L",
        "url": "https://test-regression.cm/c1"}])
    assert res["offres_inserees"] == 1
    assert res["releves_prix_crees"] == 1, res
    assert len(res["deals_crees"]) == 1, res  # -27 % vs médiane
    # doublon URL : rien de nouveau
    res2 = stocker_offres(db, [{
        "source": "Jumia Cameroun", "produit": None, "prix": 139000,
        "ville": "Douala", "titre": "Congélateur Hisense 200L",
        "url": "https://test-regression.cm/c1"}])
    assert res2["offres_inserees"] == 0 and res2["deals_crees"] == []
