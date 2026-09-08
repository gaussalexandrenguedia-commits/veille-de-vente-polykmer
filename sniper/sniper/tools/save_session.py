"""Sauvegarde de session manuelle (login persistant type Phantombuster).

Ouvre un VRAI navigateur où VOUS vous connectez à VOTRE compte
(Facebook, marketplace privée…), puis exporte les cookies vers
sessions/<nom>.json (chmod 600, jamais commité).

Usage :
    pip install playwright && playwright install chromium
    python -m sniper.tools.save_session --domain facebook.com --out sessions/facebook.json

    # …puis dans watches.yaml :  session: sessions/facebook.json

Variante sans navigateur (cookies déjà exportés via une extension) :
    python -m sniper.tools.save_session --from-json export.json --out sessions/x.json --domain example.com

⚠️ Vos comptes uniquement, usage conforme aux CGU. Ne partagez JAMAIS
ces fichiers (ils équivalent à votre mot de passe).
"""
from __future__ import annotations

import argparse
import json

from ..sessions import save_session_file


def login_and_export(domain: str, out: str, profile: str, start_url: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise SystemExit("Playwright requis : pip install playwright && playwright install chromium") from e
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=profile, headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        page = ctx.new_page()
        page.goto(start_url or f"https://{domain}", wait_until="domcontentloaded")
        print(f">> Connectez-vous à {domain} dans la fenêtre, puis Entrée ici…")
        input()
        cookies = [c for c in ctx.cookies() if domain in c.get("domain", "")]
        ctx.storage_state(path=out + ".state.json")  # réutilisable par Playwright
        ctx.close()
    if not cookies:
        raise SystemExit(f"Aucun cookie pour {domain} — connexion incomplète ?")
    save_session_file(out, domain, cookies)
    print(f"OK : {len(cookies)} cookies + storage_state ({out}.state.json)")


def from_json(in_path: str, out: str, domain: str) -> None:
    data = json.loads(open(in_path, encoding="utf-8").read())
    cookies = data if isinstance(data, list) else data.get("cookies", [])
    save_session_file(out, domain, cookies)
    print(f"OK : normalisé -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Login manuel + export cookies de session")
    ap.add_argument("--domain", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="./.login-profile")
    ap.add_argument("--start-url", default="")
    ap.add_argument("--from-json", default="")
    args = ap.parse_args()
    if args.from_json:
        assert args.domain, "--domain requis avec --from-json"
        from_json(args.from_json, args.out, args.domain)
    else:
        assert args.domain, "--domain requis"
        login_and_export(args.domain, args.out, args.profile, args.start_url)


if __name__ == "__main__":
    main()
