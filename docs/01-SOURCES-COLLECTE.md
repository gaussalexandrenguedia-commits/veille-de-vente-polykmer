# 01 — Sources de données & Canaux de collecte

## 1. Commerce informel & réseaux sociaux (priorité haute)

C'est là que se joue l'essentiel du social-commerce local.

| Canal | Quoi collecter | Comment | Fréquence | Difficulté |
|---|---|---|---|---|
| **Groupes/pages Facebook** (ex. « Vente en ligne Douala/Yaoundé ») | Prix, photos, promos, commentaires/sentiment, vendeur, localisation | Playwright + compte dédié, ciblage 50 pages pilotes, respect CGU, extraction manuelle assistée si blocage | Quotidien | ⚠️ Élevée (anti-bot, login) |
| **WhatsApp Business** (catalogues, statuts) | Prix catalogue, dispo, bundles MoMo | Constitution d'un panel de ~100 vendeurs consentants ; export catalogue + captures structurées via formulaire | Hebdo | Moyenne (consentement requis) |
| **Telegram** (canaux de vente, importateurs) | Arrivages, prix gros, nouveautés | Telethon API (avec accord admins), mots-clés | Quotidien | Moyenne |
| **TikTok / Instagram** (vendeurs cosmétique, mode) | Tendances, prix affichés, engagement | Relevé manuel hebdo (top 30 comptes) en v0.1 | Hebdo | Faible (manuel) |

> ⚠️ Règle d'or : **toujours identifier le bot, limiter le débit (1 req / 3-5 s), respecter robots.txt et CGU**. En cas de blocage, basculer en collecte semi-manuelle via formulaire « relevé digital » (copier-coller assisté).

## 2. Plateformes e-commerce & marketplaces (priorité haute)

| Plateforme | Zone | Données | Technique |
|---|---|---|---|
| **Jumia Cameroun** (jumia.cm) | CM | Prix, ancien prix, remise %, vendeur, note, stock | BeautifulSoup/Playwright — voir `scrapers/jumia_cm.py` |
| **Glotelho** | CM | Prix téléphonie/électro, promos | BeautifulSoup |
| **Izizar / Glovo** | Douala/Yaoundé | Prix livraison, paniers alimentaires | API/Playwright si dispo, sinon relevé manuel |
| **CoinAfrique** | CEMAC | Annonces, prix, ville, vendeur | Voir `scrapers/coinafrique.py` |
| **Jiji.cm / Kiaki** (si actifs) | CM | Idem | À qualifier |

Bonnes pratiques : user-agent explicite, cache, reprise sur erreur, journalisation source+URL+horodatage pour chaque prix.

## 3. Données institutionnelles & macro (priorité moyenne)

| Source | Données | Usage dans la veille |
|---|---|---|
| **INS Cameroun** (statistiques) | IPC, prix moyens, rapports | Benchmark officiel, calibration |
| **BEAC** | Taux, masse monétaire, rapports conjoncture | Contexte inflation/change (XAF) |
| **Douanes Cameroun / CEMAC** | TEC, valeurs de référence, corridors | Expliquer variations prix import |
| **FAO / PAM / FEWS NET** | Prix alimentaires, sécurité alimentaire | Alertes denrées de base |
| **COBAC / agrégateurs MoMo** | Volumes transactions (si accessibles) | Proxy de la demande |

Collecte : téléchargement mensuel + extraction manuelle → table `indicateurs_macro`.

## 4. Remontée terrain — Trade Intelligence (priorité haute, différenciant)

Relevés de prix physiques réguliers par enquêteurs équipés de **KoboToolbox / ODK** (hors-ligne).

### Marchés stratégiques

**Phase 1 — Cameroun :**
- Douala : Marché Central, Mboppi, Marché Congo (tissus/import)
- Yaoundé : Mokolo, Mfoundi, Marché du Melen
- Bafoussam : Marché A ; Garoua : Marché central

**Phase 2 — CEMAC :**
- Brazzaville : Poto-Poto, Total
- N'Djamena : Marché Central, Dembé
- Libreville : Mont-Bouët
- Bangui : PK5
- Malabo : Mercado Central

Voir `terrain/markets.json` (coordonnées, jours d'affluence, contacts).

### Protocole de relevé (résumé)

1. 1 passage / semaine / marché (même jour, même heure si possible).
2. Panier fixe : ~60 produits traceurs (riz, huile, savon, ciment, smartphones d'entrée de gamme…).
3. Pour chaque produit : prix détail, prix gros (si dispo), marque, origine, rupture (O/N), photo étagère (optionnel).
4. Formulaire : `terrain/kobo-releve-prix.md` (+ XLSForm à importer dans Kobo).

### Corridors logistiques à suivre

- **Douala → Bangui** (marchandises RCA)
- **Douala → N'Djamena** (Tchad, le plus critique)
- **Douala → Brazzaville / Pointe-Noire** (via Sangmélima/Ouesso ou maritime)
- **Kribi → Yaoundé** (port en eau profonde, montante)
- **Frontière Nigeria (Ekok/Ikom)** et **Guinée équatoriale (Kye-Ossi)**

Pour chaque corridor : temps de transit, coût transport/tonne, tracasseries signalées, ruptures induites.

## 5. Paiements & tendances d'achat (priorité moyenne, phase 2)

- **Agrégateurs** : Campay, Notch Pay, Cinpay, Fapshi → volumes/nombre de transactions par catégorie (si partenariat API).
- **Signaux faibles** : mentions « Orange Money / MTN MoMo accepté », frais offerts, bundles « paiement MoMo = -5 % ».

## Matrice de couverture cible (v1.0)

| Famille produit | Digital | Terrain | Macro |
|---|---|---|---|
| Riz, huile, farine, sucre | ✅ | ✅✅ | ✅ |
| Électroménager, TV, congelateurs | ✅✅ | ✅ | — |
| Téléphonie & accessoires | ✅✅ | ✅ | — |
| Cosmétique & hygiène | ✅ (FB/TikTok) | ✅ | — |
| Matériaux (ciment, tôle) | ✅ (CoinAfrique) | ✅✅ | ✅ (douane) |
| Habillement / friperie | ✅ | ✅ | — |

## Registre des sources (à maintenir)

Chaque source collectée doit être déclarée dans la table `sources` (voir modèle de données) : nom, type, URL/compte, fréquence, responsable, statut légal (autorisé / toléré / partenariat), date de dernière collecte.
