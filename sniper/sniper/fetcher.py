"""Fetching async httpx : requêtes conditionnelles, timeouts courts, mode démo.

Objectif latence : connexion persistante (keep-alive), pas de JS par défaut.
Le rendu Playwright/JS reste du ressort de ChangeDetection.io (tier froid)
ou d'un worker séparé — voir docs/08-SNIPING-TEMPS-REEL.md.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class FetchResult:
    ok: bool
    status: int = 0
    text: str = ""
    json: dict | list | None = None
    latency_ms: int = 0
    not_modified: bool = False   # 304 : rien n'a changé, on saute l'évaluation
    error: str = ""
    headers: dict = field(default_factory=dict)


# Compteurs du générateur démo (baisse simulée tous les N passages)
_DEMO_COUNT: dict[str, int] = {}


def build_client(user_agent: str, max_parallel: int = 10) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent, "Accept-Language": "fr-FR,fr;q=0.9"},
        timeout=httpx.Timeout(15.0, connect=5.0),
        limits=httpx.Limits(max_connections=max_parallel * 2, max_keepalive_connections=max_parallel),
        follow_redirects=True,
    )


def fetch_demo(watch: dict) -> FetchResult:
    """Cible synthétique sans réseau : marche aléatoire + chute périodique."""
    t0 = time.perf_counter()
    wid = watch["id"]
    cfg = watch.get("demo", {})
    base = float(cfg.get("base_price", 10000))
    vol = float(cfg.get("volatility", 0.03))
    n = _DEMO_COUNT.get(wid, 0) + 1
    _DEMO_COUNT[wid] = n
    prix = base * (1 + random.gauss(0, vol))
    if n % int(cfg.get("drop_every", 12)) == 0:  # chute simulée -> déclenche drop_pct
        prix *= 0.90
    return FetchResult(ok=True, status=200,
                       json={"data": {"prix": round(prix), "en_stock": True}},
                       latency_ms=int((time.perf_counter() - t0) * 1000))


async def fetch(client: httpx.AsyncClient, watch: dict,
                cache: dict[str, dict[str, str]]) -> FetchResult:
    """GET avec ETag/Last-Modified. Type 'demo' = sans réseau."""
    if watch.get("type") == "demo":
        return fetch_demo(watch)
    t0 = time.perf_counter()
    url = watch["url"]
    headers = dict(watch.get("headers", {}))
    cond = cache.get(url, {})
    if cond.get("etag"):
        headers["If-None-Match"] = cond["etag"]
    if cond.get("last_modified"):
        headers["If-Modified-Since"] = cond["last_modified"]
    try:
        r = await client.get(url, headers=headers)
    except httpx.RequestError as e:
        return FetchResult(ok=False, error=f"{type(e).__name__}: {e}",
                           latency_ms=int((time.perf_counter() - t0) * 1000))
    lat = int((time.perf_counter() - t0) * 1000)
    if r.status_code == 304:
        return FetchResult(ok=True, status=304, not_modified=True, latency_ms=lat)
    if r.status_code in (429, 403):
        return FetchResult(ok=False, status=r.status_code,
                           error=f"HTTP {r.status_code} — ralentir (risque de ban)",
                           latency_ms=lat)
    if r.status_code >= 400:
        return FetchResult(ok=False, status=r.status_code,
                           error=f"HTTP {r.status_code}", latency_ms=lat)
    if r.headers.get("etag") or r.headers.get("last-modified"):
        cache[url] = {"etag": r.headers.get("etag", ""),
                      "last_modified": r.headers.get("last-modified", "")}
    data = None
    if watch.get("type") == "api_json":
        try:
            data = r.json()
        except ValueError:
            return FetchResult(ok=False, status=r.status_code,
                               error="JSON invalide", latency_ms=lat)
    return FetchResult(ok=True, status=r.status_code, text=r.text[:100000],
                       json=data, latency_ms=lat)
