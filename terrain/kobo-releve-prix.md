# Formulaire KoboToolbox — « Relevé prix marché » (v0.1)

> Importer dans KoboToolbox (https://kf.kobotoolbox.org) : nouveau projet → construire depuis zéro en suivant ce tableau, ou convertir via https://xlsform.org (XLSForm).

## Onglet `survey`

| type | name | label::Français | label::English | required | relevant | choice_filter | calculation |
|---|---|---|---|---|---|---|---|
| date | date_releve | Date du relevé | Survey date | yes | | | |
| select_one villes | ville | Ville | Town | yes | | | |
| select_one marches | marche | Marché | Market | yes | | ville=${ville} | |
| text | enqueteur | Nom enquêteur | Enumerator | yes | | | |
| select_one produits | produit | Produit (panier traceur) | Product | yes | | | |
| integer | prix | Prix détail réellement pratiqué (XAF) | Actual retail price (XAF) | yes | ${rupture} != '1' | | |
| integer | prix_affiche | Prix affiché si différent (XAF) | Displayed price if different | no | | | |
| integer | prix_gros | Prix de gros / lot (XAF) | Wholesale price | no | | | |
| text | unite_locale | Unité locale si ≠ standard | Local unit if different | no | | | |
| text | marque | Marque observée | Brand | no | | | |
| select_one origines | origine | Origine du produit | Origin | no | | | |
| select_one oui_non | rupture | Produit en rupture sur ce point de vente ? | Out of stock? | yes | | | |
| select_one oui_non | promo | Promotion / bundle visible ? | Any promo? | yes | | | |
| text | promo_detail | Détail promo (ex. « 3 pour 2 », « -5% si MoMo ») | Promo detail | no | ${promo} = '1' | | |
| select_one oui_non | paiement_momo | Mobile Money accepté / mis en avant ? | Mobile Money accepted? | no | | | |
| image | photo | Photo étagère / affiche (optionnel) | Shelf photo (optional) | no | | | |
| text | vendeur_code | Code vendeur (ex. MOK-A12, jamais de nom) | Vendor code | no | | | |
| note | fin | Merci ! Envoyez dès que vous avez du réseau. | Thanks! Upload when online. | | | | |

## Onglet `choices`

| list_name | name | label::Français | label::English | ville |
|---|---|---|---|---|
| villes | douala | Douala | Douala | |
| villes | yaounde | Yaoundé | Yaoundé | |
| villes | bafoussam | Bafoussam | Bafoussam | |
| villes | garoua | Garoua | Garoua | |
| villes | brazzaville | Brazzaville | Brazzaville | |
| villes | ndjamena | N'Djamena | N'Djamena | |
| villes | libreville | Libreville | Libreville | |
| villes | bangui | Bangui | Bangui | |
| marches | central_dla | Marché Central | Central Market | douala |
| marches | mboppi | Mboppi | Mboppi | douala |
| marches | mokolo | Marché Mokolo | Mokolo Market | yaounde |
| marches | mfoundi | Marché Mfoundi | Mfoundi Market | yaounde |
| marches | marche_a | Marché A | Market A | bafoussam |
| marches | central_gar | Marché central | Central Market | garoua |
| marches | poto_poto | Poto-Poto | Poto-Poto | brazzaville |
| marches | central_ndj | Marché Central | Central Market | ndjamena |
| marches | mont_bouet | Mont-Bouët | Mont-Bouët | libreville |
| marches | pk5 | PK5 | PK5 | bangui |
| produits | RIZ-PARF-50KG | Riz parfumé — sac 50 kg | Parboiled rice — 50 kg bag | |
| produits | HUILE-VEG-1L | Huile végétale — 1 L | Vegetable oil — 1 L | |
| produits | SUCRE-1KG | Sucre — 1 kg | Sugar — 1 kg | |
| produits | CIMENT-50KG | Ciment — sac 50 kg | Cement — 50 kg bag | |
| produits | CONGEL-200L | Congélateur 200 L | Freezer 200 L | |
| produits | TV-32 | TV 32" | TV 32" | |
| produits | SMART-ENTRY | Smartphone entrée gamme 64 Go | Entry smartphone 64 GB | |
| origines | CM | Cameroun | Cameroon | |
| origines | CN | Chine | China | |
| origines | NG | Nigeria | Nigeria | |
| origines | AE | Dubaï / EAU | Dubai / UAE | |
| origines | TR | Turquie | Türkiye | |
| origines | IN | Inde | India | |
| origines | autre | Autre | Other | |
| oui_non | 1 | Oui | Yes | |
| oui_non | 0 | Non | No | |

## Onglet `settings`

| form_title | id_string | version |
|---|---|---|
| Releve prix marche CM-CEMAC | releve_prix_cm_cemac | v0.1-2026-09-08 |

## Webhook → API (à configurer dans Kobo : Settings → REST Services)

- URL : `https://VOTRE-SERVEUR/api/v1/ingest/kobo`
- Méthode : POST, headers : `X-API-Key: <API_KEY_INGEST>`
- Le mapping des champs est dans `backend/app/routers/ingest.py` (`KOBO_FIELD_MAP`).

## Formulaire 2 (phase 2) — « Relevé digital » (copier-coller assisté Facebook/WhatsApp)

Champs : source (FB/WhatsApp/Telegram/TikTok) + lien ou nom vendeur (haché) + capture (copier titre + prix) + ville + produit du panier. Même webhook, `methode=manuel`, `source=Panel Facebook`.
