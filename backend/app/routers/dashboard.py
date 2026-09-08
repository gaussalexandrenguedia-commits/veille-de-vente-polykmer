"""Agrégats pour l'application web : synthèse dashboard + courbes de prix."""
from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Alerte, Produit, RelevePrix, Source
from ..services.kpi import _aware, taux_rupture, variation
from ..services.normalize import resolve_produit

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _courbe(db: Session, produit_id: int, jours: int) -> dict[str, list[dict]]:
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    rows = db.query(RelevePrix.ville, RelevePrix.prix, RelevePrix.observe_le).filter(
        RelevePrix.produit_id == produit_id,
        RelevePrix.observe_le >= depuis,
        RelevePrix.rupture.is_(False)).all()
    par_ville_jour: dict[tuple[str, str], list[float]] = defaultdict(list)
    for ville, prix, quand in rows:
        jour = (_aware(quand) or dt.datetime.now(dt.timezone.utc)).date().isoformat()
        par_ville_jour[(ville, jour)].append(float(prix))
    series: dict[str, list[dict]] = defaultdict(list)
    for (ville, jour), vals in sorted(par_ville_jour.items()):
        series[ville].append({"date": jour, "prix": round(statistics.median(vals))})
    return dict(series)


@router.get("/courbe")
def courbe(produit: str = "RIZ-PARF-50KG", jours: int = 30,
            db: Session = Depends(get_db)):
    p = resolve_produit(db, produit)
    if not p:
        raise HTTPException(404, f"Produit introuvable : {produit!r}")
    series = _courbe(db, p.id, jours)
    medianes = {v: pts[-1]["prix"] for v, pts in series.items() if pts}
    return {"produit": p.nom, "sku": p.sku, "unite": p.unite,
            "jours": jours, "series": series, "dernieres_medianes": medianes}


@router.get("/summary")
def summary(produit: str = "RIZ-PARF-50KG", jours: int = 30,
            db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    sem = now - dt.timedelta(days=7)
    base7 = db.query(RelevePrix).filter(RelevePrix.observe_le >= sem)
    total = base7.count()
    rupt = base7.filter(RelevePrix.rupture.is_(True)).count() if total else 0
    promo = base7.filter(RelevePrix.promo.is_(True)).count() if total else 0
    momo = base7.filter(RelevePrix.paiement_momo.is_(True)).count() if total else 0

    variations = []
    for p in db.query(Produit).all():
        v = variation(db, p.id)
        if v:
            variations.append({"sku": p.sku, "produit": p.nom,
                               "categorie": p.categorie, **v})
    variations.sort(key=lambda x: abs(x["variation_pct"]), reverse=True)

    ruptures = []
    for p in db.query(Produit).filter(Produit.traceur.is_(True)).all():
        t = taux_rupture(db, p.id)
        if t is not None:
            ruptures.append({"sku": p.sku, "produit": p.nom, "taux": t})
    ruptures.sort(key=lambda x: x["taux"], reverse=True)

    promos_ville = [
        {"ville": v, "pct": round(n_promo / n * 100, 1)}
        for v, n, n_promo in
        db.query(RelevePrix.ville, func.count(),
                 func.sum(func.cast(RelevePrix.promo, selec_integer())))
        .filter(RelevePrix.observe_le >= sem).group_by(RelevePrix.ville).all()
        for n in [n] if n
    ]
    couverture = [
        {"source": nom, "n": n}
        for nom, n in db.query(Source.nom, func.count())
        .join(RelevePrix, RelevePrix.source_id == Source.id)
        .filter(RelevePrix.observe_le >= sem)
        .group_by(Source.nom).order_by(func.count().desc()).all()
    ]
    alertes = [
        {"id": a.id, "type": a.type, "gravite": a.gravite, "titre": a.titre}
        for a in db.query(Alerte).filter(Alerte.resolu.is_(False))
        .order_by(Alerte.id.desc()).limit(10).all()
    ]
    p = resolve_produit(db, produit)
    return {
        "releves_7j": total,
        "rupture_pct": round(rupt / total * 100, 1) if total else 0,
        "promo_pct": round(promo / total * 100, 1) if total else 0,
        "momo_pct": round(momo / total * 100, 1) if total else 0,
        "variations": variations[:12],
        "ruptures": ruptures,
        "promos_ville": sorted(promos_ville, key=lambda x: x["pct"], reverse=True),
        "couverture": couverture,
        "alertes": alertes,
        "courbe": {"produit": p.nom, "sku": p.sku, "unite": p.unite,
                   "series": _courbe(db, p.id, jours)} if p else None,
    }


def selec_integer():
    """func.cast(..., Integer) multi-bases (évite l'import circulaire)."""
    from sqlalchemy import Integer
    return Integer
