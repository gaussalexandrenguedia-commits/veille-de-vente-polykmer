"""SQUELETTE Playwright — pages/groupes Facebook (phase 2).

⚠️ Facebook impose un login et des limites strictes. Stratégie recommandée :
  1. Compte dédié "veille" membre des groupes ciblés (avec accord des admins).
  2. Session persistante (user_data_dir) ouverte UNE fois à la main.
  3. Extraction lente (1 page / 10-20 s), petits volumes quotidiens.
  4. En cas de blocage -> bascule formulaire "relevé digital" semi-manuel.

Prérequis : pip install playwright && playwright install chromium
Usage : python facebook_playwright_skeleton.py --page "https://www.facebook.com/groups/XXXX" --out ../data/fb.json
"""
from __future__ import annotations

import argparse
import json
import time

PAGES_PILOTES = [
    # TODO phase 2 : renseigner 50 pages/groupes avec accord (nom, URL, catégorie)
    # {"nom": "Vente en ligne Douala", "url": "https://www.facebook.com/groups/XXXX", "categorie": "généraliste"},
]


def extraire_posts(url_page: str, max_posts: int = 20, headless: bool = False):
    from playwright.sync_api import sync_playwright

    posts = []
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir="./.fb-profile", headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        page.goto(url_page, wait_until="domcontentloaded", timeout=60000)
        print(">> Si login requis : connectez-vous dans la fenêtre, puis Entrée…")
        if not headless:
            input()
        for _ in range(6):  # scroll doux
            page.mouse.wheel(0, 1500)
            time.sleep(3)
        # Sélecteurs volatils : à ajuster + fallback copier-coller assisté
        articles = page.query_selector_all("div[role='article']")
        for art in articles[:max_posts]:
            try:
                texte = art.inner_text()[:2000]
            except Exception:
                texte = ""
            if len(texte) > 20:
                posts.append({"url": url_page, "texte": texte,
                             "likes": None, "commentaires": None})
            time.sleep(1)
        ctx.close()
    return posts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=(PAGES_PILOTES[0]["url"] if PAGES_PILOTES else ""))
    ap.add_argument("--max-posts", type=int, default=20)
    ap.add_argument("--out", default="../data/fb_posts.json")
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    if not args.page:
        print("Renseignez PAGES_PILOTES ou passez --page URL")
        return
    posts = extraire_posts(args.page, args.max_posts, args.headless)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"{len(posts)} posts -> {args.out}")


if __name__ == "__main__":
    main()
