"""Agent IA : parser, vision/OCR, scoreur, messages, rapport.

Chaque route fonctionne SANS clé (heuristique offline) et passe en mode
Gemini quand GEMINI_API_KEYS est configuré. Le champ `source` dit lequel.
"""
from __future__ import annotations

import datetime as dt
import statistics

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Produit, RelevePrix
from ..services.ai_client import GeminiClient, GeminiError
from ..services.ai_parse import (PROMPT_PARSE, SYSTEM_PARSE, normalize_ai_result,
                                 parse_heuristic)
from ..services.ai_scoring import (PROMPT_FRAUDE, flags_fraude,
                                   score_opportunite, verdict_ecart)
from ..services.ai_write import (PROMPT_MESSAGE, PROMPT_RAPPORT,
                                 message_template, rapport_template, wa_link)
from ..services.normalize import resolve_produit

router = APIRouter(prefix="/api/v1/ai", tags=["agent IA"])


# ── statut & test ─────────────────────────────────────────────
@router.get("/statut")
def statut():
    return GeminiClient().info()


@router.post("/test")
async def test():
    client = GeminiClient()
    if not client.available:
        return {"ok": False, "erreur": "aucune clé (mode heuristique)",
                "latence_ms": 0}
    try:
        res = await client.ping()
        return {"ok": True, **res}
    except GeminiError as e:
        return {"ok": False, "erreur": str(e)[:200], "latence_ms": 0}


# ── 1. Parser d'annonces ───────────────────────────────────────
class TexteIn(BaseModel):
    texte: str


@router.post("/parser-annonce")
async def parser_annonce(body: TexteIn):
    if len(body.texte.strip()) < 3:
        raise HTTPException(422, "Texte trop court")
    client = GeminiClient()
    if client.available:
        try:
            data = await client.generate_json(PROMPT_PARSE + body.texte,
                                              SYSTEM_PARSE, max_tokens=400)
            return normalize_ai_result(data, body.texte)
        except GeminiError:
            pass  # repli heuristique ci-dessous
    return parse_heuristic(body.texte)


# ── 2. Vision / OCR ───────────────────────────────────────────
@router.post("/analyser-image")
async def analyser_image(file: UploadFile = File(...), titre: str = Form("")):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(422, "Image JPEG/PNG/WebP requise")
    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image > 5 Mo")
    client = GeminiClient()
    if not client.available:
        raise HTTPException(503, "Vision IA indisponible : aucune clé configurée")
    prompt = ("Extrais de cette annonce commerciale (flyer WhatsApp, affiche, "
              "photo produit) un JSON : {produit, prix (nombre XAF ou null), "
              "phone (9 chiffres ou null), caracteristiques [str], "
              "texte_visible (court)}." + (f" Titre fourni : {titre}. Ajoute "
              "'correspond': true/false (l'image illustre-t-elle ce titre ?)." if titre else ""))
    try:
        out = await client.analyze_image(data, file.content_type, prompt)
    except GeminiError as e:
        raise HTTPException(502, f"Gemini : {e}"[:200])
    out["source"] = "gemini-vision"
    return out


# ── 3. Scoreur d'opportunités ──────────────────────────────────
class ScorerIn(BaseModel):
    produit: str
    prix: float
    ville: str | None = None
    texte: str = ""


def _mediane(db: Session, produit_id: int, ville: str | None, jours: int = 14) -> float | None:
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    q = db.query(RelevePrix.prix).filter(
        RelevePrix.produit_id == produit_id,
        RelevePrix.observe_le >= depuis, RelevePrix.rupture.is_(False))
    if ville:
        from sqlalchemy import func
        q = q.filter(func.lower(RelevePrix.ville) == ville.lower())
    vals = [float(p[0]) for p in q.all()]
    return float(statistics.median(vals)) if vals else None


