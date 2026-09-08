"""Construction d'une observation depuis un FetchResult + config 'extract'.

Observation = {"price", "stock", "text", "items", "hash",
               "seller_phone", "zone_ok", "selector_used"}

Pipeline HTML : zone (ciblage Visualping-like) -> chaîne CSS auto-réparée
-> regex -> repli sémantique -> nettoyage compact (Firecrawl-like).
"""
from __future__ import annotations

import logging
import re

from .cleaner import clean_html_to_text
from .extractors import (extract_regex, json_path, normalize_stock, page_hash,
                         parse_prix_xaf, to_json_preview)
from .healer import best_price, extract_zone, select_first, soup_of

log = logging.getLogger("sniper.observe")
PHONE_CLEAN = re.compile(r"[\s.\-()]")


def _chain_cfg(ext: dict, single: str, chain: str) -> list[str]:
    out = list(ext.get(chain) or [])
    if ext.get(single):
        out.append(ext[single])
    return out


def build_observation(watch: dict, result, store=None) -> dict:
    ext = watch.get("extract", {}) or {}
    wid = watch.get("id", "?")
    obs: dict = {"price": None, "stock": None, "text": "", "items": None,
                 "hash": "", "seller_phone": None, "zone_ok": False,
                 "selector_used": None}

    def stats(sel: str, ok: bool):
        if store is not None:
            store.record_selector(wid, sel, ok)

    data = result.json
    if data is not None:
        if ext.get("price_jsonpath"):
            try:
                obs["price"] = parse_prix_xaf(json_path(data, ext["price_jsonpath"]))
            except (KeyError, IndexError, ValueError):
                pass
        if ext.get("stock_jsonpath"):
            try:
                obs["stock"] = normalize_stock(json_path(data, ext["stock_jsonpath"]))
            except (KeyError, IndexError):
                pass
        if ext.get("items_jsonpath"):
            try:
                arr = json_path(data, ext["items_jsonpath"])
                key = ext.get("items_id_key", "id")
                obs["items"] = [str(i.get(key, i)) if isinstance(i, dict) else str(i)
                                for i in (arr if isinstance(arr, list) else [])]
            except (KeyError, IndexError):
                pass
        obs["text"] = to_json_preview(data, ext.get("max_text_chars", 20000))

    html = result.text or ""
    soup = None
    scoped = html
    if html:
        soup = soup_of(html)
        zones = _chain_cfg(ext, "zone_css", "zone_css_chain")
        if zones:
            used, zh = extract_zone(soup, zones, stats)
            if zh:
                scoped, obs["zone_ok"], obs["selector_used"] = zh, True, used
            else:
                log.warning("[%s] zone introuvable (%s) — repli page entière", wid, zones)

        # ── prix : chaîne CSS -> regex -> repli sémantique ──
        if obs["price"] is None:
            chain = _chain_cfg(ext, "price_css", "price_css_chain")
            used, txt = select_first(soup_of(scoped), chain, stats)
            if txt and (p := parse_prix_xaf(txt)) is not None:
                obs["price"], obs["selector_used"] = p, used
                if chain and used != chain[0]:
                    log.warning("[%s] 🩹 prix auto-réparé via %r (config: %r)",
                                wid, used, chain[0])
            elif ext.get("price_regex"):
                m = extract_regex(scoped, ext["price_regex"])
                obs["price"] = parse_prix_xaf(m)
                if obs["price"] is not None:
                    obs["selector_used"] = "regex"
            if obs["price"] is None:
                obs["price"] = best_price(scoped if not zones or obs["zone_ok"] else html)
                if obs["price"] is not None:
                    obs["selector_used"] = "semantique"

        # ── stock via mots-clés sur le texte de la zone ──
        if obs["stock"] is None and (ext.get("stock_present") or ext.get("stock_absent")):
            if ext.get("stock_absent") and extract_regex(scoped, ext["stock_absent"], 0):
                obs["stock"] = False
            elif ext.get("stock_present") and extract_regex(scoped, ext["stock_present"], 0):
                obs["stock"] = True

        # ── téléphone vendeur (bouton WhatsApp one-click) ──
        if ext.get("seller_phone_regex"):
            m = extract_regex(scoped, ext["seller_phone_regex"]) or \
                extract_regex(html, ext["seller_phone_regex"])
            if m:
                obs["seller_phone"] = PHONE_CLEAN.sub("", m).strip()

        # ── texte : nettoyé compact par défaut ──
        max_chars = ext.get("max_text_chars", 20000)
        if ext.get("clean_html", True):
            obs["text"] = clean_html_to_text(scoped, max_chars)
        else:
            obs["text"] = scoped[:max_chars]

    if watch.get("type") == "demo" and data is not None:
        try:
            obs["price"] = parse_prix_xaf(json_path(data, "data.prix"))
            obs["stock"] = normalize_stock(json_path(data, "data.en_stock"))
        except KeyError:
            pass

    obs["hash"] = page_hash(f"{obs['price']}|{obs['stock']}|{obs['text'][:5000]}")
    return obs
