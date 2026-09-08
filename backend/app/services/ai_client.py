"""Client Gemini (Google AI) : rotation de clés, repli de modèle, échecs propres.

- Clés : GEMINI_API_KEYS (virgules) lues via settings (backend/.env).
- Failover : 429/5xx -> clé suivante ; 404 modèle -> modèle suivant.
- Sans clé -> available=False, les routes basculent en heuristique offline.
- Les clés ne sont JAMAIS loguées ni exposées (voir mask_key).
"""
from __future__ import annotations

import base64
import json
import logging
import random
import re
import time

import httpx

log = logging.getLogger("ai.gemini")


class GeminiError(Exception):
    pass


def mask_key(k: str) -> str:
    return (k[:6] + "…" + k[-4:]) if len(k) > 12 else "***"


class GeminiClient:
    def __init__(self):
        from ..config import settings  # import tardif (tests sans settings)
        self.keys = [k.strip() for k in (settings.GEMINI_API_KEYS or "").split(",") if k.strip()]
        first = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.models = [first] + [m for m in ("gemini-2.5-flash", "gemini-2.0-flash") if m != first]

    @property
    def available(self) -> bool:
        return bool(self.keys)

    def info(self) -> dict:
        return {"ia_disponible": self.available, "nb_cles": len(self.keys),
                "cles": [mask_key(k) for k in self.keys], "modeles": self.models}

    async def _call(self, model: str, payload: dict) -> dict:
        errs = []
        for key in random.sample(self.keys, len(self.keys)):
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:generateContent")
            try:
                async with httpx.AsyncClient(timeout=30.0) as c:
                    r = await c.post(url, params={"key": key}, json=payload)
            except httpx.RequestError as e:
                errs.append(f"{mask_key(key)}: réseau {e!r}"[:120])
                continue
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503):
                errs.append(f"{mask_key(key)}: HTTP {r.status_code}")
                continue  # failover clé suivante
            raise GeminiError(f"HTTP {r.status_code}: {r.text[:200]}")
        raise GeminiError("clés épuisées/indisponibles (" + " | ".join(errs) + ")")

    @staticmethod
    def _parse(data: dict, json_mode: bool):
        try:
            txt = data["candidates"][0]["content"]["parts"][0].get("text", "")
        except (KeyError, IndexError, TypeError):
            raise GeminiError("réponse vide du modèle")
        txt = (txt or "").strip()
        if not json_mode:
            return txt
        txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
        try:
            return json.loads(txt)
        except ValueError:
            raise GeminiError(f"JSON invalide : {txt[:150]}")

    async def _gen(self, parts: list, system: str | None = None,
                   json_mode: bool = True, max_tokens: int = 800):
        if not self.available:
            raise GeminiError("aucune clé configurée (GEMINI_API_KEYS)")
        last: GeminiError | None = None
        for model in self.models:
            payload: dict = {"contents": [{"parts": parts}],
                             "generationConfig": {"temperature": 0,
                                                  "maxOutputTokens": max_tokens}}
            if json_mode:
                payload["generationConfig"]["response_mime_type"] = "application/json"
            if system:
                payload["system_instruction"] = {"parts": [{"text": system}]}
            try:
                return self._parse(await self._call(model, payload), json_mode)
            except GeminiError as e:
                last = e
                if "HTTP 404" in str(e):
                    log.warning("Modèle %s inconnu, repli suivant", model)
                    continue
                raise
        raise last or GeminiError("aucun modèle disponible")

    async def generate_json(self, prompt: str, system: str | None = None,
                            max_tokens: int = 800) -> dict:
        return await self._gen([{"text": prompt}], system, True, max_tokens)

    async def generate_text(self, prompt: str, system: str | None = None,
                            max_tokens: int = 500) -> str:
        return await self._gen([{"text": prompt}], system, False, max_tokens)

    async def analyze_image(self, data: bytes, mime: str, prompt: str,
                            max_tokens: int = 800) -> dict:
        parts = [{"inline_data": {"mime_type": mime,
                                  "data": base64.b64encode(data).decode()}},
                 {"text": prompt}]
        return await self._gen(parts, None, True, max_tokens)

    async def ping(self) -> dict:
        t0 = time.perf_counter()
        txt = await self.generate_text("Réponds uniquement : OK", max_tokens=10)
        return {"latence_ms": int((time.perf_counter() - t0) * 1000),
                "reponse": str(txt)[:50]}
