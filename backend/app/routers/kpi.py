"""KPIs : variations, ruptures, alertes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alerte, Produit
from ..services.kpi import generer_alertes, taux_rupture, variation
from ..services.normalize import resolve_produit

router = APIRouter(prefix="/api/v1/kpi", tags=["kpi"])


@router.get("/variations")
def kpi_variations(seuil: float = 5.0, ville: str | None = None,
                   db: Session = Depends(get_db)):
    out = []
    for p in db.query(Produit).all():
        v = variation(db, p.id, ville)
        if v and abs(v["variation_pct"]) >= seuil:
            out.append({"sku": p.sku, "produit": p.nom,
                        "categorie": p.categorie, **v})
    return sorted(out, key=lambda x: abs(x["variation_pct"]), reverse=True)


@router.get("/ruptures")
def kpi_ruptures(db: Session = Depends(get_db)):
    out = []
    for p in db.query(Produit).filter(Produit.traceur.is_(True)).all():
        t = taux_rupture(db, p.id)
        if t is not None:
            out.append({"sku": p.sku, "produit": p.nom, "taux_rupture_pct": t})
    return sorted(out, key=lambda x: x["taux_rupture_pct"], reverse=True)


@router.get("/alertes")
def list_alertes(gravite: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Alerte).filter(Alerte.resolu.is_(False))
    if gravite:
        q = q.filter(Alerte.gravite == gravite)
    return [{"id": a.id, "type": a.type, "gravite": a.gravite, "titre": a.titre,
             "detail": a.detail, "produit_id": a.produit_id}
            for a in q.order_by(Alerte.id.desc()).limit(100).all()]


@router.post("/alertes/generer")
def run_alertes(seuil: float = 10.0, db: Session = Depends(get_db)):
    creees = generer_alertes(db, seuil)
    return {"nouvelles_alertes": len(creees),
            "titres": [a.titre for a in creees]}
