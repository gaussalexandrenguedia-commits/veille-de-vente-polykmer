"""Parser d'annonces informelles : heuristique offline + prompt Gemini.

Schéma commun : {produit, prix, devise, ville, nego, phone, intention,
                 caracteristiques, confiance, source}
"""
from __future__ import annotations

import re
import unicodedata

VILLES = {
    "Douala": ["douala", "dla"], "Yaoundé": ["yaounde", "yde", "mvan"],
    "Bafoussam": ["bafoussam", "baf"], "Garoua": ["garoua"],
    "Kribi": ["kribi", "krb"], "Bamenda": ["bamenda", "bda"],
    "Limbe": ["limbe"], "Ngaoundéré": ["ngaoundere"],
    "Maroua": ["maroua"], "Bertoua": ["bertoua"], "Ebolowa": ["ebolowa"],
}
PRIX_K_RE = re.compile(r"(\d[\d\s.,]*)\s*([kKmM])\b(?!va\b)", re.I)  # 350k, 1.2M (pas 5kVA !)
PRIX_RE = re.compile(r"(\d[\d\s.,]*)\s*(fcfa|xaf|f\s?cfa|frs?|f)\b", re.I)
PHONE_RE = re.compile(r"(\+237[\s.\-\d]{8,14}|\b6\d{2}[\s.\-]?\d{2}[\s.\-]?\d{2}[\s.\-]?\d{2}\b)")
NEGO_RE = re.compile(r"nego|n[eé]gociable|discutable|d[eé]battre|last\s?price", re.I)
SPAM_RE = re.compile(r"gagner|argent facile|clique|investis|forex|1xbet|paris sportifs|"
                     r"marabout|retour d.affection|pr[eê]t|cr[eé]dit|millionnaire|giveaway", re.I)
ACHAT_RE = re.compile(r"je cherche|je recherche|recherc?he|qui a|qui vend|besoin de|"
                      r"je veux acheter|o[uù] trouver|o[uù] avoir", re.I)
VENTE_RE = re.compile(r"\bvs\b|je vends?|a vendre|à vendre|en vente|dispo|disponible|"
                      r"en stock|solde|promo|liquidation", re.I)
STOP = {"vs", "vends", "vend", "vendre", "je", "a", "à", "le", "la", "les", "de", "des",
        "en", "bon", "bonne", "tres", "très", "propre", "neuf", "neuve", "kmer",
        "cameroun", "camer", "dla", "yde", "nego", "negociable", "négociable",
        "prix", "livraison", "rapide", "serie", "sérieux", "cash", "ville"}


def _sans_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _ville(texte: str) -> str | None:
    t = _sans_accents(texte)
    for ville, alias in VILLES.items():
        if any(re.search(rf"\b{a}\b", t) for a in alias):
            return ville
    return None


def _prix(texte: str) -> float | None:
    m = PRIX_K_RE.search(texte)
    if m:
        val = float(re.sub(r"[^\d.]", "", m.group(1).replace(",", ".")) or 0)
        return val * (1000 if m.group(2).lower() == "k" else 1_000_000) or None
    m = PRIX_RE.search(texte)
    if m:
        chiffres = re.sub(r"[^\d]", "", m.group(1))
        return float(chiffres) if chiffres else None
    return None


def _phone(texte: str) -> str | None:
    m = PHONE_RE.search(texte)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    if len(digits) == 9 and digits.startswith("6"):
        return digits
    if len(digits) == 12 and digits.startswith("237"):
        return digits[3:]
    return None


def _intention(texte: str) -> str:
    t = texte.lower()
    if SPAM_RE.search(t):
        return "spam"
    if ACHAT_RE.search(t):
        return "achat"
    if VENTE_RE.search(t):
        return "vente"
    return "autre"


def _produit(texte: str) -> str | None:
    reste = texte
    for rx in (PRIX_K_RE, PRIX_RE, PHONE_RE, NEGO_RE):
        reste = rx.sub(" ", reste)
    for alias in [a for aliases in VILLES.values() for a in aliases]:
        reste = re.sub(rf"\b{alias}\b", " ", reste, flags=re.I)
    mots = [w for w in re.findall(r"[A-Za-zÀ-ÿ0-9+.'-]{2,}", reste)
            if _sans_accents(w) not in STOP
            and (not w.isdigit() or len(w) <= 3)]
    return " ".join(mots[:8]).strip(" ,.-") or None


def parse_heuristic(texte: str) -> dict:
    prix, phone, ville = _prix(texte), _phone(texte), _ville(texte)
    intention = _intention(texte)
    confiance = 0.4 + (0.15 if prix else 0) + (0.15 if phone else 0) \
        + (0.1 if ville else 0) + (0.1 if intention in ("vente", "achat") else 0)
    return {"produit": _produit(texte), "prix": prix,
            "devise": "XAF" if prix else None, "ville": ville,
            "nego": bool(NEGO_RE.search(_sans_accents(texte))), "phone": phone,
            "intention": intention, "caracteristiques": [],
            "confiance": round(min(confiance, 0.9), 2), "source": "heuristique"}


SYSTEM_PARSE = ("Tu es un parseur d'annonces camerounaises informelles (français, "
                "pidgin, abréviations : vs=vends, kmer=Cameroun, dla=Douala, "
                "350k=350000 FCFA). Réponds UNIQUEMENT en JSON.")

PROMPT_PARSE = """Parse cette annonce en JSON : {"produit": str|null, "prix": number|null,
"devise": "XAF"|null, "ville": str|null (nom complet), "nego": bool,
"phone": str|null (9 chiffres, sans +237), "intention": "vente"|"achat"|"spam"|"autre",
"caracteristiques": [str], "confiance": 0..1}

Exemples :
- "Vs iphone 13 propre 350k kmer négo à dla 699123456" ->
  {"produit": "iPhone 13", "prix": 350000, "devise": "XAF", "ville": "Douala",
   "nego": true, "phone": "699123456", "intention": "vente",
   "caracteristiques": ["bon état"], "confiance": 0.95}
- "Je cherche groupe électrogène 5kva Yaoundé urgent" ->
  {"produit": "groupe électrogène 5 kVA", "prix": null, "devise": null,
   "ville": "Yaoundé", "nego": false, "phone": null, "intention": "achat",
   "caracteristiques": ["5 kVA", "urgent"], "confiance": 0.9}

Annonce : """


def normalize_ai_result(data: dict, texte: str) -> dict:
    """Valide/normalise la sortie Gemini (garde-fous anti-hallucination)."""
    out = {"produit": data.get("produit"), "prix": data.get("prix"),
           "devise": data.get("devise"), "ville": data.get("ville"),
           "nego": bool(data.get("nego")), "phone": data.get("phone"),
           "intention": data.get("intention", "autre"),
           "caracteristiques": data.get("caracteristiques") or [],
           "confiance": data.get("confiance", 0.7), "source": "gemini"}
    if not isinstance(out["prix"], (int, float)) or not (0 < out["prix"] < 1e9):
        out["prix"], out["devise"] = None, None
    if out["phone"]:
        digits = re.sub(r"\D", "", str(out["phone"]))
        out["phone"] = digits[-9:] if len(digits) >= 9 else None
    if out["intention"] not in ("vente", "achat", "spam", "autre"):
        out["intention"] = parse_heuristic(texte)["intention"]
    return out
