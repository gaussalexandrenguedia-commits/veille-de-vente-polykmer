"""Modèles ORM — miroir de infra/init.sql (v0.1)."""
import datetime as dt

from sqlalchemy import (ARRAY, JSON, Boolean, Date, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Produit(Base):
    __tablename__ = "produits"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String, unique=True)
    nom: Mapped[str] = mapped_column(String)
    categorie: Mapped[str] = mapped_column(String)
    unite: Mapped[str] = mapped_column(String, default="piece")
    marques_suivies: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    alias: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    traceur: Mapped[bool] = mapped_column(Boolean, default=False)


class Marche(Base):
    __tablename__ = "marches"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String)
    ville: Mapped[str] = mapped_column(String)
    pays: Mapped[str] = mapped_column(String(2), default="CM")
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lon: Mapped[float | None] = mapped_column(nullable=True)
    __table_args__ = (UniqueConstraint("nom", "ville"),)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(String, unique=True)
    type: Mapped[str] = mapped_column(String)
    url_ou_compte: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequence: Mapped[str] = mapped_column(String, default="hebdo")
    statut_legal: Mapped[str] = mapped_column(String, default="a_qualifier")
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class RelevePrix(Base):
    __tablename__ = "releves_prix"
    id: Mapped[int] = mapped_column(primary_key=True)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    marche_id: Mapped[int | None] = mapped_column(ForeignKey("marches.id"), nullable=True)
    prix: Mapped[float] = mapped_column(Numeric(14, 2))
    prix_gros: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    devise: Mapped[str] = mapped_column(String, default="XAF")
    ville: Mapped[str] = mapped_column(String)
    pays: Mapped[str] = mapped_column(String(2), default="CM")
    vendeur_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    marque: Mapped[str | None] = mapped_column(Text, nullable=True)
    origine: Mapped[str | None] = mapped_column(Text, nullable=True)
    rupture: Mapped[bool] = mapped_column(Boolean, default=False)
    promo: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    paiement_momo: Mapped[bool] = mapped_column(Boolean, default=False)
    methode: Mapped[str] = mapped_column(String, default="manuel")
    preuve_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    observe_le: Mapped[dt.datetime] = mapped_column(TIMESTAMP(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    collecteur: Mapped[str | None] = mapped_column(Text, nullable=True)


class Alerte(Base):
    __tablename__ = "alertes"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String)
    gravite: Mapped[str] = mapped_column(String, default="jaune")
    titre: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    produit_id: Mapped[int | None] = mapped_column(ForeignKey("produits.id"), nullable=True)
    marche_id: Mapped[int | None] = mapped_column(ForeignKey("marches.id"), nullable=True)
    resolu: Mapped[bool] = mapped_column(Boolean, default=False)


class OffreDigitale(Base):
    __tablename__ = "offres_digitales"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    url: Mapped[str] = mapped_column(Text, unique=True)
    titre: Mapped[str] = mapped_column(Text)
    prix: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    ancien_prix: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    remise_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    vendeur_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    ville: Mapped[str | None] = mapped_column(Text, nullable=True)
    engagement: Mapped[dict] = mapped_column(JSON, default=dict)


class ReleveLogistique(Base):
    __tablename__ = "releves_logistique"
    id: Mapped[int] = mapped_column(primary_key=True)
    corridor_id: Mapped[int] = mapped_column(ForeignKey("corridors.id"))
    delai_jours: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)
    cout_tonne_xaf: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    indice_tracasserie: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
