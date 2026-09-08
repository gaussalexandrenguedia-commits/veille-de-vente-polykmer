"""Utilitaires partagés des scrapers : session polie, prix XAF, envoi API."""
from __future__ import annotations

import json
import logging
import re
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

HEADERS = {
    "User-Agent": "VeilleVenteCM/0.1 (+contact: veille-vente; usage: recherche prix publics, 1 req/4s)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

PRIX_RE = re.compile(r"(\d[\d\s\u202f.,]*)\s*(FCFA|XAF|F\s?CFA)?", re.I)


def session_polie(delai: float = 4.0) -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    s.delai = delai  # type: ignore[attr-defined]
    s._dernier = 0.0  # type: ignore[attr-defined]
    orig_get = s.get

    def get_poli(*a, **k):
        attente = s.delai - (time.time() - s._dernier)  # type: ignore[attr-defined]
        if attente > 0:
            time.sleep(attente)
        for essai in range(3):
            try:
                r = orig_get(*a, timeout=k.pop("timeout", 25), **k)
                s._dernier = time.time()  # type: ignore[attr-defined]
                if r.status_code == 429:
                    time.sleep(10 * (essai + 1))
                    continue
                return r
            except requests.RequestException:
                if essai == 2:
                    raise
                time.sleep(5 * (essai + 1))
        raise RuntimeError("unreachable")

    s.get = get_poli  # type: ignore[method-assign]
    return s


def parse_prix_xaf(txt: str | None) -> float | None:
    """Extrait un prix XAF : priorité au nombre suivi d'une unité monétaire.

    « TV TCL 32 pouces 95000 FCFA » -> 95000 (pas 32).
    Sans unité explicite : dernier nombre >= 100 (évite tailles/modèles).
    Gère k (=×1000) et M (=×1 000 000).
    """
    if not txt:
        return None
    trouves = list(PRIX_RE.finditer(txt.replace(" ", " ")))
    if not trouves:
        return None

    def valeur(m):
        brut = re.sub(r"[^\d]", "", m.group(1))
        if not brut:
            return None
        v = float(brut)
        unite = (m.group(2) or "").lower()
        if unite == "k":
            v *= 1000
        elif unite == "m":
            v *= 1_000_000
        return v

    avec_unite = [m for m in trouves if (m.group(2) or "").strip()]
    if avec_unite:
        return valeur(avec_unite[-1])
    for m in reversed(trouves):  # repli : dernier nombre plausible
        v = valeur(m)
        if v is not None and v >= 100:
            return v
    return None


def push_api(api_url: str, cle: str, offres: list[dict]) -> dict:
    """Envoie un lot vers POST /api/v1/ingest/scraper."""
    r = requests.post(f"{api_url.rstrip('/')}/api/v1/ingest/scraper",
                      headers={"X-API-Key": cle}, json=offres, timeout=60)
    r.raise_for_status()
    return r.json()


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
