# Collecte réelle + deals — runbook production

> Objectif : de vraies données (scrapers + terrain Kobo + annonces), de vrais deals
> scorés contre les médianes marché, et un suivi nouveau → contacté → conclu.
> Plus aucune démo : chaque source ci-dessous écrit en base et déclenche le pipeline.

## 1. Chaîne de données (tout est câblé)

```
Jumia / CoinAfrique ─┐
                     ├─▶ POST /ingest/scraper ─┐
Annonces terrain ────┘                          ├─▶ Relevé + ✅ deal auto si écart ≤ −10 %
Kobo (webhook) ─────▶ POST /ingest/kobo ───────┘
Texte WhatsApp ─────▶ POST /deals/depuis-texte ─▶ deal immédiat
Relevé manuel ──────▶ page /releves ─▶ médiane marché (référence des scores)
```

Stockage mutualisé : `services/collecte.py:stocker_offres()` — 1 offre =
1 `Releve` (prix marché, source) + 1 `Opportunite` si le prix bat la médiane
de la ville d'au moins `SEUIL_DEAL_PCT` (10 %).

## 2. Lancer une collecte

**Depuis le navigateur** (aucune clé requise) :

1. page **🎯 Deals**, section **🔎 Collecte réelle** → site (Jumia CM /
   CoinAfrique), recherche, ville + clé `API_KEY_INGEST` → **Lancer**.
   Le job tourne en fond ; offres / relevés / **deals détectés** s'affichent
   à la fin, et les nouveaux deals apparaissent en tête, statut `nouveau`.

**En ligne de commande** (machine avec internet) :

```bash
cd scrapers
python run_all.py --push --api-url https://VOTRE-SERVEUR --api-key $API_KEY_IMPORT
python jumia_cm.py --query "riz 50kg" --max-pages 2 --push --api-url … --api-key …
python coinafrique.py --query congelateur --ville douala --push --api-url … --api-key …
```

**En automatique (cron, heures WAT)** :

```cron
0 6,18 * * * cd /opt/veille-de-vente/scrapers && /opt/vv/bin/python run_all.py --push --api-url https://VOTRE-SERVEUR --api-key $API_KEY_IMPORT >> /var/log/vv-collecte.log 2>&1
```

## 3. Score d'un deal (transparent, vérifiable)

`services/deals.py:score_prix()` — référence = **médiane des relevés 30 j**
(produit × ville, repli : produit toutes villes) :

| écart vs médiane | verdict        | score |
|------------------|----------------|-------|
| ≤ −25 %          | 🟢 prioritaire | 90+   |
| ≤ −10 %          | 🔵 interessant | 70+   |
| > −10 %          | 🟠 à surveiller| 40+   |
| pas d'historique | ⚪ sans_ref    | —     |

Conseil : saisir d'abord quelques relevés manuels par ville (page Relevés)
pour calibrer les médianes — sans référence, les deals restent `sans_ref`.

## 4. Suivi commercial

Page **🎯 Deals** : filtres statut/verdict, **économie totale potentielle**,
boutons **J'appelle** (tel:), **WhatsApp** (message pré-rempli avec l'écart),
changement de statut en 1 clic : `nouveau → contacté → conclu` (+ `abandonné`).
API : `GET /deals`, `POST /deals`, `POST /deals/depuis-texte`, `PATCH /deals/{id}`.

## 5. Couverture géographique

32 villes (10 régions CM + CEMAC) dans `services/ai_parse.py:VILLES`,
exposées par `GET /api/v1/villes` (datalists Relevés / IA / Deals) :
Douala (+quartiers Akwa… + PKn), Yaoundé (+quartiers), Bafoussam, Bamenda,
Garoua, Maroua, Ngaoundéré, Bertoua, Ebolowa, Kribi, Limbé, Buéa, Kumba,
Sangmélima, Nkongsamba, Mbalmayo, Dschang, Foumban, Kumbo, Edéa, Eséka,
Ngaoundal… + Pointe-Noire, Douala, Libreville, Franceville, NDjamena,
Moundou, Bangui + alias (lbv, pnr, pk12, dla…).

## 6. Parser : langue réelle du terrain

`parse_heuristic` comprend : `kolos` (1 kolo = 1 000 XAF), `k`/`M`,
`last price`/`prix ferme`/`on gère`, `sous carton`/`troc`/`chap chap`,
`feyman`/`momo` → alerte fraude, téléphones CM 6XXXXXXXX, quartiers → ville.
Gemini reprend le même schéma quand la clé est configurée (`GEMINI_API_KEY`).

## 7. Prérequis production (checklist)

- [ ] Serveur avec internet (scrapers + Gemini + Telegram en ont besoin)
- [ ] `.env` : `DATABASE_URL` (Postgres), `API_KEY_IMPORT`, `GEMINI_API_KEY`,
      `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
- [ ] `alembic upgrade head` (migrations `infra/migrations/`)
- [ ] Cron collecte (6h/18h) + cron sniper (`sniper/run.py --once`)
- [ ] Webhook Kobo → `POST /api/v1/ingest/kobo?cle=...` (clé `API_KEY_IMPORT`)
- [ ] Relevés de calibration par ville (médianes fiables)

## 8. Fiabilité scrapers

Parsing isolé en fonctions pures (`parse_jumia_html`, `parse_coin_html`)
testées hors-ligne (`scrapers/tests/test_parse.py`, fixtures réalistes).
Si un site change son HTML : `pytest scrapers/tests` échoue et montre quoi
ajuster. Repli générique intégré si les sélecteurs principaux ne matchent plus.
