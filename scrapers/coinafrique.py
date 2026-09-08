"""Scraper CoinAfrique — annonces par recherche + ville.

Usage:
    python coinafrique.py --query "congelateur" --ville douala --out ../data/coinafrique.json

Villes : douala, yaounde, bafoussam, garoua, brazzaville, libreville, ndjamena…
Parsing en 2 temps : blocs `.ad*` si présents, sinon ancres `/annonce/`
avec prix cherché dans le parent proche.
"""
from __future__ import annotations

import argparse
import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from utils import parse_prix_xaf, push_api, save_json, session_polie

log = logging.getLogger("coinafrique")
BASE = "https://www.coinafrique.com"


def parse_coin_html(html: str, ville: str = "Douala") -> list[dict]:
    """Pur (testable) : HTML -> annonces. Ne fait aucun réseau."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[dict] = []
    vues: set[str] = set()

    def push(url: str, titre: str, prix_txt: str):
        url = url if url.startswith("http") else BASE + url
        if url in vues:
            return
        vues.add(url)
        titre = " ".join(titre.split())[:200]
        if len(titre) > 3:
            offres.append({"source": "CoinAfrique", "url": url,
                          "titre": titre, "prix": parse_prix_xaf(prix_txt or ""),
                          "ville": ville.capitalize(), "produit": None})

    for c in soup.select("div.ad, li.ad, div[class*='annonce'], div.listing"):
        a = c.select_one("a[href]")
        if not a or not a.get("href"):
            continue
        prix_el = c.select_one("[class*='prix'], [class*='price']")
        push(a["href"], a.get("title") or a.get_text(" ", strip=True),
             prix_el.get_text(" ", strip=True) if prix_el
             else c.get_text(" ", strip=True))

    if not offres:  # repli : ancres /annonce/ + prix du parent
        for a in soup.select("a[href*='/annonce/']"):
            parent = a.find_parent(["li", "div"])
            push(a["href"], a.get("title") or a.get_text(" ", strip=True),
                 parent.get_text(" ", strip=True) if parent else "")
    return offres


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
        trouves = parse_coin_html(r.text, ville)
        log.info("page %d : %d annonces", page, len(trouves))
        offres.extend(trouves)
        if not trouves:
            break
    vus, out = set(), []
    for o in offres:
        if o["url"] not in vus:
            vus.add(o["url"])
            out.append(o)
    return out


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
