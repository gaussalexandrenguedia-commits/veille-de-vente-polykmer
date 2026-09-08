"""Construction d'une observation depuis un FetchResult + config 'extract'.

Observation = {"price": float|None, "stock": bool|None,
               "text": str, "items": list[str]|None, "hash": str}
"""
from __future__ import annotations

from .extractors import (extract_regex, json_path, normalize_stock, page_hash,
                         parse_prix_xaf, to_json_preview)


def _css_text(html: str, selector: str) -> str | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one(selector)
    return el.get_text(" ", strip=True) if el else None


def build_observation(watch: dict, result) -> dict:
    ext = watch.get("extract", {}) or {}
    obs: dict = {"price": None, "stock": None, "text": "", "items": None, "hash": ""}

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
        obs["text"] = to_json_preview(data)

    if result.text:
        if not obs["text"]:
            obs["text"] = result.text[:20000]
        if obs["price"] is None and ext.get("price_regex"):
            m = extract_regex(result.text, ext["price_regex"])
            obs["price"] = parse_prix_xaf(m)
        if obs["price"] is None and ext.get("price_css"):
            obs["price"] = parse_prix_xaf(_css_text(result.text, ext["price_css"]))
        if obs["stock"] is None and (ext.get("stock_present") or ext.get("stock_absent")):
            if ext.get("stock_absent") and extract_regex(result.text, ext["stock_absent"], 0):
                obs["stock"] = False
            elif ext.get("stock_present") and extract_regex(result.text, ext["stock_present"], 0):
                obs["stock"] = True

    # cible démo : même schéma que api_json
    if watch.get("type") == "demo" and data is not None:
        try:
            obs["price"] = parse_prix_xaf(json_path(data, "data.prix"))
            obs["stock"] = normalize_stock(json_path(data, "data.en_stock"))
        except KeyError:
            pass

    obs["hash"] = page_hash(f"{obs['price']}|{obs['stock']}|{obs['text'][:5000]}")
    return obs
