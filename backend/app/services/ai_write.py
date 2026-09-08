"""Génération : messages vendeur WhatsApp + rapport quotidien (templates + prompts)."""
from __future__ import annotations

import re
from urllib.parse import quote


def _f(n: float) -> str:
    return f"{n:,.0f}".replace(",", " ")


def message_template(produit: str, prix: float, ville: str,
                     prix_propose: float | None = None) -> str:
    base = (f"Bonjour, votre {produit} à {_f(prix)} XAF sur {ville} "
            f"est-il toujours disponible ?")
    if prix_propose:
        base += (f" Je suis acheteur sérieux, paiement cash : possible à "
                 f"{_f(prix_propose)} XAF ?")
    else:
        base += " Je suis acheteur sérieux, paiement cash."
    return base


def wa_link(phone: str | None, message: str) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 9 and digits.startswith("6"):
        digits = "237" + digits
    if not (len(digits) == 12 and digits.startswith("237")):
        return None
    return f"https://wa.me/{digits}?text={quote(message)}"


PROMPT_MESSAGE = """Tu es un acheteur camerounais sérieux et courtois qui négocie sur WhatsApp.
Annonce : {produit} à {prix} XAF à {ville}.{propose}
Rédige UN court message (max 300 caractères, français simple, ton direct) pour
bloquer la vente en premier : confirmer la dispo + proposer cash.
Réponds UNIQUEMENT avec le message, sans guillemets."""


def rapport_template(kpis: dict) -> str:
    lignes = [f"# Rapport du {kpis.get('date', '')} — Veille Vente CM & CEMAC", ""]
    var = kpis.get("variations", [])
    lignes.append("## Variations marquantes (7 j)")
    lignes += [f"- **{v['produit']}** : {v['variation_pct']:+.1f}% ({v['mediane_actuelle']:,.0f} XAF)".replace(",", " ")
               for v in var[:5]] or ["- Aucune variation > 5%."]
    lignes += ["", "## Ruptures"]
    lignes += [f"- {r['produit']} : {r['taux']}%" for r in kpis.get("ruptures", [])[:5]] \
        or ["- Pas de rupture signalée."]
    lignes += ["", f"## Sentiment social (score {kpis.get('sentiment', 0):+d})"]
    lignes += [f"- {m['label']} : {m['n']}" for m in kpis.get("motifs", [])[:5]] \
        or ["- Volume faible."]
    return "\n".join(lignes)


PROMPT_RAPPORT = """Tu es analyste commercial au Cameroun. À partir de ces données brutes,
rédige un rapport quotidien concis en français (max 250 mots, markdown) :
3 sections (## Prix, ## Disponibilité, ## Perception clients), phrases courtes,
1 recommandation d'action à la fin.

Données :
Variations : {variations}
Ruptures : {ruptures}
Sentiment : score {sentiment}, motifs {motifs}
Promos par ville : {promos}"""
