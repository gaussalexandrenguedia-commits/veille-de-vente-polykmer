# 06 — Spécificités & défis régionaux (CEMAC)

## 1. Prédominance de l'informel (> 80 %)

**Implication** : le scraping seul ne voit qu'une minorité du marché.
**Réponse du projet** :
- Relevés physiques hebdo obligatoires (marchés phares).
- Panel vendeurs WhatsApp/Facebook consentants.
- Pondération terrain ×2 dans les médianes (voir `02-KPI.md`).
- Formulation des prix en langage local dans les formulaires (ex. « sac de riz 50 kg », « congélateur 200 L »).

## 2. Logistique & transit douanier

- **TEC CEMAC** : toute hausse de droit se répercute en 2-6 semaines sur les prix import (électroménager, matériaux).
- **Corridors critiques** : Douala-N'Djamena (le plus cher/long), Douala-Bangui (sécurité), Kye-Ossi (Guinée équatoriale), Ekok (Nigeria).
- **Tracasseries routières** : barrages, péages informels → intégrer un *indice 1-5* relevé auprès des transporteurs.
- **Saisonnalité** : saison des pluies = routes dégradées = délais + prix alimentaires.
- Le dashboard doit afficher **prix + délai corridor** côte à côte pour expliquer les variations.

## 3. Pénétration réseau & équipements

- Smartphones bas de gamme, data chère, coupures électriques/Internet.
- **Outils offline-first** : KoboToolbox (saisie sans réseau, envoi différé), formulaires courts (< 5 min / produit), photos compressées, pas de vidéo.
- Fallback : saisie SMS/WhatsApp structurée (« RIZ 50KG 28500 MOKOLO ») si Kobo indisponible.
- Dashboard « lite » : version texte/WhatsApp du bulletin pour les petits écrans.

## 4. Langues & culture commerciale

- Français + anglais (Nord-Ouest/Sud-Ouest Cameroun) + pidgin + langues locales sur les marchés.
- Négociation : le « premier prix » annoncé ≠ prix de transaction → consigne enquêteurs : relever le **prix réellement pratiqué** (après négociation légère) + noter « prix affiché » si différent.
- Unités locales : « tine » (huile), « sac », « carton », « pièce », « tas » → table de conversion dans le formulaire.

## 5. Change & Mobile Money

- XAF peggé à l'euro (stabilité), mais **prix import sensibles** au dollar/yuan (Chine) et naira (Nigeria).
- Mobile Money dominant : **MTN MoMo, Orange Money** (CM), Airtel Money (Tchad/Gabon/Congo), Moov (CAR/Gabon).
- Suivre : mentions MoMo dans les offres, frais offerts, bundles → proxy d'adoption et de pouvoir d'achat.

## 6. Cadre légal & conformité (à valider avec un juriste local)

- **Scraping** : respecter CGU + robots.txt + débits raisonnables ; pas de contournement de login/paywall ; pas de revente de contenus (photos, textes) — seuls les *faits* (prix, dates) alimentent les KPIs.
- **Données personnelles** : hacher les identifiants vendeurs ; consentement explicite pour le panel WhatsApp ; droit de retrait.
- **Cameroun** : loi sur la protection des données / communications électroniques ; vérifier obligations déclaratives.
- **CEMAC/COBAC** : réglementation des paiements si on touche aux flux MoMo (on ne traite que des agrégats via partenaires agréés).
- Tenir un **registre des sources** avec statut légal (cf. `01-SOURCES-COLLECTE.md`).

## 7. Sécurité des enquêteurs

- Ne jamais relever seul dans les zones sensibles ; badge + lettre d'introduction ; pas de photos de personnes sans accord.
- Rémunération via Mobile Money le jour même ; budget transport prévu.
- Zones à risque (Extrême-Nord CM, RCA partielle) : collecte à distance (appels vendeurs connus) uniquement.
