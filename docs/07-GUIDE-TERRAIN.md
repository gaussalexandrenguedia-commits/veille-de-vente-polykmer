# 07 — Guide de l'enquêteur terrain

*Version courte, imprimable. À remettre à chaque enquêteur avec le smartphone Kobo.*

## Avant la tournée

1. Chargez le téléphone + activez le mode hors-ligne Kobo (formulaire « Relevé prix » déjà téléchargé).
2. Vérifiez la liste des produits traceurs du jour (panier fixe, ~60 produits).
3. Prévoyez monnaie/transport, badge, lettre d'introduction.

## Sur le marché (1 passage / semaine / marché, même jour si possible)

1. **Saluez, expliquez** (30 secondes) : « Bonjour, je relève les prix pour un baromètre des marchés, c'est anonyme, ça prend 2 minutes. »
2. Pour chaque produit :
   - **Prix détail réellement pratiqué** (négociez légèrement comme un client normal).
   - **Prix affiché** si différent.
   - **Prix de gros** (carton/sac lot) si le vendeur accepte de le dire.
   - **Marque + origine** (ex. « Hisense, Chine »).
   - **Rupture ?** (produit absent des étals habituels → Oui).
   - **Promo ?** (affiche, bundle, remise MoMo → décrivez en 5 mots).
3. **Photo** (optionnel) : étagère/affiche prix, jamais de visage sans accord.
4. **Ne relevez jamais seul** dans les allées isolées ; restez courtois si refus (passez au suivant).

## Unités standards (à respecter absolument)

| Produit | Unité du relevé |
|---|---|
| Riz parfumé | sac 50 kg |
| Riz vrac | kg |
| Huile végétale | litre (bouteille 1 L) puis bidon 5 L si dispo |
| Sucre | kg + sac 50 kg |
| Farine | kg |
| Savon | pièce + carton |
| Ciment | sac 50 kg (préciser marque : Cimencam, Dangote…) |
| Congélateur / TV | capacité/taille + marque |
| Smartphone | modèle exact + RAM/stockage |

> Si le vendeur vend en « tine », « tas », « carton » : relevez le prix + l'unité locale, la conversion se fera au bureau.

## Saisie Kobo (hors-ligne OK)

- 1 soumission = 1 produit × 1 vendeur.
- Champs obligatoires : marché, produit, prix détail, unité, date/heure auto.
- Envoyez dès que vous avez du réseau (Wi-Fi de préférence).

## Fallback sans Kobo (SMS/WhatsApp au superviseur)

Format : `PRODUIT PRIX UNITE MARCHE`
Exemple : `RIZ-PARF-50KG 28500 SAC MOKOLO`
Le superviseur saisira dans l'API (`POST /releves`).

## Rémunération & contact

- Défraiement par tournée complète payé via MoMo le jour même.
- Problème / refus massif / incident : appelez le superviseur immédiatement.
- **Votre sécurité d'abord** : en cas de tension, arrêtez la tournée et partez.

## Contrôle qualité

- Le superviseur rappelle 10 % des vendeurs (contrôle).
- Relevés incohérents (prix ÷2 ou ×2 sans raison) = rappel + nouvelle formation.
- 3 tournées de qualité → bonus.
