# 10 — Application web unifiée 🌐

> **Tout le projet sous forme d'app web** : un seul serveur (`uvicorn`), une seule URL, zéro build. Les modules existants (API, sniper, scrapers, terrain) restent inchangés — le web les pilote et les visualise.

## 1. Lancement

```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- `/` tableau de bord · `/prix` · `/alertes` · `/sniper` · `/social` · `/releves` · `/referentiels`
- `/docs` API Swagger · `/healthz` santé
- Mode démo : SQLite `veille_demo.db` auto-créée + seed (~900 relevés, 24 commentaires, alertes). Prod : `DATABASE_URL` Postgres dans `.env`.

## 2. Architecture (1 serveur, 0 dépendance front)

```
Navigateur ──HTTP──▶ FastAPI :8000 ──┬── pages Jinja2 (coquille légère)
                                     ├── /api/v1/* (JSON, données)
                                     ├── /static/* (CSS/JS/graphiques SVG maison)
                                     ├── Postgres (prod) ou SQLite (démo)
                                     └── lecture seule sniper.db (miroir temps réel)
```

Pas de React/Vue, pas de CDN : tout est servi en local (fonctionne avec une connexion instable, important pour les équipes terrain). Les graphiques sont générés en SVG vanilla (`charts.js`).

## 3. Les modules « massifs » — version CEMAC réaliste

Inspirations assumées, redescendues à notre échelle et nos moyens :

| Plateforme leader | Notre module web | Différence honnête |
|---|---|---|
| **Competera / Intelligence Node** (milliards de SKU) | `/prix` : référentiel SKU, médianes par ville, variations, seuils | centaines de SKU ciblés, pas des milliards ; mais **données terrain réelles** qu'ils n'ont pas |
| **Meltwater / Brandwatch / Talkwalker** (300k sources, IA) | `/social` : commentaires FB/Telegram scorés FR/pidgin/EN, motifs, timeline | panel de sources consenties + saisie manuelle, lexique maison (pas de LLM géant — voir `semantic:` côté sniper pour l'option locale) |
| **Apify / Bright Data** (milliers d'actors, 72M proxys) | `scrapers/` + `sniper/` + page `/sniper` (flotte de cibles, fraîcheur, santé) | polling poli ciblé ; Bright Data/Apify restent des **options payantes** si un jour il faut passer à l'échelle (budgets ×100) |
| **Shodan / Censys** (scan internet global) | Hors périmètre volontaire | OSINT infra ≠ veille commerciale ; cité pour mémoire uniquement |

**Doctrine** : profondeur locale (marchés, langues, Mobile Money) plutôt que largeur mondiale. C'est là que les géants sont aveugles — et que ce projet gagne.

## 4. Passer à l'échelle (quand ? comment ?)

1. **Données** : SQLite → Postgres (déjà supporté) → TimescaleDB si > 1M relevés.
2. **Collecte** : 1 runner sniper → N workers par tier (hot/warm/cold) + file RQ/Celery ; scrapers planifiés (cron/APScheduler).
3. **Social** : lexique → modèle multilingue fine-tuné (phase 3) ; panel FB/Telegram élargi avec accords.
4. **Front** : Jinja actuel tient des milliers de pages vues/jour ; envisager un build SPA seulement si besoin d'interactions complexes (édition inline massive, websockets).
5. **Temps réel poussé** : webhooks partenaires (déjà `:8001`) ; polling massif tiers = prestataires (Apify/Bright Data) **ou** partenariats, jamais de scraping sauvage.

## 5. Runbook express

| Symptôme | Action |
|---|---|
| Page vide / erreur API | `curl localhost:8000/healthz` ; logs uvicorn ; supprimer `veille_demo.db` pour re-seeder |
| `/sniper` affiche l'onboarding | normal : lancer `python -m sniper.runner` (voir page) |
| Alertes non générées | bouton « Générer » (page Alertes) ou `POST /api/v1/kpi/alertes/generer` |
| Lenteurs Postgres | vérifier index (voir `init.sql`) ; `jours` plus petits sur `/prix` |
