"""Écoute sociale (social listening) : sentiment, motifs, timeline.

Mini-Meltwater/Talkwalker local : commentaires FB/Telegram/TikTok scorés
en FR/pidgin/EN (services/sentiment.py), agrégés par motif et dans le temps.
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Commentaire, Source
from ..services.kpi import _aware
from ..services.sentiment import score_sentiment

router = APIRouter(prefix="/api/v1/social", tags=["écoute sociale"])

MOTIFS_LABELS = {"prix": "Prix", "qualite": "Qualité", "livraison": "Livraison",
                 "sav": "SAV / garantie", "arnaque": "Arnaque présumée",
                 "rupture": "Rupture / stock"}


class CommentaireIn(BaseModel):
    source: str = "Panel Facebook"
    texte: str
    langue: str = "fr"


@router.get("/resume")
def resume(jours: int = 14, db: Session = Depends(get_db)):
    depuis = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=jours)
    rows = (db.query(Commentaire, Source.nom)
            .join(Source, Commentaire.source_id == Source.id)
            .filter(Commentaire.capture_le >= depuis)
            .order_by(Commentaire.capture_le.desc()).all())
    scores = [c.sentiment_score for c, _ in rows]
    motifs: dict[str, int] = defaultdict(int)
    for c, _ in rows:
        if c.motif:
            motifs[c.motif] += 1
    timeline: dict[str, list[int]] = defaultdict(list)
    for c, _ in rows:
        jour = (_aware(c.capture_le) or dt.datetime.now(dt.timezone.utc)).date().isoformat()
        timeline[jour].append(c.sentiment_score)
    return {
        "volume": len(rows),
        "score_moyen": round(sum(scores) / len(scores)) if scores else 0,
        "positifs": sum(1 for s in scores if s > 20),
        "neutres": sum(1 for s in scores if -20 <= s <= 20),
        "negatifs": sum(1 for s in scores if s < -20),
        "motifs": [{"motif": k, "label": MOTIFS_LABELS.get(k, k), "n": v}
                   for k, v in sorted(motifs.items(), key=lambda x: -x[1])],
        "timeline": [{"date": j, "score": round(sum(v) / len(v)), "n": len(v)}
                     for j, v in sorted(timeline.items())],
        "derniers": [{"texte": c.texte[:280], "source": nom,
                      "score": c.sentiment_score, "motif": c.motif,
                      "langue": c.langue,
                      "date": (_aware(c.capture_le) or dt.datetime.now(dt.timezone.utc)).isoformat()}
                     for c, nom in rows[:30]],
    }


@router.post("/commentaires", status_code=201)
def add_commentaire(body: CommentaireIn, db: Session = Depends(get_db)):
    src = db.query(Source).filter(func.lower(Source.nom) == body.source.lower()).first()
    if not src:
        raise HTTPException(404, f"Source introuvable : {body.source!r}")
    score, motif = score_sentiment(body.texte)
    c = Commentaire(source_id=src.id, texte=body.texte, langue=body.langue,
                    sentiment_score=score, motif=motif,
                    capture_le=dt.datetime.now(dt.timezone.utc))
    db.add(c)
    db.commit()
    return {"id": c.id, "score": score, "motif": motif}
