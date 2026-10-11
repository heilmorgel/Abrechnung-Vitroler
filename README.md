# Abrechnung Vitroler

Home-Assistant-Add-on zur Aufteilung von Kondominiums-Rechnungen (Fernwärme, Wasser/Abwasser, Strom) auf EG, 1. OG und 2. OG.

Add-on-Code liegt vollständig unter [`addon/`](addon/) (Backend, Frontend, Dockerfile) — so kann Home Assistant direkt aus dem GitHub-Repo bauen.

## Installation in Home Assistant

1. **Einstellungen → Add-ons → Add-on-Store → ⋮ → Repositories**
2. Repository hinzufügen: `https://github.com/heilmorgel/Abrechnung-Vitroler`
3. **Abrechnung Vitroler** installieren und starten
4. Über Ingress / Sidebar öffnen und in den Einstellungen Entity-IDs setzen

Details: [addon/DOCS.md](addon/DOCS.md)

## Lokale Entwicklung

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r addon/backend/requirements.txt
cd addon/frontend && npm install && npm run build && cd ../..
set DATA_DIR=./data
set ALLOW_ALL_HOSTS=true
set STATIC_DIR=addon/frontend/dist
set PYTHONPATH=addon
python -m uvicorn backend.app.main:app --port 8099
```

UI: http://127.0.0.1:8099

## Tests

```bash
set PYTHONPATH=addon
pytest addon/backend/tests -q
```

Algorithmus-Referenz (Excel): [ABRECHNUNGSALGORITHMUS.md](ABRECHNUNGSALGORITHMUS.md)
