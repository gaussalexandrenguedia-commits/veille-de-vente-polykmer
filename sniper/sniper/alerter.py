"""Alertes : Telegram one-click + Apprise fan-out + API veille.

Sans token configuré -> mode dry-run (log uniquement).
Carte d'action (`actions_card:`) : boutons WhatsApp vendeur pré-rempli,
appel direct, offre, dashboard — variables {url} {title} {prix} {ville}
{seller_phone} {seller_phone_digits} {wa_text} {dashboard}.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

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

    # ── carte d'action ──
    def render(self, tpl: str, watch: dict, signal: Signal) -> str:
        d = signal.detail
        phone = re.sub(r"[^\d]", "", str(d.get("seller_phone") or ""))
        prix = d.get("prix") or d.get("prix_avant")
        var = {"url": watch.get("url", ""), "title": signal.title,
               "watch": watch.get("name", watch.get("id", "")),
               "ville": watch.get("ville", ""), "rule": signal.rule,
               "prix": f"{prix:,.0f}".replace(",", " ") if prix else "",
               "seller_phone": str(d.get("seller_phone") or ""),
               "seller_phone_digits": phone, "dashboard": self.dashboard}
        out = tpl
        for k, v in var.items():
            out = out.replace("{" + k + "}", v)
        return out

    def keyboard(self, watch: dict, signal: Signal) -> dict:
        card = watch.get("actions_card") or {}
        buttons = card.get("buttons") or [
            {"label": "🔗 Voir l'offre", "url": "{url}"},
        ]
        rows = []
        for b in buttons:
            if b.get("requires") == "seller_phone" and not signal.detail.get("seller_phone"):
                continue  # pas de numéro -> bouton masqué
            url = self.render(b["url"], watch, signal)
            url = url.replace("{wa_text}", quote(self.render(
                card.get("wa_text", "Bonjour, '{watch}' à {prix} XAF m'intéresse. Dispo ?"),
                watch, signal)))
            rows.append([{"text": self.render(b.get("label", "Ouvrir"), watch, signal),
                          "url": url}])
        if card.get("dashboard", True) and self.dashboard:
            rows.append([{"text": "📊 Dashboard", "url": self.dashboard}])
        return {"inline_keyboard": rows or [[{"text": "🔗 Voir", "url": watch.get("url", "")}]]}

    def format_telegram(self, watch: dict, signal: Signal) -> str:
        lignes = [f"{EMOJI.get(signal.severity, '🟡')} *{signal.title}*",
                  f"_{watch.get('name', watch['id'])}_ · {watch.get('ville', '')}"]
        d = signal.detail
        if "drop_pct" in d:
            lignes.append(f"Baisse : *-{d['drop_pct']:.1f} %*")
        if d.get("prix"):
            lignes.append(f"Prix : *{d['prix']:,.0f} XAF*".replace(",", " "))
        if "seuil" in d:
            lignes.append(f"Seuil : {d['seuil']:,.0f} XAF".replace(",", " "))
        if d.get("item_id"):
            lignes.append(f"Item : `{d['item_id']}`")
        if d.get("seller_phone"):
            lignes.append(f"☎️ Vendeur : `{d['seller_phone']}` — bouton WhatsApp ⬇️")
        if d.get("semantic"):
            lignes.append(f"🧠 Filtre : {d['semantic']}")
        lignes.append(f"Règle : `{signal.rule}` · gravité : {signal.severity}")
        return "\n".join(lignes)

    async def send_telegram(self, client: httpx.AsyncClient, watch: dict, signal: Signal) -> int:
        texte = self.format_telegram(watch, signal)
        if self.dry_run:
            log.warning("[dry-run] TELEGRAM : %s", texte.replace("\n", " | "))
            return 0
        t0 = time.perf_counter()
        for chat in self.chat_ids:
            try:
                r = await client.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={"chat_id": chat, "text": texte, "parse_mode": "Markdown",
                          "reply_markup": self.keyboard(watch, signal),
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
