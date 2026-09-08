# Veille de Vente — Cameroun & Afrique Centrale (CEMAC)

> Système de veille commerciale qui combine **scraping digital** + **remontée terrain** + **données institutionnelles** pour suivre prix, promos, stocks, concurrence et perception client au Cameroun et en zone CEMAC.

[![Zone](https://img.shields.io/badge/zone-Cameroun%20%2B%20CEMAC-green)]()
[![Stack](https://img.shields.io/badge/stack-Python%20%7C%20FastAPI%20%7C%20Streamlit%20%7C%20Postgres-blue)]()
[![Statut](https://img.shields.io/badge/statut-MVP%20v0.1-orange)]()

---

## 🎯 Pourquoi ce projet ?

Au Cameroun et en Afrique centrale, **+80 % des ventes passent par l'informel** : marchés physiques, groupes Facebook/WhatsApp/Telegram, vendeurs ambulants. Les outils de veille classiques (100 % web) sont donc aveugles.

Ce projet répond à ce défi avec une approche hybride :

```
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────┐
│  DIGITAL        │   │  TERRAIN         │   │  INSTITUTIONNEL │
│  Jumia, Glotelho│   │  Relevés prix    │   │  INS, BEAC,     │
│  CoinAfrique,   │ + │  KoboToolbox/ODK │ + │  Douanes, TEC   │ ──▶ KPIs + Dashboard
│  FB/WhatsApp/   │   │  Marchés phares  │   │  Taux, corridors│
│  Telegram       │   │                  │   │                 │
└─────────────────┘   └──────────────────┘   └─────────────────┘
```

## 📁 Structure du repo

```
veille-de-vente-polykmer/
├── README.md                  ← vous êtes ici
├── docs/                      ← conception complète (vision, sources, KPIs, archi, roadmap)
│   ├── 00-VISION.md
│   ├── 01-SOURCES-COLLECTE.md
│   ├── 02-KPI.md
│   ├── 03-ARCHITECTURE.md
│   ├── 04-MODELE-DONNEES.md
│   ├── 05-ROADMAP.md
│   ├── 06-DEFIS-CEMAC.md
│   └── 07-GUIDE-TERRAIN.md
├── backend/                   ← API FastAPI (ingestion + KPIs + alertes)
├── scrapers/                  ← scripts Python (Jumia, CoinAfrique, Facebook…)
├── terrain/                   ← formulaires KoboToolbox + référentiel marchés
├── dashboard/                 ← dashboard Streamlit (MVP visualisation)
├── infra/                     ← docker-compose + init.sql Postgres
└── data/samples/              ← jeux de données d'exemple
```

## 🚀 Démarrage rapide (5 min)

### Option A — Dashboard démo (sans base de données)

```bash
cd dashboard
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Le dashboard charge `data/samples/prix_exemple.csv` et affiche prix, variations, promos, sentiment.

### Option B — Stack complète (API + Postgres + Dashboard)

```bash
# 1. Lancer Postgres
docker compose -f infra/docker-compose.yml up -d

# 2. Lancer l'API
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Lancer le dashboard (2e terminal)
cd dashboard
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- API : http://localhost:8000/docs (Swagger)
- Dashboard : http://localhost:8501

### Option C — Lancer un scraper d'exemple

```bash
cd scrapers
pip install -r requirements.txt
python jumia_cm.py --query "riz 50kg" --max-pages 2 --out ../data/jumia_riz.json
python coinafrique.py --query "congelateur" --ville douala --out ../data/coinafrique.json
```

## 📊 Ce que surveille le MVP v0.1

| KPI | Source | Fréquence |
|---|---|---|
| Prix détail / gros + variations % | Scrapers + relevés terrain | Quotidien (digital), hebdo (terrain) |
| Promos & bundles Mobile Money | Scrapers + terrain | Quotidien |
| Ruptures & délais corridors | Terrain + alertes logistique | Hebdo |
| Nouveaux concurrents / marques | Scrapers + terrain | Hebdo |
| Sentiment commentaires | Scrapers FB + analyse NLP | Quotidien |

Marchés pilotes : **Douala (Central, Mboppi), Yaoundé (Mokolo, Mfoundi), Bafoussam, Garoua** → extension Brazzaville (Poto-Poto), N'Djamena, Bangui, Libreville, Malabo en phase 2.

## 🗺️ Roadmap

- **Phase 0 (S1)** : cadrage + référentiels produits/marchés ✅ *— ce repo*
- **Phase 1 (S2-S5)** : scrapers Jumia/CoinAfrique + formulaire Kobo + API + dashboard MVP
- **Phase 2 (S6-S10)** : FB/WhatsApp/Telegram + NLP sentiment + alertes + corridors logistiques
- **Phase 3 (S11+)** : données INS/BEAC/Douanes + Mobile Money agrégateurs + Power BI / Metabase prod

Détail : [`docs/05-ROADMAP.md`](docs/05-ROADMAP.md)

## 📚 Lire la conception complète

1. [Vision & objectifs](docs/00-VISION.md)
2. [Sources & canaux de collecte](docs/01-SOURCES-COLLECTE.md)
3. [KPIs détaillés](docs/02-KPI.md)
4. [Architecture technique](docs/03-ARCHITECTURE.md)
5. [Modèle de données](docs/04-MODELE-DONNEES.md)
6. [Roadmap](docs/05-ROADMAP.md)
7. [Défis CEMAC](docs/06-DEFIS-CEMAC.md)
8. [Guide enquêteurs terrain](docs/07-GUIDE-TERRAIN.md)

## 🤝 Contribuer

1. `git checkout -b feat/ma-fonctionnalite`
2. Ajoutez tests + doc
3. PR vers `main`

## ⚖️ Conformité & éthique

- Respecter les CGU des plateformes (délais, robots.txt, pas de contournement agressif).
- Données terrain : consentement vendeurs, anonymisation, pas de prix nominatifs publiés.
- Voir [`docs/06-DEFIS-CEMAC.md`](docs/06-DEFIS-CEMAC.md) § cadre légal (CEMAC/COBAC, lois nationales).

---
*Zone couverte : Cameroun 🇨🇲 + CEMAC (Congo 🇨🇬, Gabon 🇬🇦, Tchad 🇹🇩, RCA 🇨🇫, Guinée équatoriale 🇬🇶) + corridors Nigeria 🇳🇬 / Dubaï / Chine / Turquie.*
