# Scrapers — collecte réelle e-commerce CM

Sources : **Jumia Cameroun** (`jumia_cm.py`), **CoinAfrique** (`coinafrique.py`).
`run_all.py` exécute tout + pousse vers l'API. `utils.py` : session polie
(User-Agent, retries, throttle), parsing prix XAF, push API.

## Usage

```bash
pip install -r requirements.txt
python jumia_cm.py --query "riz 50kg" --max-pages 2 --out ../data/jumia_riz.json
python coinafrique.py --query congelateur --ville douala --push --api-url http://localhost:8000 --api-key $API_KEY_IMPORT
python run_all.py --push --api-url http://localhost:8000 --api-key $API_KEY_IMPORT  # tout + push API (cron 6h/18h WAT)
```

Villes CoinAfrique : douala, yaounde, bafoussam, garoua, brazzaville,
libreville, ndjamena… (voir `CIBLES` dans `run_all.py`).

## Fiabilité

Parsing isolé en fonctions pures (`parse_jumia_html`, `parse_coin_html`),
testées hors-ligne : `pytest tests/` (fixtures HTML réalistes).
Si un site change son HTML, les tests indiquent quoi ajuster.
Repli générique intégré si les sélecteurs principaux ne matchent plus.
Respect : throttle 1,5 s + jitter, max 2-3 pages, `--push` explicite.
