"""Normalisation produits + hachage vendeurs + déduplication."""
from __future__ import annotations

import hashlib
import unicodedata

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from ..models import Produit


def clean(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().strip().split())


def hash_vendeur(vendeur: str | None, source: str) -> str | None:
    if not vendeur:
        return None
    return hashlib.sha256(f"{source}::{clean(vendeur)}".encode()).hexdigest()[:32]


def resolve_produit(db: Session, raw: str) -> Produit | None:
    """1) match SKU exact, 2) match nom/alias exact, 3) flou >= 85."""
    q = clean(raw)
    prod = db.query(Produit).filter(Produit.sku == raw.strip().upper()).first()
    if prod:
        return prod
    produits = db.query(Produit).all()
    index: dict[str, Produit] = {}
    for p in produits:
        index[clean(p.nom)] = p
        index[clean(p.sku)] = p
        for a in p.alias or []:
            index[clean(a)] = p
    if q in index:
        return index[q]
    best = process.extractOne(q, list(index.keys()), scorer=fuzz.token_sort_ratio)
    if best and best[1] >= 85:
        return index[best[0]]
    return None


def dedup_key(produit_id: int, vendeur_hash: str | None, prix: float, jour: str, source_id: int) -> str:
    base = f"{produit_id}|{vendeur_hash}|{prix}|{jour}|{source_id}"
    return hashlib.sha256(base.encode()).hexdigest()[:32]
