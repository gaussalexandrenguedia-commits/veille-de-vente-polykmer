"""Sélecteurs auto-réparables + ciblage par zones (inspirés Stagehand/Scrapling/Visualping).

Stratégie en cascade pour le prix :
  1. chaîne CSS configurée (price_css_chain) — chaque essai est journalisé ;
  2. regex configurée (price_regex) ;
  3. repli sémantique : tous les candidats « prix » du texte, scorés par
     proximité aux mots-clés (prix, total, FCFA…) — survit aux refontes HTML.

Ciblage par zones : zone_css_chain restreint l'observation au bloc prix/stock,
ce qui élimine l'essentiel des fausses alertes (pubs, dates, compteurs).
"""
from __future__ import annotations

import logging
import re
from collections.abc import Callable

from bs4 import BeautifulSoup

from .extractors import parse_prix_xaf

log = logging.getLogger("sniper.healer")

PRICE_UNIT_RE = re.compile(r"(\d[\d\s\u00a0\u202f.,]*)\s*(FCFA|XAF|F\s?CFA)", re.I)
NUMBER_RE = re.compile(r"\d[\d\s\u00a0\u202f.,]{1,}")
KEYWORDS = ("prix", "price", "total", "montant", "amount", "tarif",
            "cout", "coût", "payer", "payez", "promotion", "promo")


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def select_first(soup: BeautifulSoup, selectors: list[str] | None,
                 stats_cb: Callable[[str, bool], None] | None = None
                 ) -> tuple[str | None, str | None]:
    """Essaie chaque sélecteur ; retourne (sélecteur_utilisé, texte)."""
    for sel in selectors or []:
        try:
            el = soup.select_one(sel)
        except Exception:  # sélecteur invalide -> on passe au suivant
            if stats_cb:
                stats_cb(sel, False)
            continue
        if el and (txt := el.get_text(" ", strip=True)):
            if stats_cb:
                stats_cb(sel, True)
            return sel, txt
        if stats_cb:
            stats_cb(sel, False)
    return None, None


def extract_zone(soup: BeautifulSoup, selectors: list[str] | None,
                 stats_cb: Callable[[str, bool], None] | None = None
                 ) -> tuple[str | None, str | None]:
    """Extrait le bloc HTML de la zone surveillée (ou (None, None))."""
    for sel in selectors or []:
        try:
            el = soup.select_one(sel)
        except Exception:
            if stats_cb:
                stats_cb(f"zone:{sel}", False)
            continue
        if el is not None:
            if stats_cb:
                stats_cb(f"zone:{sel}", True)
            return sel, str(el)
        if stats_cb:
            stats_cb(f"zone:{sel}", False)
    return None, None


def find_price_candidates(text: str) -> list[tuple[float, str, int]]:
    """Tous les candidats prix + contexte + score (triés, meilleur d'abord)."""
    if not text:
        return []
    low = text.lower()
    cands: list[tuple[float, str, int]] = []
    vus: set[float] = set()

    def window(m: re.Match) -> str:
        return low[max(0, m.start() - 60):m.end() + 20]

    # 1) montants avec unité FCFA/XAF : signal fort
    for m in PRICE_UNIT_RE.finditer(text):
        val = parse_prix_xaf(m.group(0))
        if val is None or val in vus:
            continue
        vus.add(val)
        score = 3
        ctx = window(m)
        if any(k in ctx for k in KEYWORDS):
            score += 2
        cands.append((val, m.group(0).strip(), score))

    # 2) nombres nus proches d'un mot-clé prix
    for m in NUMBER_RE.finditer(text):
        brut = re.sub(r"[^\d]", "", m.group(0))
        if len(brut) < 3 or len(brut) > 9:
            continue
        val = float(brut)
        if val in vus:
            continue
        ctx = window(m)
        if any(k in ctx for k in KEYWORDS):
            vus.add(val)
            score = 2
            if 100 <= val <= 50_000_000:
                score += 1
            if len(brut) == 4 and 1900 <= val <= 2100:  # année probable
                score -= 2
            cands.append((val, m.group(0).strip(), score))

    cands.sort(key=lambda c: (-c[2], text.find(c[1])))
    return cands


def best_price(text: str) -> float | None:
    """Repli sémantique : meilleur candidat prix du texte (ou None)."""
    cands = find_price_candidates(text)
    if cands:
        log.info("🩹 repli sémantique prix : %s (score %d, ctx %r)",
                 cands[0][0], cands[0][2], cands[0][1][:60])
    return cands[0][0] if cands else None
