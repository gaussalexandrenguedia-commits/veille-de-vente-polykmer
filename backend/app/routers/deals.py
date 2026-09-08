"""Deals / opportunités : liste, création (manuelle ou depuis texte), statuts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Opportunite, Produit, Source
from ..services.deals import STATUTS, changer_statut, creer_deal, creer_deal_depuis_texte
from ..services.normalize import resolve_produit

router = APIRouter(prefix="/api/v1/deals", tags=["deals"])


class DealIn(BaseModel):
    titre: str | None = None
    produit: str | None = None   # SKU ou nom (matching flou)
    source: str | None = None
    prix: float | None = None
    ville: str = ""
    preuve_url: str | None = None
    phone: str | None = None
    notes: str = ""


class TexteIn(BaseModel):
    texte: str
    url: str | None = None
    source: str = "Panel Facebook"


class StatutIn(BaseModel):
    statut: str
    notes: str | None = None


def _out(d: Opportunite, produit_nom: str | None, src_nom: str | None) -> dict:
    return {"id": d.id, "titre": d.titre, "produit": produit_nom,
            "produit_id": d.produit_id, "source": src_nom,
            "prix": float(d.prix) if d.prix is not None else None,
            "mediane_ref": float(d.mediane_ref) if d.mediane_ref is not None else None,
            "ecart_pct": float(d.ecart_pct) if d.ecart_pct is not None else None,
            "score": d.score, "verdict": d.verdict, "ville": d.ville,
            "preuve_url": d.preuve_url, "phone": d.phone, "statut": d.statut,
            "notes": d.notes, "cree_le": d.cree_le.isoformat()}


@router.get("")
def list_deals(statut: str | None = None, verdict: str | None = None,
               limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Opportunite, Produit.nom, Source.nom).outerjoin(
        Produit, Opportunite.produit_id == Produit.id).outerjoin(
        Source, Opportunite.source_id == Source.id)
    if statut:
        q = q.filter(Opportunite.statut == statut)
    if verdict:
        q = q.filter(Opportunite.verdict == verdict)
    rows = q.order_by(Opportunite.score.desc(), Opportunite.id.desc()).limit(min(limit, 300)).all()
    items = [_out(d, pn, sn) for d, pn, sn in rows]
    par_statut: dict[str, int] = {}
    for s in STATUTS:
        par_statut[s] = db.query(Opportunite).filter(Opportunite.statut == s).count()
    economie = sum((i["mediane_ref"] - i["prix"]) for i in items
                   if i["statut"] in ("nouveau", "contacte")
                   and i["prix"] is not None and i["mediane_ref"] is not None
                   and i["mediane_ref"] > i["prix"])
    return {"items": items, "par_statut": par_statut,
            "economie_potentielle": round(economie)}


@router.post("", status_code=201)
def create_deal(body: DealIn, db: Session = Depends(get_db)):
    pid, sid = None, None
    if body.produit:
        p = resolve_produit(db, body.produit)
        if not p:
            raise HTTPException(404, f"Produit introuvable : {body.produit!r}")
        pid = p.id
    if body.source:
        from sqlalchemy import func
        s = db.query(Source).filter(func.lower(Source.nom) == body.source.lower()).first()
        if not s:
            raise HTTPException(404, f"Source introuvable : {body.source!r}")
        sid = s.id
    d = creer_deal(db, titre=body.titre or f"Deal {body.produit or ''} {body.ville}".strip(),
                   prix=body.prix, ville=body.ville, produit_id=pid,
                   source_id=sid, preuve_url=body.preuve_url,
                   phone=body.phone, notes=body.notes)
    pn = db.query(Produit.nom).filter(Produit.id == d.produit_id).scalar() if d.produit_id else None
    sn = db.query(Source.nom).filter(Source.id == d.source_id).scalar() if d.source_id else None
    return _out(d, pn, sn)


@router.post("/depuis-texte", status_code=201)
def depuis_texte(body: TexteIn, db: Session = Depends(get_db)):
    if len(body.texte.strip()) < 10:
        raise HTTPException(422, "Texte trop court (min 10 caractères)")
    d, parsed = creer_deal_depuis_texte(db, body.texte, body.url, body.source)
    pn = db.query(Produit.nom).filter(Produit.id == d.produit_id).scalar() if d.produit_id else None
    return {"deal": _out(d, pn, body.source), "parse": parsed}


@router.patch("/{deal_id}")
def patch_deal(deal_id: int, body: StatutIn, db: Session = Depends(get_db)):
    try:
        d = changer_statut(db, deal_id, body.statut, body.notes)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))
    pn = db.query(Produit.nom).filter(Produit.id == d.produit_id).scalar() if d.produit_id else None
    sn = db.query(Source.nom).filter(Source.id == d.source_id).scalar() if d.source_id else None
    return _out(d, pn, sn)
