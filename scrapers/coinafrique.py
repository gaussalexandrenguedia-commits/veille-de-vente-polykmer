"""Scraper CoinAfrique — annonces par recherche + ville.

Usage:
    python coinafrique.py --query "congelateur" --ville douala --out ../data/coinafrique.json

Villes : douala, yaounde, bafoussam, garoua, brazzaville, libreville, ndjamena…
"""
from __future__ import annotations

import argparse
import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from utils import parse_prix_xaf, push_api, save_json, session_polie

log = logging.getLogger("coinafrique")
BASE = "https://www.coinafrique.com"


def scrape(query: str, ville: str = "douala", max_pages: int = 3) -> list[dict]:
    s = session_polie()
    offres: list[dict] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/cameroun/{ville}/?q={quote_plus(query)}&page={page}"
        log.info("GET %s", url)
        r = s.get(url)
        if r.status_code != 200:
            log.warning("HTTP %s — arrêt", r.status_code)
            break
        soup = BeautifulSoup(r.text, "lxml")
        cartes = soup.select("div.ad, li.ad, a.ad__link, div[class*='annonce']")
        if not cartes:
            cartes = soup.select("a[href*='/annonce/']")
        vues = set()
        for c in cartes:
            a = c if c.name == "a" else c.select_one("a[href]")
            if not a or not a.get("href"):
                continue
            lien = a["href"]
            lien = lien if lien.startswith("http") else BASE + lien
            if lien in vues:
                continue
            vues.add(lien)
            titre = (a.get("title") or a.get_text(" ", strip=True) or "")[:200]
            prix_el = c.select_one("[class*='prix'], [class*='price']")
            prix = parse_prix_xaf(prix_el.get_text(" ", strip=True) if prix_el else c.get_text(" ", strip=True))
            if titre and len(titre) > 3:
                offres.append({"source": "CoinAfrique", "url": lien,
                              "titre": titre.strip(), "prix": prix,
                              "ville": ville.capitalize(), "produit": None})
        log.info("page %d : %d annonces", page, len(vues))
        if not vues:
            break
    return offres


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--ville", default="douala")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--api-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="")
    args = ap.parse_args()
    offres = scrape(args.query, args.ville, args.max_pages)
    print(f"{len(offres)} annonces pour {args.query!r} à {args.ville}")
    for o in offres[:10]:
        print(f"  - {o['prix']} XAF | {o['titre'][:80]}")
    if args.out:
        save_json(args.out, offres)
        print(f"écrit : {args.out}")
    if args.push:
        assert args.api_key, "--api-key requis"
        print(push_api(args.api_url, args.api_key, offres))


if __name__ == "__main__":
    main()
