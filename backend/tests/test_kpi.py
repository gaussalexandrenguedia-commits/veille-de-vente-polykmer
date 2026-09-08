"""Tests unitaires (sans base) : médiane pondérée + sentiment."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.kpi import mediane_ponderee  # noqa: E402
from app.services.sentiment import score_sentiment  # noqa: E402


def test_mediane_ponderee_terrain_x2():
    # terrain compte double : médiane de [100,100,200] = 100
    assert mediane_ponderee([(100, "terrain"), (200, "scrape")]) == 100


def test_mediane_vide():
    assert mediane_ponderee([]) is None


def test_sentiment_positif():
    score, _ = score_sentiment("Super produit, livraison rapide, merci !")
    assert score > 0


def test_sentiment_arnaque():
    score, motif = score_sentiment("Attention arnaque, vendeur voleur, fuyez !")
    assert score < 0
    assert motif == "arnaque"
