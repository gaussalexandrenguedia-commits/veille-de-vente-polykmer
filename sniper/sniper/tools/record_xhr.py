"""Enregistreur XHR/Fetch — « record once, poll fast forever » (pattern Apify/bots).

Charge UNE fois la page en vrai navigateur (Playwright), capture les
réponses JSON (XHR/Fetch), devine les jsonpaths de prix/stock, et génère
un squelette de watch `api_json` : le polling passe ensuite en httpx pur
(~50 ms au lieu de ~3 s en navigateur).

Usage :
    pip install playwright && playwright install chromium
    python -m sniper.tools.record_xhr --url "https://www.jumia.cm/..." --out capture.json

N'utilisez que sur des endpoints publics raisonnables ; le polling généré
reste soumis aux garde-fous (intervalles, CGU).
"""
from __future__ import annotations

import argparse
import json
import re

TRACKING_RE = re.compile(r"google-analytics|googletagmanager|facebook\.net|doubleclick|"
                         r"hotjar|segment\.io|sentry|intercom|clarity\.ms", re.I)
PRICE_KEYS = re.compile(r"prix|price|amount|montant|total|tarif", re.I)
STOCK_KEYS = re.compile(r"stock|disponib|availab|quantity|quantit", re.I)


def walk_paths(obj, prefix: str = "", depth: int = 0, max_depth: int = 4):
    """Génère (jsonpath, valeur) pour les feuilles scalaires."""
    if depth > max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_paths(v, f"{prefix}.{k}" if prefix else str(k), depth + 1, max_depth)
    elif isinstance(obj, list) and obj:
        yield from walk_paths(obj[0], f"{prefix}.0", depth + 1, max_depth)
    elif isinstance(obj, (int, float, str, bool)) and prefix:
        yield prefix, obj


def guess_paths(payload: dict | list) -> dict:
    prix, stock = [], []
    for path, val in walk_paths(payload):
        leaf = path.split(".")[-1]
        if PRICE_KEYS.search(leaf) and isinstance(val, (int, float)):
            prix.append(path)
        if STOCK_KEYS.search(leaf):
            stock.append(path)
    return {"price_jsonpath": prix[:3], "stock_jsonpath": stock[:3]}


def record(url: str, wait: int = 8, headed: bool = False) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise SystemExit("Playwright requis : pip install playwright && playwright install chromium") from e
    captures: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page()

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                if "json" not in ct or resp.status >= 400:
                    return
                if TRACKING_RE.search(resp.url):
                    return
                data = resp.json()
            except Exception:
                return
            keys = list(data.keys())[:12] if isinstance(data, dict) else [f"list[{len(data)}]"]
            captures.append({"url": resp.url[:300], "status": resp.status,
                             "keys": keys, "guessed": guess_paths(data)})

        page.on("response", on_response)
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(wait * 1000)
        browser.close()
    # dédup par URL
    vus, out = set(), []
    for c in captures:
        if c["url"] not in vus:
            vus.add(c["url"])
            out.append(c)
    return out


def yaml_snippet(watch_id: str, cap: dict) -> str:
    g = cap["guessed"]
    pj = g["price_jsonpath"][0] if g["price_jsonpath"] else "data.PRIX_?"
    sj = g["stock_jsonpath"][0] if g["stock_jsonpath"] else ""
    lines = [f"  - id: {watch_id}", "    tier: hot", "    interval: 30",
             "    type: api_json", f"    url: \"{cap['url']}\"",
             "    extract:", f"      price_jsonpath: \"{pj}\""]
    if sj:
        lines.append(f"      stock_jsonpath: \"{sj}\"")
    lines += ["    rules:", "      - {type: drop_pct, value: 10}",
              "    actions: {telegram: true, apprise: false, post_api: true}"]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Capture les endpoints XHR/JSON d'une page")
    ap.add_argument("--url", required=True)
    ap.add_argument("--wait", type=int, default=8)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--out", default="capture.json")
    ap.add_argument("--watch-id", default="api-capturee")
    args = ap.parse_args()
    caps = record(args.url, args.wait, args.headed)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(caps, f, ensure_ascii=False, indent=2)
    print(f"{len(caps)} endpoints JSON -> {args.out}")
    for c in caps[:10]:
        print(f"\n● {c['status']} {c['url']}\n  clés: {c['keys']}\n  devinés: {c['guessed']}")
    if caps:
        print("\n--- Squelette watches.yaml ---\n" + yaml_snippet(args.watch_id, caps[0]))


if __name__ == "__main__":
    main()
