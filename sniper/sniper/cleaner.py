"""Nettoyage HTML -> texte structuré compact (inspiré Firecrawl / Jina Reader).

Objectif : -90 % de volume avant stockage / règles / filtre sémantique.
Supprime scripts, styles, pubs, navigation ; conserve le contenu utile
avec un minimum de structure markdown (titres, listes).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment

DROP_TAGS = ("script", "style", "noscript", "svg", "header", "footer",
             "nav", "aside", "form", "iframe", "canvas", "select")


def clean_html_to_text(html: str, max_chars: int = 20000) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(DROP_TAGS):
        tag.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for h in soup.find_all(["h1", "h2", "h3"]):
        h.insert_before("\n## ")
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    text = soup.get_text("\n")
    lines: list[str] = []
    for ln in text.splitlines():
        ln = re.sub(r"[ \t\u00a0]+", " ", ln).strip()
        if ln:
            lines.append(ln)
    dedup = [l for i, l in enumerate(lines) if i == 0 or l != lines[i - 1]]
    return "\n".join(dedup)[:max_chars]


def compression_ratio(html: str, max_chars: int = 20000) -> float:
    """Part conservée après nettoyage (ex. 0.08 = -92 %). Debug/monitoring."""
    if not html:
        return 0.0
    return round(len(clean_html_to_text(html, max_chars)) / len(html), 4)
