"""Persistance de sessions/cookies (inspiré Phantombuster).

Cas d'usage : surveiller des zones nécessitant une connexion avec VOS
propres comptes (groupes Facebook, WhatsApp Web, marketplace privée).
Flux : login MANUEL une fois via tools/save_session.py -> cookies chiffrés ?
Non : fichier local chmod 600, jamais commité (voir .gitignore).

Format sessions/<nom>.json :
  {"domain": "facebook.com", "saved_at": "...", "cookies": [{"name":..,"value":..}]}
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("sniper.sessions")


def save_session_file(path: str, domain: str, cookies: list[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"domain": domain,
               "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "cookies": [{"name": c.get("name"), "value": c.get("value"),
                            "domain": c.get("domain", ""), "path": c.get("path", "/")}
                           for c in cookies if c.get("name")]}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        p.chmod(0o600)
    except OSError:
        pass
    log.info("Session %s : %d cookies -> %s", domain, len(payload["cookies"]), path)


def load_session_cookies(path: str) -> dict[str, str]:
    """Charge {nom: valeur} pour httpx. Fichier absent -> {} + warning."""
    p = Path(path)
    if not p.exists():
        log.warning("Session introuvable : %s (requêtes sans cookies)", path)
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    cookies = data.get("cookies", [])
    if isinstance(cookies, dict):  # tolère le format simple {nom: valeur}
        return {str(k): str(v) for k, v in cookies.items()}
    return {str(c["name"]): str(c.get("value", "")) for c in cookies if c.get("name")}
