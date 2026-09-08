"""Discrétion & identités de navigation (rotation UA/profils/proxies).

Approche honnête et légale : on s'identifie avec des profils navigateur
standards, on espace les requêtes (voir garde-fous config), on utilise des
proxies UNIQUEMENT si fournis par l'utilisateur (abonnements légitimes).
Pas de contournement agressif (CAPTCHA, fingerprint spoofing hostile).

Options par watch (bloc `stealth:`) :
  profile: rotate | desktop | mobile | off   (défaut rotate)
  impersonate: chrome124 | safari15_5 | …    (nécessite `curl_cffi`, sinon repli httpx)
  proxies: [http://user:pass@host:port]      (round-robin ; défaut = proxies globaux)
"""
from __future__ import annotations

DESKTOP = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}
MOBILE = {
    "User-Agent": ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Upgrade-Insecure-Requests": "1",
}
_PROFILS = [DESKTOP, MOBILE]


def profile_headers(watch: dict, counter: int) -> dict:
    mode = (watch.get("stealth") or {}).get("profile", "rotate")
    if mode == "off":
        return {}
    if mode == "desktop":
        return dict(DESKTOP)
    if mode == "mobile":
        return dict(MOBILE)
    return dict(_PROFILS[counter % len(_PROFILS)])  # rotate


def proxy_for(global_cfg: dict, watch: dict, counter: int) -> str | None:
    st = watch.get("stealth") or {}
    pool = st.get("proxies", global_cfg.get("proxies", []))
    if not pool:
        return None
    return pool[counter % len(pool)]


def impersonate_for(watch: dict) -> str | None:
    return (watch.get("stealth") or {}).get("impersonate")
