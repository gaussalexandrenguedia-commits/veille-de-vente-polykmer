"""Parser d'annonces v2 : toutes villes CM+CEMAC, quartiers, lexique local.

Schéma : {produit, prix, devise, ville, quartier, nego, prix_ferme, phone,
          intention, etat, echange, alerte_fraude, caracteristiques,
          confiance, source}

Lexique réel du social-commerce camerounais : kolos (=1000 F), last price,
sous carton, troc, chap chap, feyman (arnaqueur), tchoko/do (cash), nkomo…
"""
from __future__ import annotations

import re
import unicodedata

# ── Villes : tout le Cameroun (10 régions) + capitales CEMAC ──
VILLES: dict[str, dict] = {
    "Douala": {"pays": "CM", "alias": ["douala", "dla"]},
    "Yaoundé": {"pays": "CM", "alias": ["yaounde", "yde"]},
    "Bafoussam": {"pays": "CM", "alias": ["bafoussam", "baf"]},
    "Bamenda": {"pays": "CM", "alias": ["bamenda", "bda"]},
    "Garoua": {"pays": "CM", "alias": ["garoua"]},
    "Maroua": {"pays": "CM", "alias": ["maroua"]},
    "Ngaoundéré": {"pays": "CM", "alias": ["ngaoundere", "ndere"]},
    "Bertoua": {"pays": "CM", "alias": ["bertoua"]},
    "Ebolowa": {"pays": "CM", "alias": ["ebolowa"]},
    "Kribi": {"pays": "CM", "alias": ["kribi", "krb"]},
    "Limbé": {"pays": "CM", "alias": ["limbe"]},
    "Buéa": {"pays": "CM", "alias": ["buea"]},
    "Kumba": {"pays": "CM", "alias": ["kumba"]},
    "Tiko": {"pays": "CM", "alias": ["tiko"]},
    "Nkongsamba": {"pays": "CM", "alias": ["nkongsamba", "nkong"]},
    "Edéa": {"pays": "CM", "alias": ["edea"]},
    "Mbalmayo": {"pays": "CM", "alias": ["mbalmayo"]},
    "Sangmélima": {"pays": "CM", "alias": ["sangmelima"]},
    "Dschang": {"pays": "CM", "alias": ["dschang"]},
    "Foumban": {"pays": "CM", "alias": ["foumban"]},
    "Mbouda": {"pays": "CM", "alias": ["mbouda"]},
    "Bafang": {"pays": "CM", "alias": ["bafang"]},
    "Kousséri": {"pays": "CM", "alias": ["kousseri"]},
    "Brazzaville": {"pays": "CG", "alias": ["brazzaville", "brazza"]},
    "Pointe-Noire": {"pays": "CG", "alias": ["pointe-noire", "pointe noire", "pnr"]},
    "Libreville": {"pays": "GA", "alias": ["libreville", "lbv"]},
    "Port-Gentil": {"pays": "GA", "alias": ["port-gentil", "pog"]},
    "N'Djamena": {"pays": "TD", "alias": ["ndjamena", "n'djamena", "ndjam"]},
    "Moundou": {"pays": "TD", "alias": ["moundou"]},
    "Bangui": {"pays": "CF", "alias": ["bangui"]},
    "Malabo": {"pays": "GQ", "alias": ["malabo"]},
    "Bata": {"pays": "GQ", "alias": ["bata"]},
}

# ── Quartiers → ville (annonces « dispo à Akwa », « Nkomo », « PK12 ») ──
QUARTIERS: dict[str, list[str]] = {
    "Douala": ["akwa", "deido", "bonanjo", "bonapriso", "bepanda", "logpom",
               "kotto", "ndogbong", "makepe", "bali", "new bell", "cité sic",
               "sodiko", "bekoko"],
    "Yaoundé": ["mokolo", "mvog-mbi", "nkomo", "nkolbisson", "mendong", "odza",
                "biyem-assi", "etoudi", "mvan", "mimboman", "nlongkak",
                "tongolo", "messassi", "simbock", "ahala", "olembe",
                "nkolmesseng", "ekounou", "essos", "emana", "mballa"],
    "Bafoussam": ["tamdja", "marché a", "djeleng", "banengo"],
    "Bamenda": ["commercial avenue", "nkwen", "bamendankwe"],
    "Kribi": ["grand batanga", "mpolongoue"],
}
PK_RE = re.compile(r"\bpk\s?(\d{1,2})\b", re.I)  # PK8, PK12… = axe Douala

# ── Prix : 350k / 1.2M / 175 kolos / 32 500 FCFA ──
PRIX_K_RE = re.compile(r"(\d[\d\s.,]*)\s*([kKmM])\b(?!va\b)", re.I)
KOLO_RE = re.compile(r"(\d[\d\s.,]*)\s*kolos?\b", re.I)
PRIX_RE = re.compile(r"(\d[\d\s.,]*)\s*(fcfa|xaf|f\s?cfa|frs?|f)\b", re.I)
PHONE_RE = re.compile(r"(\+237[\s.\-\d]{8,14}|\b6\d{2}[\s.\-]?\d{2}[\s.\-]?\d{2}[\s.\-]?\d{2}\b)")

