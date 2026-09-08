"""Sentiment v0.1 — lexique FR + pidgin camerounais + anglais.

Score -100..+100. Remplacé par un modèle NLP en phase 2.
"""
from __future__ import annotations

POSITIFS = {
    "bon", "bonne", "super", "genial", "génial", "merci", "parfait", "top",
    "satisfait", "rapide", "propre", "neuf", "solide", "moins cher", "cadeau",
    "nice", "good", "great", "thanks", "thank", "perfect",
    "correct", "ok", "bien", "joli", "magnifique", "recommande", "recommandé",
}
NEGATIFS = {
    "mauvais", "nulle", "nul", "arnaque", "escroc", "faux", "fake", "cher",
    "trop cher", "voleur", "volé", "cassé", "casse", "panne", "retard",
    "jamais", "déçu", "decu", "plainte", "méfiez", "attention", "fuyez",
    "bad", "scam", "cheat", "broken", "late", "expensive", "poor",
    "pourri", "honte", "pitié", "pite", "ordure",
}
MOTIFS = {
    "prix": {"cher", "prix", "augment", "expensive", "coute"},
    "qualite": {"qualite", "casse", "cassé", "faux", "fake", "panne", "pourri"},
    "livraison": {"livraison", "retard", "jamais recu", "colis", "late", "delivery"},
    "sav": {"sav", "garantie", "retour", "rembours", "refund"},
    "arnaque": {"arnaque", "escroc", "voleur", "scam", "fuyez", "attention"},
    "rupture": {"rupture", "stock", "plus dispo", "indisponible", "out of stock"},
}


def score_sentiment(texte: str) -> tuple[int, str | None]:
    t = texte.lower()
    pos = sum(1 for w in POSITIFS if w in t)
    neg = sum(1 for w in NEGATIFS if w in t)
    total = pos + neg
    score = 0 if total == 0 else round((pos - neg) / total * 100)
    motif = None
    for m, mots in MOTIFS.items():
        if any(w in t for w in mots):
            motif = m
            break
    return score, motif
