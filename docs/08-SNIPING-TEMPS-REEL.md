# 08 — Surveillance continue & sniping ultra-rapide ⚡

> Objectif : détecter **baisses de prix, nouveaux posts, changements de stock** et alerter en quelques secondes. Le pipeline **signal → notification Telegram tient < 1 s** ; la détection elle-même dépend du mode (push instantané vs polling).

## 1. Architecture

```
                    ┌──────────────────────────────┐
                    │  POUSSEURS (< 1 s, push)      │
                    │  boutique partenaire, Kobo,   │
                    │  ChangeDetection.io, n8n      │
                    └──────────────┬───────────────┘
                                   │ POST /hook/{id}
                                   ▼
┌──────────────┐   ┌──────────────────────────────┐   ┌─────────────────┐
│ TIER HOT     │   │  SNIPER (sniper/)            │   │ ALERTES         │
│ polling API  │──▶│  fetch httpx → observe →     │──▶│ Telegram bot    │
│ 15-30 s      │   │  règles → dédup+cooldown ────│──▶│ Apprise (80+ cx)│
├──────────────┤   └──────────────────────────────┘   └─────────────────┘
│ TIER WARM    │              │ post_api                    │
│ HTML 5 min   │              ▼                             │
├──────────────┤   ┌──────────────────────┐    ┌────────────────────────┐
│ TIER COLD    │   │ API veille (8000)    │    │ n8n (5678)             │
│ ChangeDet.io │   │ /ingest/scraper      │◀──▶│ logique métier, Sheets │
│ heures       │   └──────────────────────┘    └────────────────────────┘
└──────────────┘
```

| Composant | Rôle | Port |
|---|---|---|
| `sniper` (runner) | polling hot/warm, règles, dédup, alertes directes | — |
| `sniper-webhooks` | webhooks entrants = chemin < 1 s | 8001 |
| ChangeDetection.io | veille large visuelle/structurelle + rendu JS/Playwright | 5000 |
| n8n | orchestration : seuils métier, escalade, Sheets, enrichissement | 5678 |
| apprise-api | fan-out HTTP vers 80+ services | 8002 |

Lancement : `docker compose -f infra/docker-compose.sniper.yml up -d`

## 2. Budget de latence — être honnête sur « 1 seconde »

| Chemin | Latence typique | Commentaire |
|---|---|---|
| **Webhook entrant → Telegram** | **300-900 ms** ✅ | le vrai « temps réel » : push, pas de polling |
| Poll API hot (30 s) → détection | 0-30 s + ~1 s pipeline | détection au pire = intervalle ; pipeline < 1 s après fetch |
| Page HTML warm (5 min) | 0-5 min + ~2 s | polling poli obligatoire |
| ChangeDetection.io | minutes-heures | veille large, pas du snipe |
| n8n (enrichissement) | +0,5-2 s | après réception du signal |

**Règle d'or** : on ne poll **jamais** un site tiers à 1 req/s (ban IP + violation CGU en quelques minutes). Le < 1 s de bout en bout s'obtient par :
1. **Webhooks** des sources qu'on contrôle ou partenaires (boutique, Kobo, canaux Telegram admin) ;
2. Polling hot (15-30 s) **réservé aux endpoints API tolérants/partenaires** ;
3. ChangeDetection.io + n8n pour la couverture large (minutes) en complément.

Le sniper embarque des garde-fous : `min_interval_per_domain: 15 s`, requêtes conditionnelles (ETag/304), jitter, backoff exponentiel, pause auto sur 429/403.

## 3. Configuration des cibles (`sniper/config/watches.yaml`)

Voir le fichier d'exemple commenté. Champs clés par watch :

```yaml
- id: jumia-congelateur        # unique, utilisé dans /hook/{id}
  tier: warm                   # hot | warm | cold
  interval: 300                # secondes ; 0 = webhook uniquement
  type: api_json | html | demo | webhook
  url: https://…
  extract: {price_jsonpath, stock_jsonpath, items_jsonpath, price_regex, price_css, …}
  rules: [{type: drop_pct, value: 10}, {type: back_in_stock}, …]
  actions: {telegram: true, apprise: true, post_api: true}
```

Règles : `drop_pct`, `below`, `above`, `back_in_stock`, `stock_changed`, `keyword`, `new_items`, `changed` — chacune avec `severity` et `cooldown` optionnels.

## 4. Alertes Telegram (couche action)

Message formaté + boutons inline :
- 🔗 **Voir l'offre** (URL directe → action immédiate = le « snipe »)
- 📊 **Dashboard** (contexte)

Dédup 24 h + cooldown 5 min par règle par défaut : pas de spam, chaque notification est actionnable.

Fan-out : `APPRISE_URLS` (`discord://…;slack://…;signal://…`) ou via le conteneur apprise-api depuis n8n.

## 5. Raccordements recommandés (Yaoundé/Douala d'abord)

1. **Semaine 1** : cible `demo` + 2-3 pages warm (Jumia/CoinAfrique) + bot Telegram → valider les règles.
2. **Semaine 2** : ChangeDetection.io sur 20-50 URLs (sélecteurs prix) → webhook n8n → tri ≥ 20 % → Telegram 🔴.
3. **Semaine 3** : convaincre 2-3 boutiques partenaires d'appeler `/hook/{id}` (vrai push < 1 s) ; brancher `post_api` → l'API veille historise tout.
4. **Ensuite** : canaux Telegram d'arrivages (admin accord) → `new_items` + `keyword` (ex. `starlink|iphone`).

## 6. Limites assumées & éthique

- Pas de contournement agressif (ni CAPTCHA-solving, ni rotation de proxies furtive) : si un site bloque, on passe en **collecte semi-manuelle ou partenariat**.
- `User-Agent` identifié, débit ≤ 1 req / 15 s / domaine, respect de `robots.txt`.
- Les webhooks entrants sont protégés par `X-API-Key`.
- Données vendeurs : hachage, comme le reste de la plateforme (cf. `docs/06-DEFIS-CEMAC.md`).

## 7. Dépannage express

| Symptôme | Cause probable | Action |
|---|---|---|
| `[dry-run] TELEGRAM` dans les logs | token/chat_id absents | renseigner `sniper/.env` |
| HTTP 429/403 répétés | polling trop agressif | augmenter `interval`, passer en webhook |
| Doublons d'alertes | `dedup_ttl` trop court | monter à 86400, vérifier `dedup_sig` |
| Latence webhook > 2 s | réseau / Telegram lent | vérifier `latency_ms` retourné par `/hook` |
| n8n : webhook 404 | workflow inactif | passer le workflow en **Active** |
