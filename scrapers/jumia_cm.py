"""Scraper Jumia Cameroun — recherche produit -> offres -> (optionnel) API.

Usage:
    python jumia_cm.py --query "riz 50kg" --max-pages 2 --out ../data/jumia_riz.json
    python jumia_cm.py --query "congelateur" --push --api-url http://localhost:8000 --api-key XXX

Structure cible (vérifiée par tests sur fixture) : article.prd > a.core[href]
+ h3.name + div.prc (prix) + div.old (ancien prix). Si Jumia change son HTML,
le repli générique (ancres) prend le relais — et les tests l'indiquent.
"""
from __future__ import annotations

import argparse
import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from utils import parse_prix_xaf, push_api, save_json, session_polie

log = logging.getLogger("jumia_cm")
BASE = "https://www.jumia.cm"


def parse_jumia_html(html: str) -> list[dict]:
    """Pur (testable) : HTML -> offres. Ne fait aucun réseau."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[dict] = []
    vues: set[str] = set()

    def push(url: str, titre: str, prix_txt: str, ancien_txt: str = ""):
        url = url if url.startswith("http") else BASE + url
        if url in vues:
            return
        vues.add(url)
        titre = " ".join(titre.split())[:200]
        if len(titre) > 3:
            offres.append({"source": "Jumia Cameroun", "url": url,
                          "titre": titre,
                          "prix": parse_prix_xaf(prix_txt or ""),
                          "ancien_prix": parse_prix_xaf(ancien_txt or ""),
                          "ville": "Douala", "produit": None})

    cartes = soup.select("article.prd")
    for c in cartes:
        a = c.select_one("a.core") or c.select_one("a[href]")
        if not a or not a.get("href"):
            continue
        nom = c.select_one("h3.name")
        titre = nom.get_text(" ", strip=True) if nom else (a.get("title") or "")
        if not titre:
            img = a.select_one("img")
            titre = (img.get("alt", "") if img else "") or a.get_text(" ", strip=True)
        prc = c.select_one("div.prc, .prc")
        old = c.select_one("div.old, .old")
        push(a["href"], titre or a.get_text(" ", strip=True),
             prc.get_text(" ", strip=True) if prc else "",
             old.get_text(" ", strip=True) if old else "")

    if not offres:  # repli générique si structure inconnue
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/catalog/" in href or href.endswith(".html"):
                push(href, a.get("title") or a.get_text(" ", strip=True),
                     a.get_text(" ", strip=True))
    return offres


def scrape_recherche(query: str, max_pages: int = 2) -> list[dict]:
    s = session_polie()
    offres: list[dict] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/catalog/?q={quote_plus(query)}&page={page}"
        log.info("GET %s", url)
        r = s.get(url)
        if r.status_code != 200:
            log.warning("HTTP %s sur %s — arrêt", r.status_code, url)
            break
        trouves = parse_jumia_html(r.text)
        log.info("page %d : %d offres", page, len(trouves))
        offres.extend(trouves)
        if not trouves:
            break
    # dédup inter-pages
    vus, out = set(), []
    for o in offres:
        if o["url"] not in vus:
            vus.add(o["url"])
            out.append(o)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--max-pages", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--api-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="")
    args = ap.parse_args()

    offres = scrape_recherche(args.query, args.max_pages)
    print(f"{len(offres)} offres trouvées pour {args.query!r}")
    for o in offres[:10]:
        print(f"  - {o['prix']} XAF | {o['titre'][:80]}")
    if args.out:
        save_json(args.out, offres)
        print(f"écrit : {args.out}")
    if args.push:
        assert args.api_key, "--api-key requis pour --push"
        print(push_api(args.api_url, args.api_key, offres))


if __name__ == "__main__":
    main()
