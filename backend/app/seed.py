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

MARCHES = [  # (nom, ville, pays, lat, lon)
    ("Marché Central", "Douala", "CM", 4.048, 9.704),
    ("Mboppi", "Douala", "CM", 4.058, 9.732),
    ("Marché Mokolo", "Yaoundé", "CM", 3.873, 11.502),
    ("Marché Mfoundi", "Yaoundé", "CM", 3.866, 11.522),
    ("Marché A", "Bafoussam", "CM", 5.478, 10.417),
    ("Food Market", "Bamenda", "CM", 5.963, 10.159),
    ("Marché central", "Garoua", "CM", 9.301, 13.397),
    ("Marché central", "Maroua", "CM", 10.591, 14.321),
    ("Marché central", "Ngaoundéré", "CM", 7.321, 13.575),
    ("Marché central", "Bertoua", "CM", 4.579, 13.684),
    ("Marché central", "Ebolowa", "CM", 2.917, 11.151),
    ("Marché central", "Kribi", "CM", 2.939, 9.909),
    ("Mile 4 Market", "Limbé", "CM", 4.024, 9.214),
    ("Marché central", "Buéa", "CM", 4.155, 9.242),
    ("Marché central", "Kumba", "CM", 4.633, 9.446),
    ("Poto-Poto", "Brazzaville", "CG", -4.255, 15.256),
    ("Marché Total", "Brazzaville", "CG", -4.263, 15.242),
    ("Mont-Bouët", "Libreville", "GA", 0.394, 9.451),
    ("Marché Central", "NDjamena", "TD", 12.134, 15.055),
    ("Marché Dembé", "NDjamena", "TD", 12.105, 15.085),
    ("PK5", "Bangui", "CF", 4.365, 18.554),
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

    for nom, ville, pays, lat, lon in MARCHES:
        if not session.query(Marche).filter_by(nom=nom, ville=ville).first():
            session.add(Marche(nom=nom, ville=ville, pays=pays, lat=lat, lon=lon))
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

    from .services.deals import creer_deal
    _src = {s.nom: s.id for s in session.query(Source).all()}
    _prd = {p.sku: p.id for p in session.query(Produit).all()}
    for titre, sku, src, prix, ville, url, phone, statut in [
        ("Congélateur Hisense 200L — destockage Akwa", "CONGEL-200L", "CoinAfrique",
         145000, "Douala", "https://www.coinafrique.com/annonce/demo-congel", "699123456", "nouveau"),
        ("Riz parfumé 50kg — lot Mokolo", "RIZ-PARF-50KG", "Relevés terrain Kobo",
         26500, "Yaoundé", None, None, "nouveau"),
        ("Tecno Spark 10 — boutique Deïdo", "SMART-ENTRY", "Jumia Cameroun",
         48000, "Douala", "https://www.jumia.cm/demo-tecno", None, "nouveau"),
        ("Huile Mayor 1L × carton — Mboppi", "HUILE-VEG-1L", "Relevés terrain Kobo",
         1650, "Douala", None, "690112233", "contacte"),
        ("Sucre Sosucam — sac 50kg Mfoundi", "SUCRE-1KG", "Relevés terrain Kobo",
         820, "Yaoundé", None, None, "contacte"),
        ("Ciment Dangote — chantier Odza", "CIMENT-50KG", "Relevés terrain Kobo",
         5200, "Yaoundé", None, None, "conclu"),
    ]:
        creer_deal(session, titre=titre, prix=prix, ville=ville,
                   produit_id=_prd[sku], source_id=_src.get(src),
                   preuve_url=url, phone=phone, statut=statut,
                   meta={"origine": "seed-demo"})
    return {"status": "seeded", "releves": n_rel,
            "commentaires": len(COMMENTAIRES),
            "alertes": [a.titre for a in alertes], "deals": 6}


def seed_if_empty() -> None:
    s = SessionLocal()
    try:
        res = seed_all(s)
        log.warning("Seed démo : %s", res)
    finally:
        s.close()
