# 09 — Sniping avancé : healing, zones, interception API, stealth, sémantique, one-click 🩹

> Mécanismes copiés des leaders (Stagehand, Visualping, Apify, Firecrawl, Phantombuster, ScrapeGraphAI…), adaptés au contexte Cameroun/CEMAC et aux garde-fous légaux du projet.

## 1. Détection : sélecteurs auto-réparables + zones DOM

**Problème** : `.product-price` change à chaque refonte → silencieux ou faux positifs.
**Solution** (`sniper/healer.py`) — cascade à 3 niveaux :

1. **Chaîne CSS** `price_css_chain: [".product-price", ".prc", ".price", "[data-price]"]` — chaque essai alimente `selector_stats` (SQLite) ; si le 1er échoue et le 2e marche → log `🩹 auto-réparé` + rapport sur `GET /selectors/{watch}` (:8001).
2. **Regex configurée** `price_regex` en repli.
3. **Repli sémantique** : tous les montants FCFA/XAF scorés par proximité aux mots-clés (prix, total, montant) ; les années (2019…) sont déclassées.

**Zones** (`zone_css_chain`) : l'observation (prix, stock, texte, hash `changed`) est restreinte au bloc produit → pubs, dates, compteurs ignorés. Test : `test_zone_elimine_fausses_alertes`.

```yaml
extract:
  zone_css_chain: [".listing-detail", ".annonce", "main"]
  price_css_chain: [".product-price", ".prc", ".price"]
  clean_html: true   # Firecrawl-like : -90 % de volume avant règles/LLM
```

## 2. Vitesse : interception API + HTML compact

**Pattern « record once, poll fast forever »** (`sniper/tools/record_xhr.py`) :

```bash
pip install playwright && playwright install chromium
python -m sniper.tools.record_xhr --url "https://www.jumia.cm/..." --out capture.json
# -> endpoints JSON détectés + jsonpaths prix/stock devinés + squelette watches.yaml
```

Le navigateur ne sert qu'**une fois** ; le polling passe ensuite en `httpx` pur sur l'endpoint interne (~50 ms vs ~3 s). Limitations honnêtes : endpoints signés/tokens éphémères = re-record périodique ou repli HTML.

**Nettoyage** (`sniper/cleaner.py`) : suppression scripts/styles/nav/pubs, texte markdown-ish compact → règles `keyword`, hash `changed` et filtre LLM travaillent sur l'utile.

## 3. Discrétion & sessions (anti-blocage raisonnable)

`sniper/stealth.py` — rotation de profils navigateur standards (desktop/mobile), proxies **fournis par vous** en round-robin, `impersonate: chrome124` via `curl_cffi` (optionnel, repli httpx automatique). Toujours combiné aux garde-fous : ≥ 15 s/domaine, ETag/304, jitter, backoff, pause sur 429/403.

`sniper/sessions.py` + `tools/save_session.py` — **vos** logins persistés :

```bash
python -m sniper.tools.save_session --domain facebook.com --out sessions/facebook.json
# -> login MANUEL dans le vrai navigateur, Entrée, cookies exportés (chmod 600)
```

Puis `session: sessions/facebook.json` dans la watch. Fichiers **jamais commités** (gitignore). Vos comptes uniquement, usage conforme aux CGU — pas de contournement CAPTCHA/proxy-furtif : si blocage → partenariat ou collecte manuelle.

## 4. Filtre sémantique (gate avant alerte)

`sniper/semantic.py` — bloc `semantic:` évalué **après les règles, avant dédup/cooldown** (un signal rejeté ne pollue pas l'historique) :

```yaml
semantic:
  backend: heuristic        # heuristic (offline) | ollama | openai_compatible
  applies_to: ["*"]         # ou ["drop_pct", "below", "new_item", ...]
  on_error: allow           # si le LLM est injoignable
  criteria:
    must_include: ["electrogene"]
    must_exclude: ["pièces détachées", "réparation", "location"]
    numeric: [{pattern: '([\\d.,]+)\\s*kva', op: ">=", value: 5}]
    max_price: 200000
  # ollama: {url: "http://localhost:11434", model: "llama3.1:8b"}
```

L'exemple « groupe électrogène > 5 kVA sous 200 000 FCFA » est couvert par les tests. Backend LLM : prompt strict, sortie JSON `{"match", "reason"}`, température 0, texte tronqué à ~1500 caractères (coût/latence maîtrisés).

## 5. Boutons one-click (action instantanée)

`actions_card:` dans la watch — carte Telegram avec **bouton WhatsApp vendeur pré-rempli** :

```yaml
actions_card:
  wa_text: "Bonjour, '{watch}' à {prix} XAF m'intéresse, toujours dispo ? ({ville})"
  buttons:
    - {label: "💬 WhatsApp vendeur", requires: seller_phone,
       url: "https://wa.me/{seller_phone_digits}?text={wa_text}"}
    - {label: "🔗 Voir l'annonce", url: "{url}"}
```

Le numéro vient de `extract.seller_phone_regex` (ex. `(\+237[\d\s]{9,})`) ; sans numéro, le bouton est **masqué** (jamais de lien cassé). Variables : `{url} {title} {prix} {ville} {seller_phone} {dashboard}` (+ `{wa_text}` auto-encodé). Bouton Dashboard ajouté par défaut. Même pattern réutilisable dans n8n : ``https://wa.me/{{ $json.tel_digits }}?text={{ encodeURIComponent(...) }}``.

## 6. Récapitulatif d'adoption (ordre conseillé)

1. `zone_css_chain` + `price_css_chain` sur vos 3 watches chaudes → chute immédiate des faux positifs ;
2. `record_xhr` sur Jumia/CoinAfrique → convertir 1-2 watches en `api_json` (hot 30 s) ;
3. `semantic.heuristic` sur les watches à fort bruit (petites annonces) ;
4. `actions_card` WhatsApp dès qu'un `seller_phone_regex` fiable est trouvé ;
5. `session:` + login manuel pour 1-2 groupes privés (vos comptes) ;
6. `impersonate`/`proxies` uniquement si 429/403 persistants **et** accord du site.

## 7. Limites assumées

- Le healing ne fait pas de magie : si le site supprime le prix du HTML (rendu JS obligatoire), il faut ChangeDetection+Playwright ou l'interception XHR.
- `curl_cffi` imite TLS/HTTP2 mais ne bat pas tous les WAF (Cloudflare Turnstile, Akamai sensor) — comportement attendu : backoff + alerte opérateur, pas d'escalade.
- Le LLM local ajoute 1-5 s par signal : réserver `ollama` aux signaux déjà filtrés par règles (c'est le design : gate après règles).
