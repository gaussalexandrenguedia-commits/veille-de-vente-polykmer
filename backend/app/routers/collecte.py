"""Collecte réelle à la demande : lance un scraper en tâche de fond.

POST /collecte/lancer {site: jumia|coinafrique, query, ville?, max_pages?}
  + header X-API-Key -> {job_id} ; GET /collecte/jobs/{id} -> statut.
Les offres sont stockées (offres + relevés) et les deals auto-créés.
"""
from __future__ import annotations

import asyncio
import sys
import time
import uuid

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..config import ROOT_DIR, settings

router = APIRouter(prefix="/api/v1/collecte", tags=["collecte"])
JOBS: dict[str, dict] = {}
SITES = ("jumia", "coinafrique")


class CollecteIn(BaseModel):
    site: str = "jumia"
    query: str = "congelateur"
    ville: str = "douala"
    max_pages: int = 1


def _check(x_api_key: str | None):
    if x_api_key != settings.API_KEY_INGEST:
        raise HTTPException(403, "Clé API invalide (header X-API-Key)")


def _scrape_sync(site: str, query: str, ville: str, max_pages: int) -> list[dict]:
    sys.path.insert(0, str(ROOT_DIR / "scrapers"))
    max_pages = max(1, min(max_pages, 3))
    if site == "jumia":
        from jumia_cm import scrape_recherche
        return scrape_recherche(query, max_pages)
    from coinafrique import scrape
    return scrape(query, ville, max_pages)


async def _run_job(job_id: str, body: CollecteIn):
    from ..database import SessionLocal
    from ..services.collecte import stocker_offres
    JOBS[job_id].update(status="cours", debut=time.time())
    try:
        offres = await asyncio.to_thread(_scrape_sync, body.site, body.query,
                                         body.ville, body.max_pages)
        db = SessionLocal()
        try:
            res = stocker_offres(db, offres)
        finally:
            db.close()
        JOBS[job_id].update(status="termine", resultat=res,
                            fin=time.time(), erreur=None)
    except Exception as e:  # noqa: BLE001
        JOBS[job_id].update(status="erreur", erreur=str(e)[:300], fin=time.time())


@router.post("/lancer", status_code=202)
async def lancer(body: CollecteIn, x_api_key: str | None = Header(default=None)):
    _check(x_api_key)
    if body.site not in SITES:
        raise HTTPException(422, f"site inconnu (attendu : {SITES})")
    job_id = uuid.uuid4().hex[:8]
    JOBS[job_id] = {"job": job_id, "status": "file", "site": body.site,
                    "query": body.query}
    asyncio.create_task(_run_job(job_id, body))
    return {"job": job_id, "status": "file",
            "suivi": f"/api/v1/collecte/jobs/{job_id}"}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job inconnu")
    return JOBS[job_id]
