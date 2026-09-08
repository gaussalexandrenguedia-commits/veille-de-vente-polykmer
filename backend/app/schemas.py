"""Schémas Pydantic (validation à l'ingestion)."""
import datetime as dt

from pydantic import BaseModel, Field


class ReleveIn(BaseModel):
    # Accept SKU *ou* nom libre (résolu côté API via alias + flou)
    produit: str = Field(..., examples=["RIZ-PARF-50KG"])
    source: str = Field(..., examples=["Relevés terrain Kobo"])
    prix: float = Field(..., gt=0, examples=[28500])
    prix_gros: float | None = None
    ville: str = Field(..., examples=["Yaoundé"])
    pays: str = Field(default="CM", max_length=2)
    marche: str | None = Field(default=None, examples=["Marché Mokolo"])
    vendeur: str | None = None  # sera haché, jamais stocké en clair
    marque: str | None = None
    origine: str | None = None
    rupture: bool = False
    promo: bool = False
    promo_detail: str | None = None
    paiement_momo: bool = False
    methode: str = Field(default="manuel", pattern="^(scrape|terrain|manuel|api)$")
    preuve_url: str | None = None
    observe_le: dt.datetime | None = None
    collecteur: str | None = None


class ReleveOut(ReleveIn):
    id: int
    produit_id: int
    produit_nom: str


class OffreScraperIn(BaseModel):
    source: str
    url: str
    titre: str
    prix: float | None = None
    ancien_prix: float | None = None
    vendeur: str | None = None
    ville: str | None = None
    produit: str | None = None  # SKU si le scraper a pu matcher


class AlerteOut(BaseModel):
    id: int
    type: str
    gravite: str
    titre: str
    detail: dict = {}
    produit_id: int | None = None
    resolu: bool = False
