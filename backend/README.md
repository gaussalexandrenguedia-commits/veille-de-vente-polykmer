# Application web — Veille Vente CM & CEMAC

Un seul serveur FastAPI : **pages HTML + API JSON + statiques**. Zéro build, zéro dépendance externe (CSS/JS/graphiques maison).

## Lancement (30 secondes, mode démo)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# -> http://localhost:8000  (tableau de bord)
# -> http://localhost:8000/docs  (API Swagger)
```

Au premier démarrage : base SQLite `veille_demo.db` auto-créée et alimentée (référentiels + ~900 relevés + commentaires + alertes). Pour repartir de zéro : supprimez `veille_demo.db` et relancez.

## Mode production (Postgres)

```bash
cp .env.example .env   # renseigner DATABASE_URL=postgresql+psycopg2://...
docker compose -f ../infra/docker-compose.yml up -d   # crée le schéma (init.sql)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Pages

| URL | Contenu |
|---|---|
| `/` | Tableau de bord : KPIs, courbe prix, variations, ruptures, promos, couverture, alertes |
| `/prix` | Price intelligence : courbes par ville, stats, relevés par produit |
| `/alertes` | Alertes actives, génération, résolution |
| `/sniper` | Miroir temps réel du module sniper (état, fraîcheur, santé sélecteurs) |
| `/social` | Écoute sociale : sentiment, motifs, timeline, saisie scorée auto |
| `/releves` | Saisie manuelle/terrain + derniers relevés |
| `/referentiels` | Produits, marchés, sources |
| `/ia` | Agent IA : parser NLP, vision/OCR, scoreur, messages, rapport (Gemini + repli offline) |
| `/deals` | 🎯 Opportunités : statuts, score marché, actions vendeur (appel/WhatsApp) |
| `/deals` § 🔎 Collecte | Lancement collecte réelle Jumia/CoinAfrique + suivi job (clé API requise) |

## Endpoints web (en plus de l'API v0.1)

- `GET /api/v1/dashboard/summary?produit=&jours=` — tout le dashboard en 1 appel
- `GET /api/v1/dashboard/courbe?produit=&jours=` — médianes journalières par ville
- `GET /api/v1/releves/recent?limit=` — derniers relevés enrichis
- `POST /api/v1/kpi/alertes/{id}/resoudre`
- `GET /api/v1/social/resume?jours=` · `POST /api/v1/social/commentaires` (sentiment auto)
- `GET /api/v1/sniper/status` · `GET /api/v1/sniper/selectors/{watch}` (lecture sniper.db)
- Deals : `GET /api/v1/deals` · `POST /deals` · `POST /deals/depuis-texte` · `PATCH /deals/{id}` · `GET /api/v1/villes`
- Collecte : `POST /api/v1/collecte/lancer` · `GET /collecte/jobs/{id}`
- Agent IA : `GET /api/v1/ai/statut` · `POST /ai/test|parser-annonce|analyser-image|scorer|message-vendeur` · `GET /ai/rapport-jour`

## Structure

```
backend/
├── app/
│   ├── main.py          # app + lifespan (seed) + statiques
│   ├── seed.py          # données démo (CSV + commentaires + alertes)
│   ├── templates/       # 9 pages Jinja2 (coquille, données via API)
│   ├── static/css/      # thème sombre responsive
│   ├── static/js/       # charts.js (SVG maison) + app.js (pages)
│   ├── routers/         # api + pages
│   └── services/        # kpi, sentiment, normalize
└── tests/               # pytest
```
