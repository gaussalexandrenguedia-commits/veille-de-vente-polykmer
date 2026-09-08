"""Stockage mutualisé des offres collectées + création auto de deals.

Utilisé par : POST /ingest/scraper (scrapers planifiés) et
POST /collecte/lancer (collecte à la demande depuis l'app).
Un deal est créé quand une offre matchée est ≥ 10 % sous le marché.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import OffreDigitale, RelevePrix, Source
from .deals import creer_deal, match_produit
from .normalize import hash_vendeur, resolve_produit

SEUIL_DEAL_PCT = -10.0


def stocker_offres(db: Session, offres: list[dict]) -> dict:
    inserted, releves, deals = 0, 0, []
    for o in offres:
        src = db.query(Source).filter(
            func.lower(Source.nom) == str(o.get("source", "")).lower()).first()
        if not src:
            src = Source(nom=o.get("source", "inconnu"), type="ecommerce")
            db.add(src)
            db.commit()
            db.refresh(src)
        if o.get("url") and db.query(OffreDigitale).filter(
                OffreDigitale.url == o["url"]).first():
            continue
        prix, ancien = o.get("prix"), o.get("ancien_prix")
        remise = round((ancien - prix) / ancien * 100, 1) \
            if (prix and ancien and ancien > prix) else None
        db.add(OffreDigitale(
            source_id=src.id, url=o.get("url", ""), titre=o.get("titre", "")[:500],
            prix=prix, ancien_prix=ancien, remise_pct=remise,
            vendeur_hash=hash_vendeur(o.get("vendeur"), o.get("source", "")),
            ville=o.get("ville")))
        inserted += 1
        p = None
        if prix:
            # SKU explicite (Kobo/manuel) ou matching par mots-clés (scrapers)
            if o.get("produit"):
                p = resolve_produit(db, o["produit"])
            if p is None:
                p = match_produit(db, o.get("titre", ""))
            if p:
                db.add(RelevePrix(
                    produit_id=p.id, source_id=src.id, prix=prix,
                    ville=o.get("ville") or "Douala", methode="scrape",
                    vendeur_hash=hash_vendeur(o.get("vendeur"), o.get("source", "")),
                    preuve_url=o.get("url"), promo=bool(remise),
                    observe_le=dt.datetime.now(dt.timezone.utc),
                    collecteur=f"collecte:{src.nom}"))
                releves += 1
                try:
                    d = creer_deal(
                        db, titre=o.get("titre", p.nom)[:300], prix=prix,
                        ville=o.get("ville") or "Douala", produit_id=p.id,
                        source_id=src.id, preuve_url=o.get("url"),
                        meta={"origine": "collecte_auto"})
                    if d.ecart_pct is not None and d.ecart_pct <= SEUIL_DEAL_PCT:
                        deals.append(d.titre)
                    elif d.ecart_pct is None or d.ecart_pct > SEUIL_DEAL_PCT:
                        # pas un deal : on supprime (le relevé reste)
                        db.delete(d)
                except Exception:
                    db.rollback()
    db.commit()
    return {"offres_inserees": inserted, "releves_prix_crees": releves,
            "deals_crees": deals}
