"""Scoring d'opportunités (pur, testable) : écart marché, score, fraude."""
from __future__ import annotations

import re

AVANCE_RE = re.compile(r"avance|envoyez|transf[eé]rez|frais de (dossier|livraison)|"
                       r"momo d.abord|moneygram|western union", re.I)


def verdict_ecart(ecart_pct: float) -> tuple[str, int]:
    """(verdict, score de base 0-100). Écart négatif = moins cher que le marché."""
    if ecart_pct <= -30:
        return "prioritaire", 95
    if ecart_pct <= -20:
        return "prioritaire", 85
    if ecart_pct <= -10:
        return "interessant", 70
    if ecart_pct <= 10:
        return "marche", 50
    if ecart_pct <= 25:
        return "cher", 30
    return "tres_cher", 15


def score_opportunite(ecart_pct: float, rupture_marche: bool = False,
                      promo: bool = False) -> int:
    _, base = verdict_ecart(ecart_pct)
    bonus = (10 if rupture_marche and ecart_pct < 5 else 0) + (5 if promo else 0)
    return max(0, min(100, base + bonus))


def flags_fraude(prix: float | None, mediane: float | None,
                 texte: str = "") -> list[str]:
    flags = []
    if prix and mediane and mediane > 0 and prix < mediane * 0.35:
        flags.append("prix_anormalement_bas")
    if texte and len(texte.strip()) < 25:
        flags.append("descriptif_sommaire")
    if texte and AVANCE_RE.search(texte):
        flags.append("demande_avance")
    return flags


PROMPT_FRAUDE = """Tu es détecteur de fraudes e-commerce au Cameroun.
Annonce : {texte}
Prix : {prix} XAF | Médiane marché : {mediane} XAF ({ecart:+.0f}%) | Ville : {ville}
Indices classiques : prix dérisoire, demande d'avance Mobile Money, descriptif
générique, urgence artificielle.
Réponds UNIQUEMENT en JSON : {{"suspect": bool, "raisons": [max 3, francais court]}}"""
