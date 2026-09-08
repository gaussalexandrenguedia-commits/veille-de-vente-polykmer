"""Calculs KPI — médianes pondérées, variations, ruptures, alertes."""
from __future__ import annotations

import datetime as dt
import statistics

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Alerte, Produit, RelevePrix

# Pondération : le terrain compte double (marché réel > prix affichés web)
POIDS = {"terrain": 2.0, "scrape": 1.0, "api": 1.5, "manuel": 1.0}


def mediane_ponderee(valeurs: list[tuple[float, str]]) -> float | None:
    """valeurs = [(prix, methode), ...]. Répète selon poids puis médiane."""
    if not valeurs:
        return None
    pool: list[float] = []
    for prix, methode in valeurs:
        pool.extend([prix] * int(POIDS.get(methode, 1)))
    return float(statistics.median(pool))


def serie_prix(db: Session, produit_id: int, ville: str | None, jours: int = 30) -> list[dict]:
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    q = db.query(RelevePrix).filter(
        RelevePrix.produit_id == produit_id,
        RelevePrix.observe_le >= depuis,
        RelevePrix.rupture.is_(False),
    )
    if ville:
        q = q.filter(func.lower(RelevePrix.ville) == ville.lower())
    rows = q.order_by(RelevePrix.observe_le).all()
    return [
        {"prix": float(r.prix), "methode": r.methode, "ville": r.ville,
         "observe_le": r.observe_le.isoformat(), "promo": r.promo,
         "marque": r.marque, "collecteur": r.collecteur}
        for r in rows
    ]


def variation(db: Session, produit_id: int, ville: str | None = None) -> dict | None:
    """Compare médiane 7 derniers jours vs 7 précédents."""
    now = dt.datetime.now(dt.timezone.utc)
    q = db.query(RelevePrix).filter(
        RelevePrix.produit_id == produit_id,
        RelevePrix.rupture.is_(False),
        RelevePrix.observe_le >= now - dt.timedelta(days=14),
    )
    if ville:
        q = q.filter(func.lower(RelevePrix.ville) == ville.lower())
    rows = q.all()
    cur = [(float(r.prix), r.methode) for r in rows if r.observe_le >= now - dt.timedelta(days=7)]
    prev = [(float(r.prix), r.methode) for r in rows if r.observe_le < now - dt.timedelta(days=7)]
    m_cur, m_prev = mediane_ponderee(cur), mediane_ponderee(prev)
    if m_cur is None or m_prev in (None, 0):
        return None
    pct = round((m_cur - m_prev) / m_prev * 100, 2)
    return {"mediane_actuelle": m_cur, "mediane_precedente": m_prev,
            "variation_pct": pct, "n_actuel": len(cur), "n_precedent": len(prev)}


def taux_rupture(db: Session, produit_id: int | None = None, jours: int = 7) -> float | None:
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    q = db.query(RelevePrix).filter(RelevePrix.observe_le >= depuis)
    if produit_id:
        q = q.filter(RelevePrix.produit_id == produit_id)
    total = q.count()
    if not total:
        return None
    rupt = q.filter(RelevePrix.rupture.is_(True)).count()
    return round(rupt / total * 100, 1)


def generer_alertes(db: Session, seuil_variation: float = 10.0) -> list[Alerte]:
    """À lancer en tâche planifiée (cron quotidien). Crée alertes non résolues."""
    creees: list[Alerte] = []
    for p in db.query(Produit).filter(Produit.traceur.is_(True)).all():
        v = variation(db, p.id)
        if v and abs(v["variation_pct"]) >= seuil_variation:
            gravite = "rouge" if abs(v["variation_pct"]) >= 15 else "jaune"
            existe = db.query(Alerte).filter(
                Alerte.type == "variation_prix", Alerte.produit_id == p.id,
                Alerte.resolu.is_(False)).first()
            if not existe:
                a = Alerte(type="variation_prix", gravite=gravite,
                           titre=f"{p.nom} : {v['variation_pct']:+.1f}% en 7 j ({v['mediane_actuelle']:,.0f} XAF)",
                           detail=v, produit_id=p.id)
                db.add(a)
                creees.append(a)
        r = taux_rupture(db, p.id)
        if r is not None and r >= 20:
            existe = db.query(Alerte).filter(
                Alerte.type == "rupture", Alerte.produit_id == p.id,
                Alerte.resolu.is_(False)).first()
            if not existe:
                a = Alerte(type="rupture", gravite="rouge",
                           titre=f"{p.nom} : rupture {r}% des relevés (7 j)",
                           detail={"taux_rupture": r}, produit_id=p.id)
                db.add(a)
                creees.append(a)
    db.commit()
    return creees
