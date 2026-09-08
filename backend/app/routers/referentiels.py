"""Référentiels : produits, marchés, sources, corridors."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Marche, Produit, Source

router = APIRouter(prefix="/api/v1", tags=["référentiels"])


@router.get("/produits")
def list_produits(traceur: bool | None = None, db: Session = Depends(get_db)):
    q = db.query(Produit)
    if traceur is not None:
        q = q.filter(Produit.traceur == traceur)
    return [
        {"id": p.id, "sku": p.sku, "nom": p.nom, "categorie": p.categorie,
         "unite": p.unite, "marques_suivies": p.marques_suivies, "traceur": p.traceur}
        for p in q.order_by(Produit.categorie, Produit.nom).all()
    ]


@router.get("/marches")
def list_marches(pays: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Marche)
    if pays:
        q = q.filter(Marche.pays == pays.upper())
    return [{"id": m.id, "nom": m.nom, "ville": m.ville, "pays": m.pays,
             "lat": m.lat, "lon": m.lon} for m in q.all()]


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    return [{"id": s.id, "nom": s.nom, "type": s.type,
             "frequence": s.frequence, "actif": s.actif}
            for s in db.query(Source).all()]
