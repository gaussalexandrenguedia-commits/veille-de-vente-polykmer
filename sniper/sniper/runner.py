"""Boucle de surveillance asyncio : 1 tâche / watch, backoff anti-ban.

Usage :
    python -m sniper.runner --config config/watches.yaml
    python -m sniper.runner --config config/watches.yaml --once --watch demo-riz-mokolo
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import time

from .alerter import Alerter
from .config import load_config
from .fetcher import ClientPool, fetch
from .observe import build_observation
from .rules import evaluate
from .semantic import filter_signals
from .sessions import load_session_cookies
from .stealth import impersonate_for, profile_headers, proxy_for
from .store import Store

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sniper.runner")


class Watchdog:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        g = cfg["global"]
        self.store = Store(g["state_db"])
        self.alerter = Alerter(cfg)
        self.pool = ClientPool(g.get("user_agent", "veille-sniper"), g["max_parallel"])
        self.cache_cond: dict[str, dict[str, str]] = {}
        self.sem = asyncio.Semaphore(g["max_parallel"])
        self.counters: dict[str, int] = {}
        # cookies de session pré-chargés (1 fois au démarrage)
        self.sessions: dict[str, dict] = {}
        for w in cfg.get("watches", []):
            if w.get("session"):
                self.sessions[w["id"]] = load_session_cookies(w["session"])

    async def cycle(self, watch: dict) -> dict:
        t0 = time.perf_counter()
        wid = watch["id"]
        n = self.counters.get(wid, 0) + 1
        self.counters[wid] = n
        stats = {"watch": wid, "fetch_ms": 0, "signals": 0, "alert_ms": 0}
        client = self.pool.get(proxy_for(self.cfg["global"], watch, n),
                               impersonate_for(watch))
        async with self.sem:
            res = await fetch(client, watch, self.cache_cond,
                              extra_headers=profile_headers(watch, n),
                              cookies=self.sessions.get(wid))
        stats["fetch_ms"] = res.latency_ms
        if not res.ok:
            log.warning("[%s] fetch KO : %s", wid, res.error)
            return stats
        if res.not_modified:
            log.debug("[%s] 304 non modifié (%d ms)", wid, res.latency_ms)
            return stats
        obs = build_observation(watch, res, self.store)
        prev = self.store.get_state(wid)
        self.store.set_state(wid, obs)
        g = self.cfg["global"]
        # gate sémantique AVANT dédup/cooldown (les signaux rejetés ne polluent pas)
        signals = await filter_signals(watch, obs, evaluate(watch, obs, prev),
                                       self.pool.get())
        for sig in signals:
            sig.detail.setdefault("seller_phone", obs.get("seller_phone"))
            stats["signals"] += 1
            if self.store.is_duplicate(sig.dedup_sig, g["dedup_ttl"]):
                log.info("[%s] doublon ignoré : %s", wid, sig.title)
                continue
            rule_cfg = next((r for r in watch.get("rules", [])
                             if r.get("type") in (sig.rule, sig.rule.replace("new_item", "new_items"))), {})
            cooldown = int(rule_cfg.get("cooldown", watch.get("cooldown", g["default_cooldown"])))
            if not self.store.cooldown_ok(sig.cooldown_key, cooldown):
                log.info("[%s] cooldown : %s", wid, sig.title)
                continue
            lat = await self.alerter.dispatch(self.pool.get(), watch, sig)
            stats["alert_ms"] = lat
            self.store.mark_alert(sig.cooldown_key)
            total = int((time.perf_counter() - t0) * 1000)
            log.warning("[%s] 🚨 %s (fetch %d ms, alerte %d ms, total %d ms)",
                        wid, sig.title, res.latency_ms, lat, total)
        return stats

    async def loop(self, watch: dict) -> None:
        fails = 0
        interval = max(int(watch.get("interval", 300)), 1)
        log.info("[%s] démarrage (toutes les %ds, tier %s)",
                 watch["id"], interval, watch.get("tier"))
        while True:
            try:
                await self.cycle(watch)
                fails = 0
            except Exception:  # noqa: BLE001 — une watch ne doit jamais tuer les autres
                fails += 1
                log.exception("[%s] erreur cycle (%d)", watch["id"], fails)
            backoff = min(2 ** fails, 32) if fails else 1
            jitter = interval * (0.85 + random.random() * 0.3)
            await asyncio.sleep(jitter * backoff)

    async def run(self, only: str | None = None, once: bool = False) -> None:
        try:
            watches = [w for w in self.cfg.get("watches", [])
                       if w.get("interval", 0) > 0 and (not only or w["id"] == only)]
            if once:
                for w in watches:
                    print(await self.cycle(w))
                return
            if not watches:
                log.error("Aucune watch à poller (toutes en webhook ?)")
                return
            await asyncio.gather(*(self.loop(w) for w in watches))
        finally:
            await self.pool.aclose_all()


def main() -> None:
    ap = argparse.ArgumentParser(description="Veille sniper — surveillance continue")
    ap.add_argument("--config", default="config/watches.yaml")
    ap.add_argument("--watch", default=None, help="Limiter à une watch (id)")
    ap.add_argument("--once", action="store_true", help="Un seul passage puis exit")
    args = ap.parse_args()
    cfg = load_config(args.config)
    asyncio.run(Watchdog(cfg).run(only=args.watch, once=args.once))


if __name__ == "__main__":
    main()
