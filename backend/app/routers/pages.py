"""Pages HTML de l'application web (Jinja2, coquille + données via API)."""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


def _page(request: Request, active: str, titre: str, template: str):
    return templates.TemplateResponse(request, template,
                                      {"active": active, "titre": titre,
                                       "app_name": settings.APP_NAME})


@router.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request):
    return _page(request, "dashboard", "Tableau de bord", "dashboard.html")


@router.get("/prix", response_class=HTMLResponse)
def page_prix(request: Request):
    return _page(request, "prix", "Prix & produits", "prix.html")


@router.get("/alertes", response_class=HTMLResponse)
def page_alertes(request: Request):
    return _page(request, "alertes", "Alertes", "alertes.html")


@router.get("/sniper", response_class=HTMLResponse)
def page_sniper(request: Request):
    return _page(request, "sniper", "Sniper temps réel", "sniper.html")


@router.get("/social", response_class=HTMLResponse)
def page_social(request: Request):
    return _page(request, "social", "Écoute sociale", "social.html")


@router.get("/releves", response_class=HTMLResponse)
def page_releves(request: Request):
    return _page(request, "releves", "Relevés terrain", "releves.html")


@router.get("/ia", response_class=HTMLResponse)
def page_ia(request: Request):
    return _page(request, "ia", "Agent IA 🤖", "ia.html")


@router.get("/deals", response_class=HTMLResponse)
def page_deals(request: Request):
    return _page(request, "deals", "Deals détectés 🎯", "deals.html")


@router.get("/referentiels", response_class=HTMLResponse)
def page_referentiels(request: Request):
    return _page(request, "referentiels", "Référentiels", "referentiels.html")
