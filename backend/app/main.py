"""API Veille Vente — Cameroun & CEMAC (FastAPI)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import ingest, kpi, referentiels, releves

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="API d'ingestion + KPIs pour la veille commerciale Cameroun & CEMAC.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(referentiels.router)
app.include_router(releves.router)
app.include_router(kpi.router)
app.include_router(ingest.router)


@app.get("/", tags=["santé"])
def root():
    return {"app": settings.APP_NAME, "version": "0.1.0", "docs": "/docs"}


@app.get("/healthz", tags=["santé"])
def healthz():
    return {"ok": True}
