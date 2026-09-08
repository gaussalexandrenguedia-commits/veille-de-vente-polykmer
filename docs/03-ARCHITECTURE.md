# 03 — Architecture technique

## Vue d'ensemble

```
SOURCES                         INGESTION                    STOCKAGE              RESTITUTION
─────────                       ─────────                    ────────              ───────────
Jumia, Glotelho, CoinAfrique ─┐
FB / Telegram / TikTok ───────┼──▶ scrapers/ (Python) ──▶ FastAPI /ingest ─┐
KoboToolbox (terrain) ────────┼──▶ webhook Kobo ───────▶ FastAPI /ingest ─┼──▶ Postgres ──▶ Streamlit (MVP)
Fichiers CSV manuels ─────────┘   + validation pydantic                     │    │           Metabase/PowerBI (prod)
                                                                                │    └──▶ jobs KPIs ──▶ alertes WhatsApp
                                                                                └──▶ data/ (brut JSON/CSV)
```

## Composants

| Composant | Choix MVP (ce repo) | Choix prod (phase 2-3) |
|---|---|---|
| Scraping web | Python `requests/BeautifulSoup` + `Playwright` (JS) | + file d'attente (Celery/RQ), proxy rotation, monitoring |
| Collecte terrain | KoboToolbox / ODK (gratuit, offline) | + appli légère custom si besoin |
| API ingestion | **FastAPI** (`backend/`) | + auth JWT, quotas, audit |
| Base de données | **Postgres 16** (voir `infra/init.sql`) | + TimescaleDB pour séries prix, backups S3 |
| Calcul KPIs | jobs Python (`backend/app/services/kpi.py`) | + dbt ou Airflow |
| Sentiment | lexique FR/pidgin/EN (règles) | modèle multilingue (AfroXLMR / CamemBERT + fine-tune) |
| Dashboard | **Streamlit** (`dashboard/`) | Metabase ou Power BI |
| Alertes | logs + CSV (MVP) | WhatsApp Cloud API / Telegram Bot |
| Paiements/tendances | saisie manuelle (MVP) | API Campay / Notch Pay / Cinpay (partenariat) |
| Hébergement | local / petit VPS | VPS (Hetzner/OVH) ou cloud, ~20-50 €/mois au départ |

## Contrats d'API (MVP)

```
POST /api/v1/releves            → créer un relevé terrain ou digital
GET  /api/v1/prix?produit=&ville=&debut=&fin=  → série de prix
GET  /api/v1/kpi/variations?seuil=10           → variations > seuil
GET  /api/v1/kpi/ruptures                      → taux de rupture
GET  /api/v1/alertes?gravite=rouge             → alertes actives
POST /api/v1/ingest/scraper     → ingestion lot depuis scrapers (clé API)
POST /api/v1/ingest/kobo        → webhook KoboToolbox
GET  /api/v1/produits / /marches / /sources    → référentiels
```

Détail interactif : `http://localhost:8000/docs` (Swagger auto-généré).

## Modèle de déploiement MVP

```bash
# infra/docker-compose.yml : postgres + (optionnel) metabase
docker compose -f infra/docker-compose.yml up -d
```

Variables d'environnement (`.env`, voir `backend/.env.example`) :
`DATABASE_URL, API_KEY_INGEST, KOBO_TOKEN, WHATSAPP_TOKEN (phase 2)`.

## Qualité & fiabilité

- Chaque prix stocké avec : `source_id, url/preuve, horodatage, devise (XAF), ville, vendeur_hash, méthode (scrapé/terrain/manuel)`.
- Déduplication : hash `(produit_normalisé, vendeur, prix, jour)`.
- Normalisation produits : table `produits` + alias (« riz parfumé 50kg », « riz 50 kg parfumé » → même SKU).
- Logs structurés JSON, retry 3× sur scraping, backoff exponentiel.
- Tests : `pytest backend/tests` (à compléter en phase 1).

## Coûts estimés (ordre de grandeur, début)

| Poste | Coût mensuel |
|---|---|
| VPS 4 Go + Postgres | 15-30 € |
| KoboToolbox (serveur humanitarian gratuit) | 0 € |
| Enquêteurs (4 marchés × 1 passage/sem, défraiement) | 200-600 € selon pays |
| Forfaits data enquêteurs | 40-100 € |
| WhatsApp Cloud API (alertes) | ~0-20 € (volume faible) |
| **Total MVP terrain inclus** | **≈ 300-800 €/mois** |

## Sécurité

- Clé API pour `/ingest/*`, CORS restreint, rate-limit.
- Données vendeurs : hachage identifiants, pas de diffusion nominative sans consentement.
- Sauvegardes Postgres quotidiennes (pg_dump + copie externe).
