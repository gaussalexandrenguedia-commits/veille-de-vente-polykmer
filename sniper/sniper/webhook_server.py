"""Serveur de webhooks entrants — le chemin < 1 s (push, pas de polling).

Lancement :
    uvicorn sniper.webhook_server:app --host 0.0.0.0 --port 8001
    # config via SNIPER_CONFIG (défaut: config/watches.yaml)
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from .alerter import Alerter
from .config import load_config
from .extractors import page_hash
from .rules import evaluate
from .semantic import filter_signals
from .store import Store

CONFIG_PATH = os.getenv("SNIPER_CONFIG", "config/watches.yaml")
API_KEY = os.getenv("API_KEY_INGEST", "")

app = FastAPI(title="Veille Sniper — webhooks", version="0.2.0")
cfg = load_config(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else {"global": {}, "watches": []}
store = Store(cfg.get("global", {}).get("state_db", "state/sniper.db"))
alerter = Alerter(cfg)
WATCHES = {w["id"]: w for w in cfg.get("watches", [])}


class Push(BaseModel):
    price: float | None = None
    stock: bool | None = None
    text: str = ""
    items: list[str] | None = None
    seller_phone: str | None = None


def _check(x_api_key: str | None):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(403, "Clé API invalide")


@app.get("/healthz")
def healthz():
    return {"ok": True, "watches": sorted(WATCHES)}


@app.get("/status")
def status():
    return {wid: store.get_state(wid) for wid in WATCHES}


@app.get("/selectors/{watch_id}")
def selectors(watch_id: str):
    """Santé des sélecteurs (auto-réparation) : succès/échecs par sélecteur."""
    if watch_id not in WATCHES:
        raise HTTPException(404, f"Watch inconnue : {watch_id}")
    return store.selector_report(watch_id)


@app.post("/hook/{watch_id}")
async def hook(watch_id: str, push: Push, x_api_key: str | None = Header(default=None)):
    t0 = time.perf_counter()
    _check(x_api_key)
    watch = WATCHES.get(watch_id)
    if not watch:
        raise HTTPException(404, f"Watch inconnue : {watch_id}")
    obs = {"price": push.price, "stock": push.stock, "text": push.text[:20000],
           "items": push.items, "seller_phone": push.seller_phone,
           "hash": page_hash(push.text)}
    prev = store.get_state(watch_id)
    store.set_state(watch_id, obs)
    g = cfg.get("global", {})
    envoyees: list[str] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        signals = await filter_signals(watch, obs, evaluate(watch, obs, prev), client)
        for sig in signals:
            sig.detail.setdefault("seller_phone", obs.get("seller_phone"))
            if store.is_duplicate(sig.dedup_sig, g.get("dedup_ttl", 86400)):
                continue
            if not store.cooldown_ok(sig.cooldown_key, g.get("default_cooldown", 300)):
                continue
            await alerter.dispatch(client, watch, sig)
            store.mark_alert(sig.cooldown_key)
            envoyees.append(sig.title)
    total_ms = int((time.perf_counter() - t0) * 1000)
    return {"watch": watch_id, "alertes": envoyees, "latency_ms": total_ms}
