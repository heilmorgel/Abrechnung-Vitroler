# Abrechnung Vitroler

Home-Assistant-Add-on zur Aufteilung von Kondominiums-Rechnungen (Fernwärme, Wasser/Abwasser, Strom) auf EG, 1. OG und 2. OG.

## Schnellstart (Entwicklung)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
set DATA_DIR=./data
set ALLOW_ALL_HOSTS=true
set STATIC_DIR=frontend/dist
python -m uvicorn backend.app.main:app --port 8099
```

UI: http://127.0.0.1:8099 — API-Health: http://127.0.0.1:8099/api/health

## Add-on bauen

```bash
cd frontend && npm install && npm run build && cd ..
python scripts/prepare_addon.py
# Ordner addon/ nach /addons/abrechnung_vitroler kopieren
```

Details: [addon/DOCS.md](addon/DOCS.md)

## Tests

```bash
pytest backend/tests -q
```

Algorithmus-Referenz (Excel): [ABRECHNUNGSALGORITHMUS.md](ABRECHNUNGSALGORITHMUS.md)
