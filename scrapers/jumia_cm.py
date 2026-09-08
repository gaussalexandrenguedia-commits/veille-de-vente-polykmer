"""Scraper Jumia Cameroun — recherche produit -> offres -> (optionnel) API.

Usage:
    python jumia_cm.py --query "riz 50kg" --max-pages 2 --out ../data/jumia_riz.json
    python jumia_cm.py --query "congelateur" --push --api-url http://localhost:8000 --api-key XXX

Note : sélecteurs indicatifs — Jumia change son HTML ; ajuster si vide
et toujours respecter robots.txt + débit ≤ 1 req / 4 s.
"""
from __future__ import annotations

import argparse
import logging
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from utils import parse_prix_xaf, push_api, save_json, session_polie

log = logging.getLogger("jumia_cm")
BASE = "https://www.jumia.cm"


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
        soup = BeautifulSoup(r.text, "lxml")
        cartes = soup.select("article.prd, div.info, a.core")
        if not cartes:  # fallback générique
            cartes = soup.select("a[href*='/catalog/'], a[href*='.html']")
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
            bloc = str(c)
            titre = (a.get("title") or a.get_text(" ", strip=True) or "")[:200]
            prix_txt = ""
            for sel in [".prc", ".price", "[data-price]"]:
                el = c.select_one(sel)
                if el:
                    prix_txt = el.get("data-price") or el.get_text(" ", strip=True)
                    break
            if not prix_txt:
                # cherche un prix dans le bloc
                import re
                m = re.search(r"[\d\s.]{3,}\s*(FCFA|F CFA|XAF)", bloc)
                prix_txt = m.group(0) if m else ""
            prix = parse_prix_xaf(prix_txt)
            if titre and len(titre) > 3:
                offres.append({"source": "Jumia Cameroun", "url": lien,
                              "titre": titre.strip(), "prix": prix,
                              "ville": "Douala", "produit": None})
        log.info("page %d : %d offres", page, len(vues))
        if not vues:
            break
    return offres


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
