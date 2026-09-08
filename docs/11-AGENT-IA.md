# 11 — Agent IA (Gemini) 🤖

> L'IA transforme le système en agent autonome : elle comprend le langage informel (français/pidgin/abréviations), lit les visuels, score les opportunités vs le marché et rédige les messages vendeur. **Sans clé, tout reste utilisable en mode heuristique offline** (moins fin, jamais bloqué).

## 1. Les 4 capacités (où l'IA est branchée)

| Capacité | Route / usage | IA | Repli offline |
|---|---|---|---|
| **1. Parser NLP** : texte bruyant → JSON (`produit, prix, ville, nego, phone, intention`) | `POST /api/v1/ai/parser-annonce` + page `/ia` §1 | Gemini few-shot (fr/pidgin/`350k`/`dla`) | `ai_parse.parse_heuristic` (regex villes, prix k/M, `+237`, intentions vente/achat/spam) |
| **2. Vision/OCR** : flyers WhatsApp, affiches, photos → prix/tél/caractéristiques + validation vs titre | `POST /api/v1/ai/analyser-image` (JPEG/PNG/WebP ≤ 5 Mo) + `/ia` §3 | Gemini multimodal | — (vision exige l'IA → `503` explicite) |
| **3. Scoreur** : écart vs médiane marché, score /100, verdict, anti-fraude | `POST /api/v1/ai/scorer` + `/ia` §2 | Gemini (raisons de fraude en langage naturel) + médiane DB | verdicts + flags regex (prix dérisoire, demande d'avance, descriptif sommaire) |
| **4a. Message vendeur** : texte WhatsApp prêt + lien `wa.me` pré-rempli | `POST /api/v1/ai/message-vendeur` + `/ia` §4 | Gemini (ton direct, cash, négociation) | template |
| **4b. Rapport quotidien** : synthèse prix/ruptures/sentiment | `GET /api/v1/ai/rapport-jour` + `/ia` §5 | Gemini (250 mots, 3 sections + reco) | template markdown |
| **Bonus sniper** : gate sémantique temps réel | `semantic: {backend: gemini}` dans `watches.yaml` | validation < 2 s/signal | `heuristic` / `ollama` |

## 2. Configuration

```bash
# backend/.env  (JAMAIS commité — déjà dans .gitignore)
GEMINI_API_KEYS=cle1,cle2,cle3
GEMINI_MODEL=gemini-2.5-flash
```

- **Rotation + failover** : tirage aléatoire, bascule inter-clés sur 429/5xx, repli `gemini-2.5-flash → gemini-2.0-flash` sur 404.
- **Statut** : `GET /api/v1/ai/statut` (clés masquées `AQ.Ab8…TfKV`) · **Test live** : `POST /api/v1/ai/test` → `{ok, latence_ms}`.
- Sniper : `export GEMINI_API_KEYS=…` (ou `sniper/.env` + `export $(cat .env | xargs)`).

## 3. Sécurité des clés ⚠️

1. Les clés vivent **uniquement** dans `backend/.env` et `sniper/.env` (vérifier : `git check-ignore backend/.env`).
2. Jamais loguées, jamais renvoyées par l'API (tests `test_mask_key`).
3. **Si une clé a transité par un chat/email, régénérez-la** dans Google AI Studio après vos tests, puis mettez à jour `.env`.
4. Quotas : 3 clés = 3× le quota gratuit ; le failover absorbe les pics. Surveillez l'usage dans AI Studio.

## 4. Latences & coûts typiques (Flash)

| Appel | Latence | Coût indicatif |
|---|---|---|
| Parser / scorer / message | 0,5-2 s | ~0,0001 $ |
| Vision (image 1 Mo) | 1-3 s | ~0,0005 $ |
| Rapport quotidien | 2-5 s | ~0,001 $ |

Budget mensuel réaliste (100 signaux/jour) : **< 2 $**. Le design « règles d'abord, IA ensuite » (gate post-règles, §4b/09) évite les appels inutiles.

## 5. Garde-fous anti-hallucination

- Température 0, sorties JSON contraintes (`response_mime_type`), prompts few-shot.
- `normalize_ai_result` : prix borné (0–1e9), téléphone revalidé (9 chiffres), intention repli heuristique.
- Le **marché (DB) reste la vérité** pour les chiffres ; l'IA ne fait que le langage et les raisons.
- Images : `correspond: true/false` explicite ; un humain valide avant tout paiement.
