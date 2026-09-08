"""Relevés de prix : création (terrain/manuel) + consultation séries."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Marche, Produit, RelevePrix, Source
from ..schemas import ReleveIn, ReleveOut
from ..services.normalize import dedup_key, hash_vendeur, resolve_produit
from ..services.kpi import serie_prix

router = APIRouter(prefix="/api/v1", tags=["relevés"])


@router.post("/releves", response_model=ReleveOut, status_code=201)
def create_releve(body: ReleveIn, db: Session = Depends(get_db)):
    produit = resolve_produit(db, body.produit)
    if not produit:
        raise HTTPException(404, f"Produit introuvable : {body.produit!r} (vérifiez SKU/nom/alias)")
    source = db.query(Source).filter(func.lower(Source.nom) == body.source.lower()).first()
    if not source:
        raise HTTPException(404, f"Source introuvable : {body.source!r}")
    marche = None
    if body.marche:
        marche = db.query(Marche).filter(
            func.lower(Marche.nom) == body.marche.lower(),
            func.lower(Marche.ville) == body.ville.lower()).first()
        if not marche:  # marché libre (nouveau point de vente) -> on l'accepte sans FK
            pass
    observe = body.observe_le or dt.datetime.now(dt.timezone.utc)
    r = RelevePrix(
        produit_id=produit.id, source_id=source.id,
        marche_id=marche.id if marche else None,
        prix=body.prix, prix_gros=body.prix_gros, ville=body.ville,
        pays=body.pays.upper(), vendeur_hash=hash_vendeur(body.vendeur, body.source),
        marque=body.marque, origine=body.origine, rupture=body.rupture,
        promo=body.promo, promo_detail=body.promo_detail,
        paiement_momo=body.paiement_momo, methode=body.methode,
        preuve_url=body.preuve_url, observe_le=observe, collecteur=body.collecteur,
    )
    # Déduplication souple : même produit/vendeur/prix/jour/source -> 409
    jour = observe.date().isoformat()
    key = dedup_key(produit.id, r.vendeur_hash, body.prix, jour, source.id)
    doublon = db.query(RelevePrix).filter(
        RelevePrix.produit_id == produit.id, RelevePrix.source_id == source.id,
        RelevePrix.prix == body.prix, func.date(RelevePrix.observe_le) == observe.date(),
    ).first()
    if doublon and (doublon.vendeur_hash or None) == r.vendeur_hash:
        raise HTTPException(409, f"Doublon probable (clé {key})")
    db.add(r)
    db.commit()
    db.refresh(r)
    return ReleveOut(**body.model_dump(), id=r.id, produit_id=produit.id, produit_nom=produit.nom)


@router.get("/prix")
def get_prix(produit: str, ville: str | None = None, jours: int = 30,
             db: Session = Depends(get_db)):
    p = resolve_produit(db, produit)
    if not p:
        raise HTTPException(404, f"Produit introuvable : {produit!r}")
    return {"produit": p.nom, "sku": p.sku, "ville": ville, "jours": jours,
            "serie": serie_prix(db, p.id, ville, jours)}


@router.get("/releves/recent")
def recent_releves(limit: int = 50, db: Session = Depends(get_db)):
    rows = (db.query(RelevePrix, Produit.nom, Produit.sku, Source.nom, Marche.nom)
            .join(Produit, RelevePrix.produit_id == Produit.id)
            .join(Source, RelevePrix.source_id == Source.id)
            .outerjoin(Marche, RelevePrix.marche_id == Marche.id)
            .order_by(RelevePrix.observe_le.desc()).limit(min(limit, 200)).all())
    return [{"id": r.id, "date": r.observe_le.isoformat(), "produit": nom,
             "sku": sku, "ville": r.ville, "marche": marche,
             "source": src, "prix": float(r.prix), "promo": r.promo,
             "rupture": r.rupture, "marque": r.marque, "methode": r.methode}
            for r, nom, sku, src, marche in rows]
