# 02 — Indicateurs clés (KPIs)

Chaque KPI répond à une **décision commerciale**. Formule + seuil d'alerte + source.

---

## A. Variations de prix & promotions

### A1. Prix médian de détail par produit × ville
- **Formule** : médiane des prix relevés (pondérée : terrain ×2, digital ×1) sur 7 jours glissants.
- **Décision** : « Mon prix est-il dans le marché ? »
- **Alerte** : écart > 10 % vs médiane ville.

### A2. Variation hebdo / mensuelle (%)
- **Formule** : `(médiane_S - médiane_S-1) / médiane_S-1 × 100`.
- **Alerte** : |variation hebdo| > 10 % → 🔴 ; > 5 % → 🟡.

### A3. Écart gros / détail (marge implicite)
- **Formule** : `(prix_détail - prix_gros) / prix_gros × 100`.
- **Décision** : négocier avec grossistes, détecter pénuries.

### A4. Taux de promotion
- **Formule** : % d'offres avec remise/bundle sur 7 jours, par catégorie + canal.
- **Signaux** : remise %, bundle (« 3 pour 2 »), bonus Mobile Money (« -5 % si MoMo »).

### A5. Prix plancher / plafond observés
- Min/max par produit × ville × semaine (détection dumping ou spéculation).

## B. Disponibilité & logistique

### B1. Taux de rupture
- **Formule** : % de relevés avec `rupture = oui` par produit × marché.
- **Alerte** : rupture > 20 % sur un traceur (riz, huile, ciment) → 🔴.

### B2. Délai d'approvisionnement corridor
- Jours moyens constatés par corridor (Douala-Bangui, Douala-N'Djamena…).
- **Alerte** : délai > moyenne + 30 %.

### B3. Surcoût logistique estimé
- Coût transport + « tracasseries » reporté au prix final (enquête qualitative → indice 1-5).

## C. Concurrence & lancements

### C1. Nouveaux entrants (marques / vendeurs)
- Nb de nouvelles marques ou vendeurs détectés / semaine / catégorie.
- Origines suivies : Chine, Dubaï, Nigeria, Turquie, Inde.

### C2. Part de voix digitale
- % de mentions/offres par marque sur les sources digitales suivies.

### C3. Prix d'attaque concurrent
- Prix le plus bas d'un nouveau concurrent vs médiane (−X %).

## D. Perception & réclamations (sentiment)

### D1. Score de sentiment (−100 à +100)
- Analyse des commentaires FB/Telegram/TikTok (lexique FR + pidgin + anglais en v0.1, modèle NLP en phase 2).
- **Alerte** : score < −20 sur une marque/produit sur 7 jours.

### D2. Top motifs de plainte
- Classification : prix, qualité, livraison, SAV, arnaque présumée, rupture.
- Livrable : nuage + top 5 hebdo.

### D3. Taux de réponse vendeur (si observable)
- % de commentaires avec réponse vendeur < 24 h (proxy qualité service).

## E. Demande & Mobile Money (phase 2)

### E1. Indice de demande
- Nb d'offres × engagement (likes/commentaires/partages) par catégorie.

### E2. Pénétration Mobile Money
- % d'offres mentionnant OM/MoMo/Moov + % avec incitation (frais offerts, remise).

---

## Seuils d'alerte par défaut

| Gravité | Condition | Canal |
|---|---|---|
| 🔴 Critique | Variation prix > 15 % / rupture traceur > 20 % / sentiment < −40 | WhatsApp + dashboard |
| 🟡 Attention | Variation 5-15 % / nouveau concurrent / sentiment < −20 | Dashboard + bulletin hebdo |
| 🟢 Info | Nouveauté produit, promo massive | Bulletin hebdo |

## Restitution

- **Dashboard temps réel** (Streamlit en MVP → Metabase/Power BI en prod).
- **Bulletin hebdo PDF/WhatsApp** : top 10 variations, ruptures, nouveaux concurrents, sentiment.
- **Alertes push** : WhatsApp/Telegram pour les abonnés (opt-in).
