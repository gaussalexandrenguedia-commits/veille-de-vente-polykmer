"""Ingestion lots scrapers + webhook KoboToolbox (protégés par clé API)."""
import datetime as dt

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Marche, OffreDigitale, RelevePrix, Source
from ..schemas import OffreScraperIn
from ..services.normalize import hash_vendeur, resolve_produit

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


def check_key(x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY_INGEST:
        raise HTTPException(403, "Clé API invalide")
    return True


@router.post("/scraper")
def ingest_scraper(offres: list[OffreScraperIn], db: Session = Depends(get_db),
                   _ok: bool = Depends(check_key)):
    """Reçoit un lot d'offres scrapées -> table offres_digitales (+ relevé prix si produit matché)."""
    inserted, releves = 0, 0
    for o in offres:
        src = db.query(Source).filter(func.lower(Source.nom) == o.source.lower()).first()
        if not src:
            src = Source(nom=o.source, type="ecommerce")
            db.add(src)
            db.commit()
            db.refresh(src)
        if db.query(OffreDigitale).filter(OffreDigitale.url == o.url).first():
            continue
        remise = None
        if o.prix and o.ancien_prix and o.ancien_prix > o.prix:
            remise = round((o.ancien_prix - o.prix) / o.ancien_prix * 100, 1)
        db.add(OffreDigitale(source_id=src.id, url=o.url, titre=o.titre, prix=o.prix,
                             ancien_prix=o.ancien_prix, remise_pct=remise,
                             vendeur_hash=hash_vendeur(o.vendeur, o.source), ville=o.ville))
        inserted += 1
        if o.produit and o.prix:
            p = resolve_produit(db, o.produit)
            if p:
                db.add(RelevePrix(produit_id=p.id, source_id=src.id, prix=o.prix,
                                 ville=o.ville or "Douala", methode="scrape",
                                 vendeur_hash=hash_vendeur(o.vendeur, o.source),
                                 preuve_url=o.url, promo=bool(remise),
                                 observe_le=dt.datetime.now(dt.timezone.utc),
                                 collecteur=f"scraper:{src.nom}"))
                releves += 1
    db.commit()
    return {"offres_inserees": inserted, "releves_prix_crees": releves}


# Mapping champs Kobo -> API (adapter aux noms réels du formulaire)
KOBO_FIELD_MAP = {
    "produit": "produit", "product": "produit",
    "prix_detail": "prix", "prix": "prix", "price": "prix",
    "prix_gros": "prix_gros",
    "ville": "ville", "city": "ville",
    "marche": "marche", "market": "marche",
    "marque": "marque", "brand": "marque",
    "origine": "origine", "origin": "origine",
    "rupture": "rupture", "promo": "promo", "promo_detail": "promo_detail",
    "momo": "paiement_momo", "paiement_momo": "paiement_momo",
    "vendeur_code": "vendeur",
}


@router.post("/kobo")
def ingest_kobo(payload: dict, db: Session = Depends(get_db),
                _ok: bool = Depends(check_key)):
    """Webhook KoboToolbox : reçoit une soumission, la convertit en relevé terrain."""
    data = payload.get("data", payload)  # Kobo envoie parfois {"data": {...}}
    mapped: dict = {}
    for k, v in data.items():
        if k in KOBO_FIELD_MAP:
            mapped[KOBO_FIELD_MAP[k]] = v
    if "produit" not in mapped or "prix" not in mapped:
        raise HTTPException(422, f"Champs requis manquants (produit, prix). Reçu : {sorted(mapped)}")
    produit = resolve_produit(db, str(mapped["produit"]))
    if not produit:
        raise HTTPException(404, f"Produit Kobo non résolu : {mapped['produit']!r}")
    src = db.query(Source).filter(Source.nom == "Relevés terrain Kobo").first()
    marche = None
    if mapped.get("marche"):
        marche = db.query(Marche).filter(
            func.lower(Marche.nom) == str(mapped["marche"]).lower()).first()
    r = RelevePrix(
        produit_id=produit.id, source_id=src.id if src else 1,
        marche_id=marche.id if marche else None,
        prix=float(mapped["prix"]), prix_gros=mapped.get("prix_gros"),
        ville=mapped.get("ville", marche.ville if marche else "Douala"),
        vendeur_hash=hash_vendeur(mapped.get("vendeur"), "kobo"),
        marque=mapped.get("marque"), origine=mapped.get("origine"),
        rupture=str(mapped.get("rupture", "")).lower() in ("1", "true", "yes", "oui"),
        promo=str(mapped.get("promo", "")).lower() in ("1", "true", "yes", "oui"),
        promo_detail=mapped.get("promo_detail"),
        paiement_momo=str(mapped.get("paiement_momo", "")).lower() in ("1", "true", "yes", "oui"),
        methode="terrain", preuve_url=data.get("_uuid") or data.get("_id"),
        collecteur=data.get("_submitted_by") or data.get("enqueteur"),
    )
    db.add(r)
    db.commit()
    return {"ok": True, "produit": produit.nom, "prix": r.prix, "ville": r.ville}
