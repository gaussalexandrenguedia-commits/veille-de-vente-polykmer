"""Seed démo : référentiels + relevés CSV + commentaires + alertes.

Idempotent : si des relevés existent déjà, ne fait rien.
Utilisé au démarrage en mode SQLite (zéro config) et dans les tests.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging

from .config import ROOT_DIR
from .database import SessionLocal
from .models import (Commentaire, Corridor, Marche, Produit, RelevePrix,
                     Source)
from .services.kpi import generer_alertes
from .services.sentiment import score_sentiment

log = logging.getLogger("seed")
CSV = ROOT_DIR / "data" / "samples" / "prix_exemple.csv"
UTC = dt.timezone.utc

MARCHES = [
    ("Marché Central", "Douala", "CM"), ("Mboppi", "Douala", "CM"),
    ("Marché Mokolo", "Yaoundé", "CM"), ("Marché Mfoundi", "Yaoundé", "CM"),
    ("Marché A", "Bafoussam", "CM"), ("Poto-Poto", "Brazzaville", "CG"),
    ("Marché Central", "NDjamena", "TD"),
]
SOURCES = [
    ("Jumia Cameroun", "ecommerce"), ("CoinAfrique", "ecommerce"),
    ("Glotelho", "ecommerce"), ("Relevés terrain Kobo", "terrain"),
    ("Panel Facebook", "facebook"), ("Canaux Telegram", "telegram"),
]
PRODUITS = [
    ("RIZ-PARF-50KG", "Riz parfumé 50 kg", "Alimentaire", "sac 50kg", ["Mémé", "Broli"], True),
    ("HUILE-VEG-1L", "Huile végétale 1 L", "Alimentaire", "bouteille 1L", ["Mayor", "Diamaor"], True),
    ("SUCRE-1KG", "Sucre en poudre 1 kg", "Alimentaire", "kg", ["Sosucam"], True),
    ("CIMENT-50KG", "Ciment 50 kg", "Matériaux", "sac 50kg", ["Cimencam", "Dangote"], True),
    ("CONGEL-200L", "Congélateur 200 L", "Électroménager", "pièce", ["Hisense", "Nasco"], False),
    ("TV-32", "Téléviseur 32 pouces", "Électroménager", "pièce", ["Hisense", "TCL"], False),
    ("SMART-ENTRY", "Smartphone entrée de gamme 64 Go", "Téléphonie", "pièce", ["Tecno", "Itel", "Redmi"], True),
]
CORRIDORS = [
    ("Douala-Bangui", "Douala", "Bangui", 1450),
    ("Douala-Ndjamena", "Douala", "NDjamena", 1850),
    ("Douala-Brazzaville", "Douala", "Brazzaville", 1500),
    ("Kribi-Yaoundé", "Kribi", "Yaoundé", 175),
]

# (source, texte, langue, jours_avant) — FR + pidgin + EN, réalistes
COMMENTAIRES = [
    ("Panel Facebook", "Le prix du riz a encore augmenté à Mokolo, c'est grave. 32 000 le sac maintenant !", "fr", 1),
    ("Panel Facebook", "Super congélateur Hisense, livraison rapide à Douala, merci au vendeur !", "fr", 1),
    ("Panel Facebook", "Attention arnaque, le vendeur demande orange money avant livraison et disparaît. Fuyez !", "fr", 2),
    ("Panel Facebook", "Huile Mayor 5L à bon prix chez le grossiste de Mboppi, je recommande", "fr", 2),
    ("Canaux Telegram", "Arrivage Tecno Spark ce matin, stock limité, premier arrivé premier servi", "fr", 3),
    ("Panel Facebook", "This seller na thief, e collect my momo for TV wey e never deliver", "pidgin", 3),
    ("Panel Facebook", "Ciment Dangote en rupture partout à Yaoundé, quelqu'un a un contact ?", "fr", 4),
    ("Panel Facebook", "Très déçu, le congélateur est tombé en panne après 2 semaines, SAV injoignable", "fr", 4),
    ("Canaux Telegram", "New stock Samsung chargers and covers, wholesale prices Douala", "en", 5),
    ("Panel Facebook", "Sucre Sosucam moins cher au marché Mfoundi qu'en boutique, allez-y tôt le matin", "fr", 5),
    ("Panel Facebook", "Livraison Glovo en retard de 3h, colis arrivé ouvert. Honteux.", "fr", 6),
    ("Panel Facebook", "Bon plan : TV TCL 32 pouces à 95 000, vendeur sérieux à Akwa", "fr", 6),
    ("Canaux Telegram", "Prix du sac de riz stabilisé à 29 000 chez les importateurs cette semaine", "fr", 7),
    ("Panel Facebook", "Méfiez-vous des faux Redmi, vérifiez le code IMEI avant de payer", "fr", 7),
    ("Panel Facebook", "Excellent service, paiement MoMo accepté et garantie 6 mois incluse", "fr", 8),
    ("Panel Facebook", "Trop cher ! Le même modèle se vend 10 000 moins cher à Bafoussam", "fr", 8),
    ("Canaux Telegram", "Rupture huile Diamaor signalée sur l'axe Douala-Yaoundé, restock prévu lundi", "fr", 9),
    ("Panel Facebook", "Vendeur correct, produit neuf et bien emballé, je reviendrai", "fr", 9),
    ("Panel Facebook", "E don cost too much, bag of rice na today 32k? We dey suffer for this country", "pidgin", 10),
    ("Panel Facebook", "Qualité top pour le prix, congélateur silencieux et économique", "fr", 10),
    ("Panel Facebook", "Commande jamais reçue après 2 semaines, le vendeur ne répond plus. Plainte déposée.", "fr", 11),
    ("Canaux Telegram", "Promo rentrée : -10% sur tout l'électroménager si paiement Orange Money", "fr", 11),
    ("Panel Facebook", "Farine en hausse aussi, le pain va encore augmenter…", "fr", 12),
    ("Panel Facebook", "Good phone for the price, battery lasts two days. Seller delivered same day.", "en", 12),
]


def seed_all(session) -> dict:
    if session.query(RelevePrix).count() > 0:
        return {"status": "exists"}

    for nom, ville, pays in MARCHES:
        if not session.query(Marche).filter_by(nom=nom, ville=ville).first():
            session.add(Marche(nom=nom, ville=ville, pays=pays))
    for nom, typ in SOURCES:
        if not session.query(Source).filter_by(nom=nom).first():
            session.add(Source(nom=nom, type=typ))
    for sku, nom, cat, unite, marques, traceur in PRODUITS:
        if not session.query(Produit).filter_by(sku=sku).first():
            session.add(Produit(sku=sku, nom=nom, categorie=cat, unite=unite,
                                marques_suivies=marques, traceur=traceur))
    for nom, ori, dst, km in CORRIDORS:
        if not session.query(Corridor).filter_by(nom=nom).first():
            session.add(Corridor(nom=nom, origine=ori, destination=dst, distance_km=km))
    session.commit()

    produits = {p.sku: p.id for p in session.query(Produit).all()}
    sources = {s.nom: s.id for s in session.query(Source).all()}
    marches = {(m.nom, m.ville): m.id for m in session.query(Marche).all()}

    n_rel = 0
    if CSV.exists():
        with open(CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["sku"] not in produits:
                    continue
                sid = sources.get(row["source"])
                if not sid:
                    s = Source(nom=row["source"], type="terrain" if row["methode"] == "terrain" else "ecommerce")
                    session.add(s)
                    session.commit()
                    sid = sources[row["source"]] = s.id
                y, m, d = map(int, row["date"].split("-"))
                session.add(RelevePrix(
                    produit_id=produits[row["sku"]], source_id=sid,
                    marche_id=marches.get((row["marche"], row["ville"])),
                    prix=float(row["prix"]), ville=row["ville"],
                    marque=row["marque"] or None, origine=row["origine"] or None,
                    rupture=row["rupture"] == "1", promo=row["promo"] == "1",
                    promo_detail=row["promo_detail"] or None,
                    paiement_momo=row["paiement_momo"] == "1",
                    methode=row["methode"], collecteur="seed-demo",
                    observe_le=dt.datetime(y, m, d, 12, tzinfo=UTC)))
                n_rel += 1
        session.commit()

    now = dt.datetime.now(UTC)
    for i, (src, texte, langue, jours) in enumerate(COMMENTAIRES):
        score, motif = score_sentiment(texte)
        session.add(Commentaire(source_id=sources[src], texte=texte, langue=langue,
                                auteur_hash=f"demo-{i:03d}",
                                sentiment_score=score, motif=motif,
                                capture_le=now - dt.timedelta(days=jours, hours=i)))
    session.commit()

    alertes = generer_alertes(session, 10.0)
    return {"status": "seeded", "releves": n_rel,
            "commentaires": len(COMMENTAIRES),
            "alertes": [a.titre for a in alertes]}


def seed_if_empty() -> None:
    s = SessionLocal()
    try:
        res = seed_all(s)
        log.warning("Seed démo : %s", res)
    finally:
        s.close()
