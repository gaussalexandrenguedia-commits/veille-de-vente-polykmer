# Workflows n8n — orchestration des alertes

## Import

1. Ouvrir n8n : http://localhost:5678 (voir `infra/docker-compose.sniper.yml`)
2. **Workflows → Import from file** → choisir `workflows/veille-sniper.json`
3. Configurer les credentials :
   - **Telegram** : bot token (@BotFather) + chat ID
   - **Google Sheets** (optionnel) : OAuth2 + ID du classeur
   - **API veille** : Header Auth `X-API-Key: <API_KEY_INGEST>` (nœud HTTP déjà paramétré, mettre à jour host/clé)
4. Activer le workflow (**Active**). Copier l'URL du webhook.

## Raccorder les détecteurs au webhook n8n

- **Sniper** : dans `watches.yaml`, ajoutez une action webhook… ou laissez le sniper alerter Telegram en direct (plus rapide) et n8n gérer l'enrichissement (Sheets, escalade).
- **ChangeDetection.io** : Edit → Notifications → webhook `http://n8n:5678/webhook/veille-sniper` avec le JSON du changement.
- **API veille** : un cron `POST /api/v1/kpi/alertes/generer` peut pousser vers n8n (nœud Webhook en entrée).

## Logique du workflow `veille-sniper`

```
Webhook entrée ─▶ Code (normalise + calcule drop_pct)
                    ─▶ IF baisse ≥ 20 % ──OUI──▶ Telegram URGENT 🔴
                    │                            + Google Sheets (log)
                    │                            + API veille (stockage offre)
                    └──NON──▶ IF rupture/mot-clé ? ──▶ Telegram info 🟡
```

Le nœud **Code** attend ce JSON (celui qu'envoie le sniper / ChangeDetection) :

```json
{
  "watch_id": "jumia-congelateur",
  "title": "Baisse -12.5%",
  "rule": "drop_pct",
  "severity": "jaune",
  "prix": 175000,
  "prix_avant": 200000,
  "drop_pct": 12.5,
  "url": "https://www.jumia.cm/...",
  "ville": "Douala"
}
```
