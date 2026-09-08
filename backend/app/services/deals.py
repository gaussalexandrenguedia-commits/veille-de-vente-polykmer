"""Moteur d'opportunités (deals) : scoring marché + statuts + dédup.

Sources réelles : ingestion scrapers (auto), texte d'annonce parsé (FB/
WhatsApp copié-collé), saisie manuelle. Statuts : nouveau -> contacte ->
conclu | abandonne (+ rouverture possible).
"""
from __future__ import annotations

import datetime as dt
import statistics

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import Opportunite, Produit, RelevePrix, Source
from .ai_parse import parse_heuristic
from .ai_scoring import score_opportunite, verdict_ecart
from .normalize import resolve_produit

STATUTS = ("nouveau", "contacte", "conclu", "abandonne")

# Mots-clés -> SKU (repli quand le matching flou échoue sur texte libre)
PRODUIT_KEYWORDS = {
    "congel": "CONGEL-200L", "frigo": "CONGEL-200L", "congél": "CONGEL-200L",
    "riz": "RIZ-PARF-50KG", "huile": "HUILE-VEG-1L", "sucre": "SUCRE-1KG",
    "ciment": "CIMENT-50KG", "téléviseur": "TV-32", "televiseur": "TV-32",
    " tv ": "TV-32", "tecno": "SMART-ENTRY", "itel": "SMART-ENTRY",
    "redmi": "SMART-ENTRY", "smartphone": "SMART-ENTRY",
}


def mediane_marche(db: Session, produit_id: int, ville: str | None = None,
                   jours: int = 14) -> float | None:
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    q = db.query(RelevePrix.prix).filter(
        RelevePrix.produit_id == produit_id, RelevePrix.observe_le >= depuis,
        RelevePrix.rupture.is_(False))
    if ville:
        q = q.filter(func.lower(RelevePrix.ville) == ville.lower())
    vals = [float(p[0]) for p in q.all()]
    return float(statistics.median(vals)) if vals else None


def score_prix(db: Session, produit_id: int, prix: float,
               ville: str | None = None) -> dict:
    med = mediane_marche(db, produit_id, ville)
    if not med:
        return {"mediane": None, "ecart_pct": None, "score": 50,
                "verdict": "sans_ref"}
    ecart = round((prix - med) / med * 100, 1)
    verdict, _ = verdict_ecart(ecart)
    return {"mediane": round(med), "ecart_pct": ecart,
            "score": score_opportunite(ecart), "verdict": verdict}


def match_produit(db: Session, texte: str) -> Produit | None:
    p = resolve_produit(db, texte)
    if p:
        return p
    t = f" {texte.lower()} "
    for kw, sku in PRODUIT_KEYWORDS.items():
        if kw in t:
            return db.query(Produit).filter(Produit.sku == sku).first()
    return None


def creer_deal(db: Session, titre: str, prix: float | None,
               ville: str = "", produit_id: int | None = None,
               source_id: int | None = None, preuve_url: str | None = None,
               phone: str | None = None, notes: str = "",
               statut: str = "nouveau", meta: dict | None = None) -> Opportunite:
    if statut not in STATUTS:
        raise ValueError(f"statut invalide : {statut}")
    if preuve_url:
        ouvert = db.query(Opportunite).filter(
            Opportunite.preuve_url == preuve_url,
            Opportunite.statut.in_(["nouveau", "contacte"])).first()
        if ouvert:  # dédup : l'URL est déjà suivie
            return ouvert
    sc = score_prix(db, produit_id, prix, ville or None) \
        if (produit_id and prix) else {"mediane": None, "ecart_pct": None,
                                       "score": 50, "verdict": "sans_ref"}
    d = Opportunite(titre=titre[:300], produit_id=produit_id,
                    source_id=source_id, prix=prix,
                    mediane_ref=sc["mediane"], ecart_pct=sc["ecart_pct"],
                    score=sc["score"], verdict=sc["verdict"], ville=ville,
                    preuve_url=preuve_url, phone=phone, statut=statut,
                    notes=notes, meta_=meta or {})
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def creer_deal_depuis_texte(db: Session, texte: str,
                            url: str | None = None,
                            source_nom: str = "Panel Facebook") -> tuple[Opportunite, dict]:
    """Collez un post FB/WhatsApp -> deal parsé + scoré. Le vrai flux terrain."""
    parsed = parse_heuristic(texte)
    produit = match_produit(db, f"{parsed['produit'] or ''} {texte}")
    src = db.query(Source).filter(func.lower(Source.nom) == source_nom.lower()).first()
    titre = parsed["produit"] or texte[:80]
    if parsed["prix"]:
        titre += f" — {parsed['prix']:,.0f} XAF".replace(",", " ")
    deal = creer_deal(db, titre=titre, prix=parsed["prix"],
                      ville=parsed["ville"] or "",
                      produit_id=produit.id if produit else None,
                      source_id=src.id if src else None,
                      preuve_url=url, phone=parsed["phone"],
                      meta={"parse": parsed,
                            "produit_matche": produit.sku if produit else None})
    return deal, parsed


def changer_statut(db: Session, deal_id: int, statut: str,
                   notes: str | None = None) -> Opportunite:
    if statut not in STATUTS:
        raise ValueError(f"statut invalide : {statut} (attendu : {STATUTS})")
    d = db.query(Opportunite).filter(Opportunite.id == deal_id).first()
    if not d:
        raise LookupError(f"deal {deal_id} introuvable")
    d.statut = statut
    if notes is not None:
        d.notes = notes
    d.maj_le = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(d)
    return d
