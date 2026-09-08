# 05 — Roadmap de mise en œuvre

## Phase 0 — Cadrage (S1) ✅ *en cours — ce repo*

- [x] Vision, sources, KPIs, architecture, modèle de données
- [x] Squelette API + scrapers + dashboard + formulaire terrain
- [ ] Valider panier de 60 produits traceurs avec 3-5 commerçants pilotes
- [ ] Choisir 4 marchés pilotes Cameroun + recruter 2-4 enquêteurs
- [ ] Créer compte KoboToolbox + importer formulaire `terrain/`

**Livrable** : ce dépôt + liste produits/marchés validée.

## Phase 1 — MVP digital + terrain (S2-S5)

**S2 — Référentiels & API**
- Charger `produits` (500 SKU), `marches`, `sources`, `corridors` via API
- Finaliser `POST /releves`, `GET /prix`, validation + dédup
- Tests pytest + CI GitHub Actions

**S3 — Scrapers e-commerce**
- Jumia CM + CoinAfrique robustes (pagination, retry, logs)
- Planification quotidienne (cron / APScheduler)
- Table `offres_digitales` alimentée

**S4 — Terrain**
- Formation enquêteurs (voir `07-GUIDE-TERRAIN.md`)
- 2 tournées test / marché, ajustement formulaire
- Webhook Kobo → API opérationnel

**S5 — Dashboard + bulletin**
- Dashboard Streamlit branché sur Postgres (pas seulement CSV)
- Calcul variations/ruptures + page alertes
- Bulletin hebdo v1 (export PDF/WhatsApp manuel)

**Livrable S5** : 1er bulletin « Prix & ventes — Douala/Yaoundé » avec données réelles.

## Phase 2 — Social + sentiment + logistique (S6-S10)

- S6-S7 : panel 50 pages FB + 10 canaux Telegram ; formulaire « relevé digital » semi-manuel
- S8 : moteur sentiment v1 (lexique FR/pidgin/EN) + motifs de plainte
- S9 : suivi corridors (relevés transporteurs) + alertes logistique
- S10 : extension Brazzaville + N'Djamena (2 enquêteurs, 2 marchés)

**Livrable S10** : alertes WhatsApp auto + couverture 6 marchés / 3 pays.

## Phase 3 — Institutionnel + scale (S11-S16)

- Intégration mensuelle INS/BEAC/Douanes (table `indicateurs_macro`)
- Partenariats agrégateurs MoMo (Campay/NotchPay/Cinpay/Fapshi)
- Migration dashboard prod (Metabase ou Power BI), TimescaleDB
- Modèle NLP sentiment v2 (fine-tune multilingue)
- Monétisation : abonnements (freemium bulletin / premium alertes + API)

**Livrable S16** : offre commerciale + 20 comptes payants/gratuits actifs.

## Risques & parades

| Risque | Parade |
|---|---|
| Blocage anti-bot FB | collecte semi-manuelle + panel vendeurs consentants |
| Turnover enquêteurs | défraiement ponctuel via MoMo, formation courte, supervision |
| Données sales (unités, doublons) | validation pydantic + normalisation + contrôle hebdo |
| Coûts terrain | démarrer 4 marchés, mutualiser avec partenaires (ONG, associations commerçants) |
| Légal (scraping, données perso) | registre sources, hachage vendeurs, CGU respectées |

## Jalons de décision (go / no-go)

- **Fin S5** : si < 500 relevés/semaine ou qualité < 70 % → revoir protocole avant d'étendre.
- **Fin S10** : si 0 client pilote prêt à payer/tester → pivoter cible (ONG/institutions).
