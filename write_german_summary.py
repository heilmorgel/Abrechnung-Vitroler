"""Write structured German billing algorithm summary from analysis findings."""
from pathlib import Path

OUT = Path(r"d:\Coding\Abrechnung-Vitroler\ABRECHNUNGSALGORITHMUS.md")

OUT.write_text(r'''# Abrechnungsalgorithmus Kondominium Vitroler

Quelle: `Abrechnung_KondominiumVitroler_V2.xlsx` (Sheet: **Verrechnung**, 85×111)

**Kernaussage:** Die Datei enthält *ausschließlich* die Aufteilung der **Fernwärme-Rechnungen (Stadtwerke)** auf drei Wohnungen anhand von Wärmemengenzählern und Warmwasserzählern. Es gibt **keine** Abwasser-Abrechnung, **keine** Millessimale/Tausendstel, **keine** sonstigen Hauskosten (Müll, Versicherung, Strom Allgemein etc.) in dieser Datei.

---

## 1. Beteiligte Parteien / Einheiten

| Code | Bedeutung |
|------|-----------|
| **EG** | Erdgeschoss-Wohnung |
| **1OG** | 1. Obergeschoss |
| **2OG** | 2. Obergeschoss |
| **Gesamt** | Gebäude-/Hauptzähler |

Keine Eigentümernamen in der Datei – nur Stockwerks-Codes.

---

## 2. Kostentypen (in dieser Datei)

| Kostentyp | Verwendet zur Abrechnung? | Bemerkung |
|-----------|---------------------------|-----------|
| **Fernwärme** (Stadtwerke-Rechnung) | Ja – einziger abgerechneter Kostenblock | Input: Rechnungsbetrag € |
| davon **Heizungsanteil** | Ja | aus WMZ-Differenz abgeleitet |
| davon **Warmwassererzeugung** | Ja | Restwärme = WMZ Gesamt − Summe Wohnung-WMZ |
| Kaltwasser (KW) | Nein (nur Verbrauchsstatistik) | Monatswerte werden berechnet, fließen nicht in €-Split |
| Zirkulation | Nein | historische Zählerstände, Verbrauchszeilen leer |
| Abwasser | **Nicht vorhanden** | — |
| Sonstige Kondominiumskosten | **Nicht vorhanden** | — |

Zusatz am unteren Rand (manuell, nicht systematisch): Betrag `168.93/2` je für EG und 2OG (nicht 1OG) – wirkt wie eine ad-hoc-Nebenposition, nicht Teil der Kernformel.

---

## 3. Blattstruktur

Eine Spalte = ein Kalendermonat (E … DG, Dez 2018 → Okt 2027).

| Zeilen | Inhalt | Typ |
|--------|--------|-----|
| 1 | Monatsdatum (Anzeige „mmmm yyyy“) | Input |
| 2 | Datum Ablesung | Input (manchmal `---`, manchmal leer) |
| 3–6 | Zählerstände WMZ EG/1OG/2OG/Gesamt [kWh] | Input (selten Interpolation) |
| 8–11 | Zählerstände WW EG/1OG/2OG/Gesamt [m³] | Input (selten Interpolation) |
| 12–13 | Zählerstände Zirkulation 1OG/2OG | Input (unvollständig) |
| 14–17 | Zählerstände KW EG/1OG/2OG/Gesamt [m³] | Input (selten Interpolation) |
| 19–36 | Monatsverbräuche | **berechnet** |
| 38–43 | Rechnungs-Metadaten / Periode | gemischt |
| 44–69 | Periodenverbrauch, Anteile, Preise | **berechnet** |
| 71–74 | Zu zahlen je Wohnung | **berechnet** |

Rechnungs-Trigger: Wenn Zeile 40 (`Rechnungsbetrag`) in einer Spalte gefüllt ist, gilt diese Spalte als **Abrechnungsspalte** (27 Rechnungen 2019–2026).

---

## 4. Zähler → Monatsverbrauch

Für Monatsspalte `M` und Folgemonat `M+1`:

```
# Wärmemengenzähler (Wohnungen + Gesamt)
delta_WMZ_EG(M)      = Stand_WMZ_EG(M+1)      - Stand_WMZ_EG(M)
delta_WMZ_1OG(M)     = Stand_WMZ_1OG(M+1)     - Stand_WMZ_1OG(M)
delta_WMZ_2OG(M)     = Stand_WMZ_2OG(M+1)     - Stand_WMZ_2OG(M)
delta_WMZ_Gesamt(M)  = Stand_WMZ_Gesamt(M+1)  - Stand_WMZ_Gesamt(M)

# Heizung vs. Warmwasser-Wärme (kWh)
Waerme_Heizung(M) = delta_WMZ_EG(M) + delta_WMZ_1OG(M) + delta_WMZ_2OG(M)
Waerme_WW(M)      = delta_WMZ_Gesamt(M) - Waerme_Heizung(M)
# Annahme: Wohnung-WMZ messen nur Heizung; Gesamt-WMZ = Heizung + WW-Erzeugung
```

```
# Warmwasser m³
delta_WW_EG(M)     = Stand_WW_EG(M+1)     - Stand_WW_EG(M)
delta_WW_2OG(M)    = Stand_WW_2OG(M+1)    - Stand_WW_2OG(M)
delta_WW_Gesamt(M) = Stand_WW_Gesamt(M+1) - Stand_WW_Gesamt(M)

# SPEZIALREGEL 1OG: nicht aus eigenem Zählerdifferenzen, sondern Rest!
delta_WW_1OG(M) = delta_WW_Gesamt(M) - delta_WW_EG(M) - delta_WW_2OG(M)
# (Kommentar in Excel: „WW Gesamt - EG - 2.OG“)
```

```
# Kaltwasser m³ (nur Statistik)
delta_KW_EG(M)  = Stand_KW_EG(M+1)  - Stand_KW_EG(M)
delta_KW_1OG(M) = Stand_KW_1OG(M+1) - Stand_KW_1OG(M)
delta_KW_2OG(M) = Stand_KW_2OG(M+1) - Stand_KW_2OG(M)

# KW-Gesamt-Verbrauch = Hauptzähler-Differenz minus WW-Gesamt
delta_KW_Gesamt_netto(M) = (Stand_KW_Gesamt(M+1) - Stand_KW_Gesamt(M)) - delta_WW_Gesamt(M)
```

### Fehlende Ablesungen / Interpolation (Input-Formeln)

Wenn Zwischenstände fehlen, werden Stände geschätzt, z. B.:

```
# lineare Interpolation zwischen zwei bekannten Ständen A und B zum Zeitpunkt t
Stand(t) = Stand(A) + (t_ablesung - t_A) * (Stand(B) - Stand(A)) / (t_B - t_A)

# oder Anteil einer Spanne:
Stand = Stand_start + f * (Stand_ende - Stand_start)   # f ∈ {0.4, 0.8, …}

# oder Mittelwert / Viertel-Schritte:
Stand = AVERAGE(links, rechts)
Stand = (Stand_ende - Stand_start)/4 + Bezugspunkt
```

---

## 5. Abrechnungsperiode ↔ Zähler

Pro Rechnungsspalte `R`:

| Feld | Zeile | Rolle |
|------|-------|-------|
| Rechnungsnummer | 39 | Input (Text) |
| Rechnungsbetrag € | 40 | **Input** – steuert, ob abgerechnet wird |
| Rechnungsperiode Stadtwerke | 41 | Input (Label, informativ) |
| Verrechnungsperiode Beginn | 42 | **Input** (manuell!) |
| Verrechnungsperiode Ende | 43 | meist. `= Monatsspalte.Datum` wenn Betrag gesetzt |

Periodensumme (Excel-Idee mit INDEX/MATCH):

```
# Alle Monatsspalten M mit: period_begin <= Monat(M) <= period_end
# (Excel: SUM von Spalte MATCH(begin) bis aktueller Rechnungsspalte)

Verbrauch_HZ_gesamt_Periode   = Σ Waerme_Heizung(M)      für M in Periode
Verbrauch_WW_Waerme_Periode   = Σ Waerme_WW(M)           für M in Periode
Verbrauch_WMZ_Gesamt_Periode  = Σ delta_WMZ_Gesamt(M)    für M in Periode

Verbrauch_HZ_EG_Periode       = Σ delta_WMZ_EG(M)
Verbrauch_HZ_1OG_Periode      = Σ delta_WMZ_1OG(M)
Verbrauch_HZ_2OG_Periode      = Σ delta_WMZ_2OG(M)

Verbrauch_WW_EG_Periode       = Σ delta_WW_EG(M)
Verbrauch_WW_1OG_Periode      = Σ delta_WW_1OG(M)   # Residual-Regel gilt monatlich
Verbrauch_WW_2OG_Periode      = Σ delta_WW_2OG(M)
Verbrauch_WW_m3_Periode       = Σ delta_WW_Gesamt(M)
```

**Wichtig:** Die Verbrauchsperiode wird über `Verrechnungsperiode Beginn` (manuell) und die Rechnungsspalte als Ende gesteuert – nicht zwingend identisch mit dem Stadtwerke-Text in Zeile 41. Es gibt dokumentierte Inkonsistenzen (z. B. Label „März–Oktober 2019“ vs. Beginndatum 2020-03-01).

---

## 6. Kostenaufteilung (Kernalgorithmus)

```
Rechnung = Rechnungsbetrag_EUR   # Input

# 1) Split Fernwärme in Heizung vs. Warmwasser-Erzeugung (nach kWh)
Anteil_HZ  = Verbrauch_HZ_gesamt_Periode  / Verbrauch_WMZ_Gesamt_Periode
Anteil_WW  = Verbrauch_WW_Waerme_Periode  / Verbrauch_WMZ_Gesamt_Periode
# → Anteil_HZ + Anteil_WW ≈ 1

Kosten_HZ = Anteil_HZ * Rechnung
Kosten_WW = Anteil_WW * Rechnung   # „Preis Warmwassererzeugung“

# 2) Heizung auf Wohnungen nach WMZ-Wohnungsverbrauch
Anteil_HZ_EG  = Verbrauch_HZ_EG_Periode  / Verbrauch_HZ_gesamt_Periode
Anteil_HZ_1OG = Verbrauch_HZ_1OG_Periode / Verbrauch_HZ_gesamt_Periode
Anteil_HZ_2OG = Verbrauch_HZ_2OG_Periode / Verbrauch_HZ_gesamt_Periode
# → Summe ≈ 1

Preis_HZ_EG  = Anteil_HZ_EG  * Kosten_HZ
Preis_HZ_1OG = Anteil_HZ_1OG * Kosten_HZ
Preis_HZ_2OG = Anteil_HZ_2OG * Kosten_HZ

# 3) Warmwasser-Kosten auf Wohnungen nach m³-WW-Verbrauch
Anteil_WW_EG  = Verbrauch_WW_EG_Periode  / Verbrauch_WW_m3_Periode
Anteil_WW_1OG = Verbrauch_WW_1OG_Periode / Verbrauch_WW_m3_Periode
Anteil_WW_2OG = Verbrauch_WW_2OG_Periode / Verbrauch_WW_m3_Periode
# → Summe ≈ 1

Preis_WW_EG  = Anteil_WW_EG  * Kosten_WW
Preis_WW_1OG = Anteil_WW_1OG * Kosten_WW
Preis_WW_2OG = Anteil_WW_2OG * Kosten_WW

# 4) Endbetrag je Wohnung
zu_zahlen_EG  = Preis_HZ_EG  + Preis_WW_EG
zu_zahlen_1OG = Preis_HZ_1OG + Preis_WW_1OG
zu_zahlen_2OG = Preis_HZ_2OG + Preis_WW_2OG
# → Summe ≈ Rechnung
```

### Pseudocode (App)

```python
def allocate_district_heating(invoice_eur, monthly):
    """monthly: list of months in billing period with deltas already computed."""
    hz = sum(m.waerme_heizung for m in monthly)
    ww_kwh = sum(m.waerme_ww for m in monthly)
    total_kwh = sum(m.delta_wmz_gesamt for m in monthly)  # == hz + ww_kwh

    cost_hz = invoice_eur * (hz / total_kwh)
    cost_ww = invoice_eur * (ww_kwh / total_kwh)

    hz_eg  = sum(m.delta_wmz_eg  for m in monthly)
    hz_1og = sum(m.delta_wmz_1og for m in monthly)
    hz_2og = sum(m.delta_wmz_2og for m in monthly)

    ww_eg  = sum(m.delta_ww_eg  for m in monthly)
    ww_1og = sum(m.delta_ww_1og for m in monthly)  # residual monthly
    ww_2og = sum(m.delta_ww_2og for m in monthly)
    ww_m3  = sum(m.delta_ww_gesamt for m in monthly)

    return {
        "EG":  cost_hz * hz_eg/hz   + cost_ww * ww_eg/ww_m3,
        "1OG": cost_hz * hz_1og/hz  + cost_ww * ww_1og/ww_m3,
        "2OG": cost_hz * hz_2og/hz  + cost_ww * ww_2og/ww_m3,
    }
```

---

## 7. Fixe Anteile / Sonderregeln

| Regel | Detail |
|-------|--------|
| Millessimale / % Fix | **Keine** |
| WW 1OG | **Restmenge**: Gesamt − EG − 2OG (Zähler 1OG wird für Verbrauch nicht direkt verwendet) |
| Wärme-Split | Wohnung-WMZ = Heizung; Differenz zu Gesamt-WMZ = WW-Wärme |
| KW-Gesamt netto | KW-Hauptzähler-Delta − WW-Gesamt-Delta |
| Zirkulation | nicht in Kostenformel |
| Abrechnung nur wenn | `Rechnungsbetrag` gesetzt |
| Periodenanfang | **manuell** je Rechnung |
| Interpolation | ad-hoc bei fehlenden Ablesungen |

---

## 8. Input- vs. berechnete Zellen

### Inputs (App/HA müssen liefern oder Nutzer erfassen)

- Monatsspalten-Datum
- Ablesedatum
- Zählerstände: WMZ×4, WW×4, KW×4 (Zirkulation optional/historisch)
- Pro Rechnung: Nummer, Betrag €, Stadtwerke-Periodenlabel, **Verrechnungsbeginn**
- gelegentlich manuelles Periodenende

### Berechnet

- alle Monatsdifferenzen (Zeilen 20–36)
- Periodensummen, Anteile, Preise, „zu bezahlen“ (44–74)

---

## 9. Ambiguities / Lücken für Home-Assistant-Automation

1. **Kein Abwasser / keine Wasserrechnung** in dieser Datei – nur Fernwärme. KW/WW-m³ dienen (WW) dem Wärmekosten-Split bzw. (KW) der Statistik.
2. **WW-1OG-Restregel:** Wenn HA alle drei WW-Zähler liefert, widerspricht die Excel-Logik dem 1OG-Zähler – App muss entscheiden: Restregel beibehalten oder echte Zähler nutzen.
3. **Periodengrenzen manuell** und teilweise inkonsistent zum Stadtwerke-Text; Automation braucht klare Regel (Rechnungseingang + Zählerstände an Periodengrenzen).
4. **Ablesezeitpunkt ≠ Monatsanfang:** Zeile 2 weicht oft vom Spaltenmonat ab; Verbrauch = Stand(nächster Monat) − Stand(dieser), unabhängig vom Kalendertag – bei HA besser zeitgestempelte Stände und Delta über echte Periodengrenzen.
5. **Fehlende Ablesungen:** Excel interpoliert manuell; HA sollte fehlende Werte flaggen statt still zu interpolieren (oder klare Interpolationspolitik).
6. **Zirkulationszähler** unvollständig und ungenutzt – für Abrechnung irrelevant.
7. **WMZ-Gesamt vs. Summe Wohnungen:** Negative oder unplausible `Waerme_WW` möglich bei Zählerfehlern/Reset – Validierung nötig.
8. **Zählerwechsel/Reset:** Label „- 0“ / „- 0,0“ deutet auf Startwerte hin; kein explizites Reset-Handling.
9. **Ad-hoc-Zusatzkosten** (unten `168.93/2` nur EG+2OG) sind nicht algorithmisiert.
10. **Keine Eigentümer-/IBAN-Zuordnung**, keine Vorauszahlungen/Salden in dieser Datei.
11. **Frühe Excel-Formeln** für Periodensumme Heizung (Zeile 44) weichen teils vom Muster der anderen Zeilen ab – bei Reimplementation saubere Periodensumme verwenden, nicht blind Formeln kopieren.

### Empfohlene HA-Sensoren für diese Logik

| Sensor | Einheit | Pflicht |
|--------|---------|---------|
| WMZ EG, 1OG, 2OG, Gesamt | kWh (kumulativ) | ja |
| WW EG, 2OG, Gesamt | m³ (kumulativ) | ja |
| WW 1OG | m³ | optional (Excel ignoriert für Verbrauch) |
| KW EG, 1OG, 2OG, Gesamt | m³ | nur wenn KW-Statistik gewünscht |
| Fernwärme-Rechnungsbetrag + Perioden | € / Daten | ja (manuell oder OCR/Import) |

---

## 10. Kurz: Was eine App implementieren muss

1. Monatliche (oder periodenbezogene) Zählerstände speichern.
2. Deltas berechnen; WW-1OG als Rest; Heizung/WW-Wärme aus WMZ splitten.
3. Bei neuer Stadtwerke-Rechnung: Betrag + Verrechnungsintervall setzen.
4. Deltas über Intervall summieren.
5. Rechnung proportional kWh(HZ)/kWh(Gesamt) und kWh(WW)/kWh(Gesamt) splitten.
6. HZ-Kosten nach WMZ-Wohnung, WW-Kosten nach m³-WW verteilen.
7. Pro Wohnung: HZ-Anteil + WW-Anteil = Zahlbetrag.

''', encoding='utf-8')
print(f"Wrote {OUT}")
