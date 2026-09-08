"""Filtrage sémantique des signaux (inspiré ScrapeGraphAI / Hexowatch).

Un bloc `semantic:` dans la watch valide chaque signal AVANT l'alerte.
Backends :
  - heuristic (défaut, 100 % hors-ligne) : must_include / must_exclude /
    contraintes numériques par regex / prix min-max ;
  - ollama : petit LLM local (ex. llama3.1:8b) via http://localhost:11434 ;
  - openai_compatible : tout endpoint /chat/completions.

Exemple (groupe électrogène > 5 kVA sous 200 000 FCFA) : voir tests +
watches.example.yaml. `on_error: allow|block` si le backend LLM est injoignable.
"""
from __future__ import annotations

import json
import logging
import re

from .rules import Signal

log = logging.getLogger("sniper.semantic")


def _to_number(s: str) -> float | None:
    s = re.sub(r"[\s\u00a0\u202f]", "", s).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b,
       ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "<": lambda a, b: a < b, "<=": lambda a, b: a <= b}


def heuristic_pass(criteria: dict, obs: dict, signal: Signal) -> tuple[bool, str]:
    texte = f"{obs.get('text', '')} {signal.title} {signal.detail}".lower()
    for mot in criteria.get("must_include", []):
        if str(mot).lower() not in texte:
            return False, f"mot requis absent : {mot!r}"
    for mot in criteria.get("must_exclude", []):
        if str(mot).lower() in texte:
            return False, f"mot exclu présent : {mot!r}"
    prix = obs.get("price")
    if criteria.get("max_price") is not None and prix is not None \
            and prix > float(criteria["max_price"]):
        return False, f"prix {prix:,.0f} > max {criteria['max_price']}"
    if criteria.get("min_price") is not None and prix is not None \
            and prix < float(criteria["min_price"]):
        return False, f"prix {prix:,.0f} < min {criteria['min_price']}"
    for num in criteria.get("numeric", []):
        m = re.search(num.get("pattern", ""), texte, re.I | re.S)
        if not m:
            return False, f"motif numérique absent : {num.get('pattern')}"
        val = _to_number(m.group(1) if m.lastindex else m.group(0))
        if val is None:
            return False, f"nombre illisible : {m.group(0)[:30]!r}"
        op = OPS.get(num.get("op", "=="))
        if op is None or not op(val, float(num.get("value", 0))):
            return False, f"{val} {num.get('op')} {num.get('value')} faux"
    return True, "heuristique OK"


def _prompt(criteria: dict, obs: dict, signal: Signal, ville: str) -> str:
    crits = []
    if criteria.get("must_include"):
        crits.append(f"Doit concerner : {', '.join(criteria['must_include'])}")
    if criteria.get("must_exclude"):
        crits.append(f"Exclure si : {', '.join(criteria['must_exclude'])}")
    for num in criteria.get("numeric", []):
        crits.append(f"Contrainte : {num.get('pattern')} {num.get('op')} {num.get('value')}")
    if criteria.get("max_price") is not None:
        crits.append(f"Prix max : {criteria['max_price']} XAF")
    if criteria.get("instruction"):
        crits.append(criteria["instruction"])
    prix = obs.get("price")
    return ("Tu es un filtre d'opportunités commerciales strict. "
            "Réponds UNIQUEMENT en JSON : {\"match\": true|false, \"reason\": \"...\"}.\n"
            f"Critères : {'; '.join(crits) or 'aucun'}\n"
            f"Signal : {signal.title} | prix : {prix} XAF | ville : {ville}\n"
            f"Annonce :\n{(obs.get('text', '') or '')[:1500]}")


async def _ollama_pass(client, cfg: dict, prompt: str) -> tuple[bool, str]:
    o = cfg.get("ollama", {})
    r = await client.post(o.get("url", "http://localhost:11434") + "/api/generate",
                          json={"model": o.get("model", "llama3.1:8b"),
                                "prompt": prompt, "stream": False,
                                "format": "json",
                                "options": {"temperature": 0, "num_predict": 150}},
                          timeout=30.0)
    r.raise_for_status()
    data = json.loads(r.json().get("response", "{}"))
    return bool(data.get("match")), str(data.get("reason", "ollama"))


async def _openai_pass(client, cfg: dict, prompt: str) -> tuple[bool, str]:
    o = cfg.get("openai_compatible", {})
    r = await client.post(o.get("base_url", "").rstrip("/") + "/chat/completions",
                          headers={"Authorization": f"Bearer {o.get('api_key', '')}"},
                          json={"model": o.get("model", "gpt-4o-mini"), "temperature": 0,
                                "response_format": {"type": "json_object"},
                                "messages": [{"role": "user", "content": prompt}]},
                          timeout=30.0)
    r.raise_for_status()
    data = json.loads(r.json()["choices"][0]["message"]["content"])
    return bool(data.get("match")), str(data.get("reason", "llm"))


async def filter_signals(watch: dict, obs: dict, signals: list[Signal],
                         http_client=None) -> list[Signal]:
    """Applique le gate sémantique ; sans bloc `semantic:` -> inchangé."""
    sem = watch.get("semantic")
    if not sem or not signals:
        return signals
    backend = sem.get("backend", "heuristic")
    applies = set(sem.get("applies_to", ["*"]))
    criteria = sem.get("criteria", {})
    on_error = sem.get("on_error", "allow")
    prompt = _prompt(criteria, obs, signals[0], watch.get("ville", "")) \
        if backend in ("ollama", "openai_compatible") else ""
    out: list[Signal] = []
    for sig in signals:
        if "*" not in applies and sig.rule not in applies:
            out.append(sig)
            continue
        try:
            if backend == "heuristic":
                ok, raison = heuristic_pass(criteria, obs, sig)
            elif backend == "ollama":
                assert http_client is not None
                ok, raison = await _ollama_pass(http_client, sem, prompt)
            else:
                assert http_client is not None
                ok, raison = await _openai_pass(http_client, sem, prompt)
        except Exception as e:  # noqa: BLE001
            ok, raison = (on_error == "allow"), f"backend {backend} KO ({e})"
        if ok:
            sig.detail["semantic"] = raison
            out.append(sig)
        else:
            log.info("[%s] 🧠 signal filtré (%s) : %s", watch["id"], sig.rule, raison)
    return out
