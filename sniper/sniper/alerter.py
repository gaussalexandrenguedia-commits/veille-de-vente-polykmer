"""Alertes : Telegram Bot API (push < 1 s) + Apprise (fan-out) + API veille.

Sans token configuré -> mode dry-run (log uniquement), parfait pour tester.
"""
from __future__ import annotations

import logging
import time

import httpx

from .rules import Signal

log = logging.getLogger("sniper.alerter")
EMOJI = {"rouge": "🔴", "jaune": "🟡", "vert": "🟢"}


class Alerter:
    def __init__(self, cfg: dict):
        tg = cfg.get("telegram", {}) or {}
        self.token = (tg.get("bot_token") or "").strip()
        self.chat_ids = [c.strip() for c in str(tg.get("chat_ids") or "").split(",") if c.strip()]
        self.dashboard = (tg.get("dashboard_url") or "").strip()
        self.apprise_urls = [u.strip() for u in str(cfg.get("apprise_urls") or "").split(";") if u.strip()]
        api = cfg.get("api_veille", {}) or {}
        self.api_url = (api.get("url") or "").rstrip("/")
        self.api_key = api.get("key") or ""
        self._apprise = None

    @property
    def dry_run(self) -> bool:
        return not (self.token and self.chat_ids)

    def format_telegram(self, watch: dict, signal: Signal) -> str:
        ville = watch.get("ville", "")
        lignes = [
            f"{EMOJI.get(signal.severity, '🟡')} *{signal.title}*",
            f"_{watch.get('name', watch['id'])}_ · {ville}",
        ]
        d = signal.detail
        if "drop_pct" in d:
            lignes.append(f"Baisse : *-{d['drop_pct']:.1f} %*")
        if "prix" in d and d["prix"]:
            lignes.append(f"Prix : *{d['prix']:,.0f} XAF*".replace(",", " "))
        if "seuil" in d:
            lignes.append(f"Seuil : {d['seuil']:,.0f} XAF".replace(",", " "))
        if "item_id" in d:
            lignes.append(f"Item : `{d['item_id']}`")
        lignes.append(f"Règle : `{signal.rule}` · gravité : {signal.severity}")
        return "\n".join(lignes)

    def keyboard(self, watch: dict) -> dict:
        boutons = [[{"text": "🔗 Voir l'offre", "url": watch.get("url", "https://example.com")}]]
        if self.dashboard:
            boutons.append([{"text": "📊 Dashboard", "url": self.dashboard}])
        return {"inline_keyboard": boutons}

    async def send_telegram(self, client: httpx.AsyncClient, watch: dict, signal: Signal) -> int:
        """Retourne la latence d'envoi en ms. 0 si dry-run."""
        texte = self.format_telegram(watch, signal)
        if self.dry_run:
            log.warning("[dry-run] TELEGRAM (pas de token) : %s", texte.replace("\n", " | "))
            return 0
        t0 = time.perf_counter()
        for chat in self.chat_ids:
            try:
                r = await client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={"chat_id": chat, "text": texte, "parse_mode": "Markdown",
                          "reply_markup": self.keyboard(watch),
                          "disable_web_page_preview": True},
                    timeout=10.0)
                if r.status_code != 200:
                    log.error("Telegram %s : %s", r.status_code, r.text[:200])
            except httpx.RequestError as e:
                log.error("Telegram erreur : %s", e)
        return int((time.perf_counter() - t0) * 1000)

    async def send_apprise(self, title: str, body: str) -> None:
        if not self.apprise_urls:
            return
        try:
            import apprise
        except ImportError:
            log.error("Apprise non installé (pip install apprise)")
            return
        if self._apprise is None:
            self._apprise = apprise.Apprise()
            for u in self.apprise_urls:
                self._apprise.add(u)
        ok = self._apprise.notify(body=body, title=title)
        log.info("Apprise fan-out %d canaux : %s", len(self.apprise_urls), "OK" if ok else "ÉCHEC")

    async def post_api_veille(self, client: httpx.AsyncClient, watch: dict, signal: Signal) -> None:
        """Stocke le signal comme offre dans l'API veille (/ingest/scraper)."""
        if not (self.api_url and self.api_key):
            return
        prix = signal.detail.get("prix") or signal.detail.get("prix_avant")
        offre = {"source": f"sniper:{watch['id']}", "url": watch.get("url", ""),
                 "titre": f"[{signal.rule}] {watch.get('name')}",
                 "prix": prix, "ville": watch.get("ville", "Douala"),
                 "produit": watch.get("produit_sku")}
        try:
            r = await client.post(f"{self.api_url}/api/v1/ingest/scraper",
                                  headers={"X-API-Key": self.api_key},
                                  json=[offre], timeout=15.0)
            log.info("API veille : %s %s", r.status_code, r.text[:150])
        except httpx.RequestError as e:
            log.error("API veille erreur : %s", e)

    async def dispatch(self, client: httpx.AsyncClient, watch: dict, signal: Signal) -> int:
        """Envoie selon actions configurées. Retourne latence Telegram en ms."""
        actions = watch.get("actions", {})
        lat = 0
        if actions.get("telegram"):
            lat = await self.send_telegram(client, watch, signal)
        if actions.get("apprise"):
            await self.send_apprise(f"[veille-sniper] {signal.title}",
                                    f"{watch.get('name')} — {watch.get('url')}")
        if actions.get("post_api"):
            await self.post_api_veille(client, watch, signal)
        return lat
