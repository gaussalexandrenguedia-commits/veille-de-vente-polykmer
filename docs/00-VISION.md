# 00 — Vision & Objectifs

## Problème

Au Cameroun et en CEMAC, les décisions commerciales (pricing, assortiment, promos, sourcing) se prennent **à l'aveugle** :

- 80 %+ des ventes dans l'informel → aucune donnée centralisée.
- Prix volatils (change, douane, corridors, saisonnalité).
- Concurrence opaque (importations Chine, Dubaï, Nigeria, Turquie).
- Signaux clients dispersés (commentaires Facebook, statuts WhatsApp).

## Vision

> **Devenir le « baromètre des ventes » du Cameroun et de la CEMAC** : une plateforme qui capte les prix et tendances où qu'ils soient (marché Mokolo comme groupe Facebook), les transforme en KPIs actionnables, et alerte avant les ruptures et les mouvements concurrents.

## Objectifs mesurables (12 mois)

| Objectif | Cible |
|---|---|
| Produits suivis (référentiel) | 500 SKU prioritaires (alimentaire, électroménager, cosmétique, téléphonie, matériaux) |
| Marchés couverts | 8 marchés (4 Cameroun + 4 CEMAC) |
| Sources digitales | 5 (Jumia, Glotelho, Izizar/Glovo, CoinAfrique, 50 pages/groupes FB) |
| Fraîcheur prix digital | < 24 h |
| Fraîcheur prix terrain | < 7 jours |
| Alertes utiles / mois | 50+ (variation prix > 10 %, rupture, nouveau concurrent) |
| Utilisateurs | 20 comptes (commerciaux, acheteurs, dirigeants PME/importateurs) |

## Utilisateurs cibles

1. **Importateurs / grossistes** (Douala, Yaoundé) : anticiper prix d'achat, TEC, corridors.
2. **Détaillants & e-commerçants** : ajuster prix/promos, détecter ruptures concurrents.
3. **Marques & distributeurs** : suivre lancement concurrents, perception produit.
4. **ONG / institutions** : sécurité alimentaire, suivi inflation (INS, BEAC en miroir).
5. **Équipes terrain** : enquêteurs avec smartphone Android bas de gamme, mode hors-ligne.

## Principes de conception

1. **Hybride digital + humain** — jamais de scraping seul, jamais de terrain seul.
2. **Léger & économe en data** — outils offline-first, images compressées, USSD/SMS en fallback.
3. **Français d'abord, pidgin/anglais toléré** — formulaires bilingues FR/EN (Cameroun anglophone).
4. **Preuve par l'exemple** — chaque KPI doit répondre à une décision (« dois-je augmenter mon prix du riz de 5 % ? »).
5. **Éthique & légal** — consentement, anonymisation, respect CGU/robots.txt.

## Périmètre v0.1 (ce repo)

- ✅ Référentiels : catégories, produits, marchés, corridors, sources.
- ✅ Modèle de données Postgres + API FastAPI (relevés, prix, alertes).
- ✅ 2 scrapers de démo (Jumia CM, CoinAfrique) + squelette Facebook/Playwright.
- ✅ Formulaire terrain KoboToolbox (XLSForm) + guide enquêteur.
- ✅ Dashboard Streamlit MVP sur données d'exemple.
- ⏳ Phase 2 : WhatsApp/Telegram, NLP sentiment, API Mobile Money, Metabase/Power BI.

## Hors périmètre (pour l'instant)

- Prédiction ML des prix (phase 3).
- Application mobile native (KoboToolbox suffit en v0.1).
- Couverture UEMOA / Nigeria en profondeur (uniquement corridors d'import).
