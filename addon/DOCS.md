# Abrechnung Vitroler

Kondominiums-Abrechnung für **Fernwärme**, **Wasser/Abwasser** und **Strom** mit Aufteilung auf EG, 1. OG und 2. OG.

## Funktionen

- Rechnungen erfassen (Datum, Bezugszeitraum, Betrag, optional Datei-Upload)
- Zwei Methoden **pro Scope** (in den Einstellungen):
  - **Verbrauchsbasiert** — Fernwärme nach Excel-Logik (WMZ/WW); Wasser und Strom proportional nach Wohnungszählern
  - **Fixe Prozente** — z. B. EG 50 %, 1. OG 25 %, 2. OG 25 %
- Zählerstände aus Home-Assistant-Sensoren oder Helfer-Variablen (`input_number`) über die History-API
- Fehlende Stände: Abbruch mit Hinweis; optional lineare Interpolation

## Installation (lokales Add-on)

1. Frontend bauen und Add-on-Kontext vorbereiten (auf dem Entwicklungsrechner):

```bash
cd frontend && npm install && npm run build && cd ..
python scripts/prepare_addon.py
```

2. Den Ordner `addon` nach `/addons/abrechnung_vitroler` auf dem HA-Host kopieren (Inhalt von `addon/`, inkl. `app/`).

3. In Home Assistant: **Einstellungen → Add-ons → Add-on-Store → Menü → Lokale Add-ons neu laden**.

4. **Abrechnung Vitroler** installieren und starten. Sidebar-Eintrag bzw. „OPEN WEB UI“ (Ingress).

## Konfiguration in der App

1. **Einstellungen** öffnen.
2. Pro Scope Methode und ggf. Prozentwerte setzen.
3. Entity-IDs zuordnen, z. B.:
   - `sensor.wmz_eg`, `sensor.wmz_1og`, `sensor.wmz_2og`, `sensor.wmz_gesamt`
   - `sensor.ww_eg`, `sensor.ww_2og`, `sensor.ww_gesamt` (1. OG optional bei Restregel)
   - Wasser: `sensor.wasser_eg` / `_1og` / `_2og`
   - Strom: `sensor.strom_eg` / `_1og` / `_2og`
4. Speichern, danach Rechnung anlegen.

## Fernwärme-Logik (Kurz)

1. Verbrauch = Stand(Periodenende) − Stand(Periodenanfang)
2. Wärme Heizung = WMZ EG + 1OG + 2OG; Wärme WW = WMZ Gesamt − Heizung
3. WW 1OG = WW Gesamt − EG − 2OG (Standard, abschaltbar)
4. Rechnungsbetrag nach kWh-Anteilen HZ/WW, dann HZ nach WMZ-Wohnung, WW nach m³

## Lokale Entwicklung

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
# optional: .env mit HA_URL und HA_TOKEN (Long-Lived Access Token)
set DATA_DIR=./data
set ALLOW_ALL_HOSTS=true
cd frontend && npm install && npm run build && cd ..
set STATIC_DIR=frontend/dist
python -m uvicorn backend.app.main:app --reload --port 8099
```

Tests:

```bash
pytest backend/tests -q
```

## Datenschutz

Rechnungsdateien und die SQLite-Datenbank liegen unter `/data` im Add-on (persistent).
