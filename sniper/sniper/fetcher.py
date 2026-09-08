"""Fetching async : httpx par défaut, impersonation TLS optionnelle.

- Clients persistants (keep-alive) mutualisés par (proxy, impersonate) ;
- cookies de session + headers de profils stealth passés par requête ;
- requêtes conditionnelles ETag/Last-Modified (304 = rien à faire) ;
- `impersonate: chrome124` utilise curl_cffi si installé, sinon repli httpx.

Objectif hot-tier sur endpoint API : réponse typique < 100 ms.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("sniper.fetcher")
_WARNED_IMPERSONATE = False


@dataclass
class FetchResult:
    ok: bool
    status: int = 0
    text: str = ""
    json: dict | list | None = None
    latency_ms: int = 0
    not_modified: bool = False
    error: str = ""
    headers: dict = field(default_factory=dict)


_DEMO_COUNT: dict[str, int] = {}


def build_client(user_agent: str, max_parallel: int = 10,
                 proxy: str | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent, "Accept-Language": "fr-FR,fr;q=0.9"},
        timeout=httpx.Timeout(15.0, connect=5.0),
        limits=httpx.Limits(max_connections=max_parallel * 2,
                            max_keepalive_connections=max_parallel),
        follow_redirects=True,
        proxy=proxy,
    )


class _ImpersonatedClient:
    """Adaptateur curl_cffi (empreinte TLS navigateur) — même interface .get()."""

    def __init__(self, impersonate: str, proxy: str | None):
        from curl_cffi.requests import AsyncSession
        self._s = AsyncSession(impersonate=impersonate, proxy=proxy,
                               timeout=15, allow_redirects=True)

    async def get(self, url, headers=None, cookies=None, timeout=15.0):
        return await self._s.get(url, headers=headers or {},
                                 cookies=cookies or {}, timeout=timeout)

    async def aclose(self):
        await self._s.close()


class ClientPool:
    """Cache de clients par (proxy, impersonate)."""

    def __init__(self, user_agent: str, max_parallel: int = 10):
        self.ua = user_agent
        self.mp = max_parallel
        self._pool: dict[tuple[str, str], object] = {}

    def get(self, proxy: str | None = None, impersonate: str | None = None):
        global _WARNED_IMPERSONATE
        key = (proxy or "", impersonate or "")
        if key not in self._pool:
            if impersonate:
                try:
                    self._pool[key] = _ImpersonatedClient(impersonate, proxy)
                    log.info("Client TLS impersonate=%s proxy=%s", impersonate, bool(proxy))
                except ImportError:
                    if not _WARNED_IMPERSONATE:
                        log.warning("curl_cffi absent — repli httpx (pip install curl-cffi)")
                        _WARNED_IMPERSONATE = True
                    self._pool[key] = build_client(self.ua, self.mp, proxy)
            else:
                self._pool[key] = build_client(self.ua, self.mp, proxy)
        return self._pool[key]

    async def aclose_all(self):
        for c in self._pool.values():
            try:
                await c.aclose()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        self._pool.clear()


def fetch_demo(watch: dict) -> FetchResult:
    import random
    t0 = time.perf_counter()
    wid = watch["id"]
    cfg = watch.get("demo", {})
    base = float(cfg.get("base_price", 10000))
    vol = float(cfg.get("volatility", 0.03))
    n = _DEMO_COUNT.get(wid, 0) + 1
    _DEMO_COUNT[wid] = n
    prix = base * (1 + random.gauss(0, vol))
    if n % int(cfg.get("drop_every", 12)) == 0:
        prix *= 0.90
    return FetchResult(ok=True, status=200,
                       json={"data": {"prix": round(prix), "en_stock": True}},
                       latency_ms=int((time.perf_counter() - t0) * 1000))


async def fetch(client, watch: dict, cache: dict[str, dict[str, str]],
                extra_headers: dict | None = None,
                cookies: dict | None = None) -> FetchResult:
    if watch.get("type") == "demo":
        return fetch_demo(watch)
    t0 = time.perf_counter()
    url = watch["url"]
    headers = {**(extra_headers or {}), **watch.get("headers", {})}
    cond = cache.get(url, {})
    if cond.get("etag"):
        headers["If-None-Match"] = cond["etag"]
    if cond.get("last_modified"):
        headers["If-Modified-Since"] = cond["last_modified"]
    try:
        r = await client.get(url, headers=headers, cookies=cookies or {}, timeout=15.0)
    except Exception as e:  # httpx.RequestError, curl_cffi.errors…
        return FetchResult(ok=False, error=f"{type(e).__name__}: {str(e)[:150]}",
                           latency_ms=int((time.perf_counter() - t0) * 1000))
    lat = int((time.perf_counter() - t0) * 1000)
    status = getattr(r, "status_code", 0)
    if status == 304:
        return FetchResult(ok=True, status=304, not_modified=True, latency_ms=lat)
    if status in (429, 403):
        return FetchResult(ok=False, status=status,
                           error=f"HTTP {status} — ralentir (risque de ban)",
                           latency_ms=lat)
    if status >= 400:
        return FetchResult(ok=False, status=status, error=f"HTTP {status}", latency_ms=lat)
    hdrs = getattr(r, "headers", {}) or {}
    get = hdrs.get if hasattr(hdrs, "get") else (lambda k, d="": d)
    if get("etag") or get("last-modified"):
        cache[url] = {"etag": get("etag", ""), "last_modified": get("last-modified", "")}
    data = None
    if watch.get("type") == "api_json":
        try:
            data = r.json()
        except ValueError:
            return FetchResult(ok=False, status=status, error="JSON invalide", latency_ms=lat)
    text = getattr(r, "text", "") or ""
    return FetchResult(ok=True, status=status, text=text[:100000], json=data, latency_ms=lat)