# ── Négociation / prix ferme ──
NEGO_RE = re.compile(r"nego|n[eé]gociable|discutable|d[eé]battre|on g[eè]re|"
                     r"on s.entend|a debattre", re.I)
LASTPRICE_RE = re.compile(r"last\s?price|prix ferme|non n[eé]gociable", re.I)

# ── Intentions ──
SPAM_RE = re.compile(r"gagner|argent facile|clique|investis|forex|1xbet|paris sportifs|"
                     r"marabout|retour d.affection|pr[eê]t|cr[eé]dit|millionnaire|giveaway", re.I)
ACHAT_RE = re.compile(r"je cherche|je recherche|recherc?he|qui a|qui vend|besoin de|"
                      r"je veux acheter|o[uù] trouver|o[uù] avoir|na who get", re.I)
VENTE_RE = re.compile(r"\bvs\b|je vends?|a vendre|à vendre|en vente|dispo|disponible|"
                      r"en stock|solde|promo|liquidation|deals?\b", re.I)

# ── Lexique local ──
NEUF_RE = re.compile(r"\bneuf\b|\bneuve\b|nouveau|sous carton|scell[eé]|brand new", re.I)
OCCAS_RE = re.compile(r"2e main|deuxi[eè]me main|occasion|fripe|friperie|tokumbo", re.I)
ECHANGE_RE = re.compile(r"\btroc\b|[eé]change possible|[eé]change accept", re.I)
URGENCE_RE = re.compile(r"urgent|vite|aujourd.hui|chap chap|\bchap\b|rapide", re.I)
CASH_RE = re.compile(r"\bcash\b|liquide|esp[eè]ces|tchoko|paiement direct", re.I)
FEY_RE = re.compile(r"feyman|\bfey\b|mougou|arnaque|escroc|voleur", re.I)

STOP = {"vs", "vends", "vend", "vendre", "je", "a", "à", "le", "la", "les", "de",
        "des", "en", "bon", "bonne", "tres", "très", "propre", "neuf", "neuve",
        "nouveau", "kmer", "cameroun", "camer", "dla", "yde", "nego", "negociable",
        "négociable", "prix", "livraison", "rapide", "serie", "sérieux",
        "cash", "ville", "disponible", "dispo", "urgent", "troc", "carton"}


def _sans_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _nombre(s: str) -> float | None:
    s = re.sub(r"[\s\u00a0]", "", s).replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _ville_quartier(texte: str) -> tuple[str | None, str | None]:
    t = _sans_accents(texte)
    for ville, quartiers in QUARTIERS.items():
        for q in quartiers:
            if re.search(rf"\b{re.escape(_sans_accents(q))}\b", t):
                return ville, q
    m = PK_RE.search(texte)
    if m:
        return "Douala", f"PK{m.group(1)}"
    for ville, d in VILLES.items():
        if any(re.search(rf"\b{re.escape(a)}\b", t) for a in d["alias"]):
            return ville, None
    return None, None


def _prix(texte: str) -> float | None:
    m = PRIX_K_RE.search(texte)
    if m and (v := _nombre(m.group(1))):
        return v * (1000 if m.group(2).lower() == "k" else 1_000_000)
    m = KOLO_RE.search(texte)
    if m and (v := _nombre(m.group(1))):
        return v * 1000
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
    for rx in (PRIX_K_RE, KOLO_RE, PRIX_RE, PHONE_RE, NEGO_RE):
        reste = rx.sub(" ", reste)
    for d in VILLES.values():
        for a in d["alias"]:
            reste = re.sub(rf"\b{re.escape(a)}\b", " ", reste, flags=re.I)
    mots = [w for w in re.findall(r"[A-Za-zÀ-ÿ0-9+.'-]{2,}", reste)
            if _sans_accents(w) not in STOP
            and (not w.isdigit() or len(w) <= 3)]
    return " ".join(mots[:8]).strip(" ,.-") or None


def parse_heuristic(texte: str) -> dict:
    prix, phone = _prix(texte), _phone(texte)
    ville, quartier = _ville_quartier(texte)
    intention = _intention(texte)
    prix_ferme = bool(LASTPRICE_RE.search(_sans_accents(texte)))
    nego = bool(NEGO_RE.search(_sans_accents(texte))) and not prix_ferme
    etat = "neuf" if NEUF_RE.search(texte) else ("seconde_main" if OCCAS_RE.search(texte) else None)
    carac: list[str] = []
    if URGENCE_RE.search(_sans_accents(texte)):
        carac.append("urgent")
    if CASH_RE.search(_sans_accents(texte)):
        carac.append("paiement cash")
    if prix_ferme:
        carac.append("prix ferme")
    confiance = 0.4 + (0.15 if prix else 0) + (0.15 if phone else 0) \
        + (0.1 if ville else 0) + (0.1 if intention in ("vente", "achat") else 0)
    return {"produit": _produit(texte), "prix": prix,
            "devise": "XAF" if prix else None, "ville": ville,
            "quartier": quartier, "nego": nego, "prix_ferme": prix_ferme,
            "phone": phone, "intention": intention, "etat": etat,
            "echange": bool(ECHANGE_RE.search(_sans_accents(texte))),
            "alerte_fraude": bool(FEY_RE.search(_sans_accents(texte))),
            "caracteristiques": carac,
            "confiance": round(min(confiance, 0.9), 2), "source": "heuristique"}


