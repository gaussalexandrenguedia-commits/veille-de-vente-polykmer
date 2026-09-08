"""Application web Veille Vente — Cameroun & CEMAC.

Un seul serveur : pages HTML + API JSON + fichiers statiques.
Mode démo : SQLite auto-créée et alimentée au premier démarrage.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import ai, collecte, dashboard, deals, ingest, kpi, pages, referentiels, releves, sniper, social

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.DATABASE_URL.startswith("sqlite"):
        from .database import Base, engine
        from .seed import seed_if_empty
        Base.metadata.create_all(bind=engine)
        seed_if_empty()
    yield


app = FastAPI(title=settings.APP_NAME, version="0.3.0",
              description="Cockpit web : prix, alertes, sniper temps réel, écoute sociale.",
              lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.include_router(pages.router)
app.include_router(ai.router)
app.include_router(deals.router)
app.include_router(collecte.router)
app.include_router(referentiels.router)
app.include_router(releves.router)
app.include_router(kpi.router)
app.include_router(dashboard.router)
app.include_router(social.router)
app.include_router(sniper.router)
app.include_router(ingest.router)


@app.get("/healthz", tags=["santé"])
def healthz():
    return {"ok": True, "app": settings.APP_NAME}
