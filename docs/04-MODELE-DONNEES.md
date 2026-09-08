# 04 — Modèle de données

Implémentation SQL : `infra/init.sql`. Schéma ORM : `backend/app/models.py`.

## Diagramme (texte)

```
produits 1───∞ releves_prix ∞───1 sources
   │               │
   │               ├───1 marches (si terrain)
   │               └───1 corridors (si logistique)
   │
   └───∞ alertes ∞───1 regles_alerte
sources 1───∞ offres_digitales (annonces scrapées)
releves_prix ──译文 avertissement── verdict: commentaires (sentiment)
indicateurs_macro (INS/BEAC/douane, mensuel)
```

## Tables principales

### `produits` (référentiel SKU)
| Colonne | Type | Exemple |
|---|---|---|
| id | serial PK | 1 |
| sku | text unique | `RIZ-PARF-50KG` |
| nom | text | Riz parfumé 50 kg |
| categorie | text | Alimentaire |
| marques_suivies | text[] | {Mémé, Broli} |
| unite | text | sac 50kg |
| alias | text[] | {riz 50 kg parfumé, …} |
| traceur | bool | true (panier prioritaire) |

### `marches`
| Colonne | Type | Exemple |
|---|---|---|
| id | serial PK | 1 |
| nom | text | Marché Mokolo |
| ville / pays | text | Yaoundé / CM |
| lat / lon | float | 3.87 / 11.52 |
| jours_affluence | text[] | {sam, mer} |

### `sources`
| Colonne | Type | Exemple |
|---|---|---|
| id | serial PK | 1 |
| nom | text | Jumia Cameroun |
| type | enum | ecommerce / facebook / whatsapp / telegram / terrain / institutionnel / manuel |
| url_ou_compte | text | https://www.jumia.cm/… |
| frequence | text | quotidien |
| statut_legal | text | autorisé / toléré / partenariat |

### `releves_prix` (cœur)
| Colonne | Type | Notes |
|---|---|---|
| id | serial PK | |
| produit_id | FK | |
| source_id | FK | |
| marche_id | FK nullable | renseigné si terrain |
| prix | numeric | en XAF |
| prix_gros | numeric nullable | |
| devise | text default XAF | |
| ville / pays | text | |
| vendeur_hash | text | identifiant haché (anonyme) |
| marque | text | marque observée |
| origine | text | Chine, Nigeria… |
| rupture | bool default false | |
| promo | bool default false | + `promo_detail` (texte) |
| paiement_momo | bool | mention MoMo/OM |
| methode | enum | scrape / terrain / manuel / api |
| preuve_url | text | URL annonce ou ID soumission Kobo |
| observe_le | timestamptz | date d'observation |
| collecteur | text | nom enquêteur ou nom du scraper |

Index : `(produit_id, ville, observe_le)`, `(marche_id, observe_le)`.

### `offres_digitales` (annonces brutes enrichies)
`id, source_id, url unique, titre, prix, ancien_prix, remise_pct, vendeur_hash, ville, engagement (jsonb : likes/commentaires), capture_le`.

### `commentaires`
`id, offre_id nullable, source_id, texte, auteur_hash, langue (fr/en/pidgin), sentiment_score (-100..100), motif (prix/qualité/livraison/sav/arnaque/autre), capture_le`.

### `corridors` + `releves_logistique`
`corridors(id, nom, origine, destination, distance_km)` ; `releves_logistique(id, corridor_id, delai_jours, cout_tonne_xaf, indice_tracasserie 1-5, commentaire, observe_le)`.

### `indicateurs_macro`
`id, source (INS/BEAC/Douane/FAO), indicateur (IPC, prix_moyen_riz…), valeur, periode (mois), note`.

### `alertes`
`id, type (variation_prix/rupture/nouveau_concurrent/sentiment/logistique), gravite (rouge/jaune/vert), titre, detail jsonb, produit_id nullable, marche_id nullable, cree_le, resolu bool`.

## Règles de gestion

1. Prix toujours stockés en **XAF** (conversion à l'ingestion si besoin).
2. `observe_le` ≠ `cree_le` : l'observation terrain peut être saisie a posteriori.
3. Déduplication à l'insertion sur `(produit_id, vendeur_hash, prix, date(observe_le), source_id)`.
4. Normalisation produit via table `produits.alias` + matching flou (rapidfuzz) côté API.
5. Commentaires : conserver texte brut 90 jours puis ne garder que score + motif (sobriété + vie privée).
