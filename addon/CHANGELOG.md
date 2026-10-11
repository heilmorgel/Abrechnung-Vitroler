# Changelog

## 0.1.1

- Fix: Add-on ist selbstständig baubar (Backend/Frontend im Add-on-Ordner, UI-Build im Docker-Image)
- Kein `prepare_addon`-Schritt mehr nötig für die Installation aus GitHub

## 0.1.0

- Erstversion: Ingress-UI, SQLite, Rechnungs-Upload
- Scopes Fernwärme, Wasser/Abwasser, Strom
- Methoden verbrauchsbasiert und fixe Prozente
- Fernwärme-Algorithmus nach Excel Vitroler
- HA History für Zählerstände, optionale Interpolation
