"""Collecte planifiée : toutes les cibles -> API veille (+ deals auto).

Usage ponctuel :
    API_URL=http://localhost:8000 API_KEY=xxx python run_all.py

Cron recommandé (quotidien 6h + 18h WAT) :
    0 6,18 * * * cd /opt/veille/scrapers && API_URL=http://localhost:8000 API_KEY=xxx /usr/bin/python3 run_all.py >> /var/log/veille-collecte.log 2>&1

La détection de deals (≥ 10 % sous le marché) se fait côté API.
"""
from __future__ import annotations

import logging
import os

from coinafrique import scrape as scrape_coin
from jumia_cm import scrape_recherche as scrape_jumia
from utils import push_api

log = logging.getLogger("run_all")

CIBLES = [
    # (site, query, ville, pages)
    ("jumia", "congelateur", "douala", 2),
    ("jumia", "televiseur 32", "douala", 2),
    ("jumia", "tecno", "douala", 2),
    ("jumia", "riz 50kg", "douala", 1),
    ("coinafrique", "congelateur", "douala", 2),
    ("coinafrique", "congelateur", "yaounde", 2),
    ("coinafrique", "ciment", "douala", 1),
    ("coinafrique", "groupe electrogene", "douala", 2),
    ("coinafrique", "iphone", "douala", 1),
]

# Essaie de lier chaque offre à un SKU connu (mots-clés -> produit_sku)
SKU_KEYWORDS = {
    "CONGEL-200L": ["congel", "frigo"],
    "TV-32": ["televiseur", "tv 32", "tv32", "smart tv"],
    "SMART-ENTRY": ["tecno", "itel", "redmi", "spark", "camon"],
    "RIZ-PARF-50KG": ["riz"],
    "CIMENT-50KG": ["ciment"],
}


def guess_sku(titre: str) -> str | None:
    t = titre.lower()
    for sku, kws in SKU_KEYWORDS.items():
        if any(k in t for k in kws):
            return sku
    return None


def main() -> None:
    api_url = os.getenv("API_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "")
    assert api_key, "API_KEY requise"
    total = {"offres": 0, "releves": 0, "deals": []}
    for site, query, ville, pages in CIBLES:
        try:
            offres = scrape_jumia(query, pages) if site == "jumia" \
                else scrape_coin(query, ville, pages)
        except Exception as e:  # noqa: BLE001 — une cible ne bloque pas les autres
            log.error("%s/%s : %s", site, query, e)
            continue
        for o in offres:
            o["produit"] = guess_sku(o.get("titre", ""))
        if not offres:
            continue
        res = push_api(api_url, api_key, offres)
        total["offres"] += res.get("offres_inserees", 0)
        total["releves"] += res.get("releves_prix_crees", 0)
        total["deals"] += res.get("deals_crees", [])
        log.warning("%s/%s : %s", site, query, res)
    print(f"TOTAL: {total['offres']} offres, {total['releves']} relevés, "
          f"{len(total['deals'])} deals")
    for d in total["deals"]:
        print("  🎯", d)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