@router.post("/scorer")
async def scorer(body: ScorerIn, db: Session = Depends(get_db)):
    p = resolve_produit(db, body.produit)
    if not p:
        raise HTTPException(404, f"Produit introuvable : {body.produit!r} (médiane marché requise)")
    med = _mediane(db, p.id, body.ville)
    if not med:
        raise HTTPException(404, "Pas assez d'historique marché pour ce produit")
    ecart = round((body.prix - med) / med * 100, 1)
    verdict, _ = verdict_ecart(ecart)
    raisons: list[str] = []
    suspect = False
    ia_ok = False
    client = GeminiClient()
    if client.available and body.texte:
        try:
            g = await client.generate_json(PROMPT_FRAUDE.format(
                texte=body.texte[:600], prix=f"{body.prix:,.0f}",
                mediane=f"{med:,.0f}", ecart=ecart, ville=body.ville or "Cameroun"),
                max_tokens=300)
            suspect = bool(g.get("suspect"))
            raisons = [str(r) for r in (g.get("raisons") or [])][:3]
            ia_ok = True
        except GeminiError:
            pass
    flags = flags_fraude(body.prix, med, body.texte)
    if flags:
        suspect = True
        raisons += [f"Heuristique : {f}" for f in flags]
    if not raisons:
        raisons = [f"Écart marché {ecart:+.1f}%."]
    return {"produit": p.nom, "sku": p.sku, "prix": body.prix,
            "mediane_marche": round(med), "ecart_pct": ecart,
            "score": score_opportunite(ecart),
            "verdict": "prioritaire" if (verdict == "prioritaire" and not suspect)
            else ("suspect" if suspect and ecart < -20 else verdict),
            "fraude_suspectee": suspect, "raisons": raisons,
            "source": "gemini+marche" if ia_ok else "marche"}


# ── 4. Message vendeur ─────────────────────────────────────────
class MessageIn(BaseModel):
    produit: str
    prix: float
    ville: str = "Douala"
    phone: str | None = None
    prix_propose: float | None = None


@router.post("/message-vendeur")
async def message_vendeur(body: MessageIn):
    propose = (f" Tu peux proposer {body.prix_propose:,.0f} XAF cash."
               .replace(",", " ")) if body.prix_propose else ""
    client = GeminiClient()
    if client.available:
        try:
            msg = await client.generate_text(PROMPT_MESSAGE.format(
                produit=body.produit, prix=f"{body.prix:,.0f}".replace(",", " "),
                ville=body.ville, propose=propose), max_tokens=200)
            return {"message": msg.strip(), "wa_link": wa_link(body.phone, msg.strip()),
                    "source": "gemini"}
        except GeminiError:
            pass
    msg = message_template(body.produit, body.prix, body.ville, body.prix_propose)
    return {"message": msg, "wa_link": wa_link(body.phone, msg), "source": "template"}


# ── 5. Rapport quotidien ───────────────────────────────────────
@router.get("/rapport-jour")
async def rapport_jour(db: Session = Depends(get_db)):
    from ..services.kpi import taux_rupture, variation
    kpis: dict = {"date": dt.date.today().isoformat()}
    var = []
    for p in db.query(Produit).all():
        v = variation(db, p.id)
        if v and abs(v["variation_pct"]) >= 5:
            var.append({"produit": p.nom, **v})
    kpis["variations"] = sorted(var, key=lambda x: abs(x["variation_pct"]), reverse=True)[:5]
    kpis["ruptures"] = [{"produit": p.nom, "taux": t}
                        for p in db.query(Produit).filter(Produit.traceur.is_(True)).all()
                        if (t := taux_rupture(db, p.id)) is not None and t >= 5][:5]
    from .social import resume as resume_social
    soc = resume_social(jours=7, db=db)
    kpis["sentiment"] = soc["score_moyen"]
    kpis["motifs"] = soc["motifs"][:5]
    client = GeminiClient()
    if client.available:
        try:
            texte = await client.generate_text(PROMPT_RAPPORT.format(
                variations=kpis["variations"] or "aucune > 5%",
                ruptures=kpis["ruptures"] or "aucune",
                sentiment=soc["score_moyen"], motifs=soc["motifs"][:5] or "volume faible",
                promos="(voir dashboard)"), max_tokens=700)
            return {"rapport": texte.strip(), "source": "gemini",
                    "genere_le": dt.datetime.now(dt.timezone.utc).isoformat()}
        except GeminiError:
            pass
    return {"rapport": rapport_template(kpis), "source": "template",
            "genere_le": dt.datetime.now(dt.timezone.utc).isoformat()}
