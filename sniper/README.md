# Veille Sniper — surveillance continue + détection ultra-rapide ⚡

> Polling « hot » sur endpoints API (15-30 s) + **webhooks entrants < 1 s** + alertes Telegram à boutons + fan-out Apprise + stockage vers l'API veille.

## Démarrage en 3 minutes (démo sans réseau)

```bash
cd sniper
pip install -r requirements.txt
cp config/watches.example.yaml config/watches.yaml

# 1. Un seul passage sur la cible démo (aucun réseau requis)
python -m sniper.runner --config config/watches.yaml --once --watch demo-riz-mokolo

# 2. Boucle continue (Ctrl+C pour arrêter)
python -m sniper.runner --config config/watches.yaml
```

Sans `TELEGRAM_BOT_TOKEN` configuré, l'alerter tourne en **dry-run** (log au lieu d'envoi) — parfait pour valider les règles.

## Activer les vraies alertes Telegram

1. Créez un bot via [@BotFather](https://t.me/BotFather) → récupérez le token.
2. Récupérez votre `chat_id` via [@userinfobot](https://t.me/userinfobot).
3. `cp .env.example .env` puis renseignez `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_IDS`.
4. `export $(cat .env | xargs)` (ou utilisez Docker Compose) puis relancez le runner.

## Chemin < 1 s : webhooks entrants (push)

```bash
# Terminal 1 : serveur de webhooks
API_KEY_INGEST=xxx uvicorn sniper.webhook_server:app --host 0.0.0.0 --port 8001

# Terminal 2 : simuler un push (rupture terrain, boutique partenaire…)
curl -X POST localhost:8001/hook/kobo-rupture-push \
  -H 'X-API-Key: xxx' -H 'Content-Type: application/json' \
  -d '{"text": "rupture riz parfumé signalée Mokolo allée 3"}'
# -> {"watch": ..., "alertes": [...], "latency_ms": 612}
```

C'est **ce chemin push** (et non le polling) qui tient la promesse « retard d'une seconde » : voir `docs/08-SNIPING-TEMPS-REEL.md` § budget de latence.

## Tester les règles sans attendre

```bash
pytest tests/ -q
```

## Règles disponibles

| Règle | Exemple | Usage |
|---|---|---|
| `drop_pct` | `{type: drop_pct, value: 10}` | baisse ≥ 10 % vs dernière valeur |
| `below` / `above` | `{type: below, value: 25000}` | seuil de prix (snipe d'achat) |
| `back_in_stock` | `{type: back_in_stock}` | retour en stock |
| `stock_changed` | `{type: stock_changed}` | tout changement de dispo |
| `keyword` | `{type: keyword, pattern: "iphone\|starlink"}` | mot-clé / nouveau produit |
| `new_items` | `{type: new_items}` | nouveaux items d'une liste JSON |
| `changed` | `{type: changed}` | contenu modifié (hash) |

Options par règle : `severity: rouge|jaune|vert`, `cooldown: 600` (secondes).

## Extraction supportée (`extract:`)

- `price_jsonpath` / `stock_jsonpath` / `items_jsonpath` + `items_id_key` (API JSON)
- `price_regex` (ex. `'([\\d\\s.]+)\\s*(FCFA|XAF)'`), `price_css` (sélecteur, ex. `.prc`)
- `stock_present` / `stock_absent` (regex sur le HTML)

## Stack complète (Docker)

```bash
docker compose -f infra/docker-compose.sniper.yml up -d
# 5000 ChangeDetection.io · 5678 n8n · 8001 webhooks sniper · 8002 apprise-api
```

Détail architecture : [`docs/08-SNIPING-TEMPS-REEL.md`](../docs/08-SNIPING-TEMPS-REEL.md).