SYSTEM_PARSE = ("Tu es un parseur d'annonces camerounaises et centrafricaines "
                "(français, pidgin, camfranglais : vs=vends, kmer=Cameroun, "
                "dla=Douala, yde=Yaoundé, 350k=350000, kolos=×1000, last "
                "price=prix ferme, sous carton=neuf, troc=échange, "
                "chap chap=urgent, feyman=arnaqueur). Réponds UNIQUEMENT en JSON.")

PROMPT_PARSE = """Parse cette annonce en JSON : {"produit": str|null, "prix": number|null,
"devise": "XAF"|null, "ville": str|null (nom complet : Douala, Yaoundé, Bafoussam,
Bamenda, Garoua, Maroua, Kribi, Brazzaville, Libreville, N'Djamena, Bangui…),
"quartier": str|null (Akwa, Mokolo, Nkomo, PK12…), "nego": bool,
"prix_ferme": bool, "phone": str|null (9 chiffres), "intention": "vente"|"achat"|"spam"|"autre",
"etat": "neuf"|"seconde_main"|null, "echange": bool, "alerte_fraude": bool,
"caracteristiques": [str], "confiance": 0..1}

Exemples :
- "Vs iphone 13 propre 350k kmer négo à dla 699123456" ->
  {"produit": "iPhone 13", "prix": 350000, "devise": "XAF", "ville": "Douala",
   "quartier": null, "nego": true, "prix_ferme": false, "phone": "699123456",
   "intention": "vente", "etat": null, "echange": false, "alerte_fraude": false,
   "caracteristiques": ["bon état"], "confiance": 0.95}
- "Congélateur Hisense 200L sous carton 175 kolos Akwa last price 690112233" ->
  {"produit": "Congélateur Hisense 200 L", "prix": 175000, "devise": "XAF",
   "ville": "Douala", "quartier": "akwa", "nego": false, "prix_ferme": true,
   "phone": "690112233", "intention": "vente", "etat": "neuf",
   "echange": false, "alerte_fraude": false,
   "caracteristiques": ["prix ferme"], "confiance": 0.93}
- "Je cherche groupe électrogène 5kva Yaoundé urgent, troc possible" ->
  {"produit": "groupe électrogène 5 kVA", "prix": null, "devise": null,
   "ville": "Yaoundé", "quartier": null, "nego": false, "prix_ferme": false,
   "phone": null, "intention": "achat", "etat": null, "echange": true,
   "alerte_fraude": false, "caracteristiques": ["urgent"], "confiance": 0.9}
- "Attention feyman au marché Mokolo, il prend le momo et disparaît" ->
  {"produit": null, "prix": null, "devise": null, "ville": "Yaoundé",
   "quartier": "mokolo", "nego": false, "prix_ferme": false, "phone": null,
   "intention": "autre", "etat": null, "echange": false, "alerte_fraude": true,
   "caracteristiques": ["signalement fraude"], "confiance": 0.85}

Annonce : """


def normalize_ai_result(data: dict, texte: str) -> dict:
    """Valide/normalise la sortie Gemini (garde-fous anti-hallucination)."""
    h = parse_heuristic(texte)  # replis
    out = {"produit": data.get("produit") or h["produit"],
           "prix": data.get("prix"), "devise": data.get("devise"),
           "ville": data.get("ville") or h["ville"],
           "quartier": data.get("quartier") or h["quartier"],
           "nego": bool(data.get("nego")),
           "prix_ferme": bool(data.get("prix_ferme")),
           "phone": data.get("phone"),
           "intention": data.get("intention", "autre"),
           "etat": data.get("etat") or h["etat"],
           "echange": bool(data.get("echange")),
           "alerte_fraude": bool(data.get("alerte_fraude")) or h["alerte_fraude"],
           "caracteristiques": data.get("caracteristiques") or h["caracteristiques"],
           "confiance": data.get("confiance", 0.7), "source": "gemini"}
    if not isinstance(out["prix"], (int, float)) or not (0 < out["prix"] < 1e9):
        out["prix"], out["devise"] = h["prix"], ("XAF" if h["prix"] else None)
    if out["phone"]:
        digits = re.sub(r"\D", "", str(out["phone"]))
        out["phone"] = digits[-9:] if len(digits) >= 9 else None
    if out["intention"] not in ("vente", "achat", "spam", "autre"):
        out["intention"] = h["intention"]
    if out["etat"] not in ("neuf", "seconde_main", None):
        out["etat"] = h["etat"]
    return out
