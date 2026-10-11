from __future__ import annotations

from typing import Any

from ..models import AllocationResult, Method, Scope


class FernwaermeInput:
    """Deltas over the billing period."""

    def __init__(
        self,
        *,
        wmz_eg: float,
        wmz_1og: float,
        wmz_2og: float,
        wmz_gesamt: float,
        ww_eg: float,
        ww_1og: float | None,
        ww_2og: float,
        ww_gesamt: float,
        ww_1og_residual: bool = True,
    ):
        self.wmz_eg = wmz_eg
        self.wmz_1og = wmz_1og
        self.wmz_2og = wmz_2og
        self.wmz_gesamt = wmz_gesamt
        self.ww_eg = ww_eg
        self.ww_2og = ww_2og
        self.ww_gesamt = ww_gesamt
        if ww_1og_residual:
            self.ww_1og = ww_gesamt - ww_eg - ww_2og
        else:
            if ww_1og is None:
                raise ValueError("WW 1OG-Zähler erforderlich wenn Restregel deaktiviert")
            self.ww_1og = ww_1og


def allocate_fernwaerme(
    amount: float,
    data: FernwaermeInput,
) -> AllocationResult:
    waerme_hz = data.wmz_eg + data.wmz_1og + data.wmz_2og
    waerme_ww = data.wmz_gesamt - waerme_hz

    if data.wmz_gesamt <= 0:
        raise ValueError("WMZ-Gesamtverbrauch muss > 0 sein")
    if waerme_hz <= 0:
        raise ValueError("Heizungsverbrauch muss > 0 sein")
    if data.ww_gesamt <= 0:
        raise ValueError("WW-Gesamtverbrauch (m³) muss > 0 sein")
    if waerme_ww < 0:
        raise ValueError(
            "Wärmemenge WW negativ: WMZ-Gesamt < Summe Wohnungs-WMZ — Zählerstände prüfen"
        )

    anteil_hz = waerme_hz / data.wmz_gesamt
    anteil_ww = waerme_ww / data.wmz_gesamt
    kosten_hz = amount * anteil_hz
    kosten_ww = amount * anteil_ww

    share_hz = {
        "EG": data.wmz_eg / waerme_hz,
        "1OG": data.wmz_1og / waerme_hz,
        "2OG": data.wmz_2og / waerme_hz,
    }
    share_ww = {
        "EG": data.ww_eg / data.ww_gesamt,
        "1OG": data.ww_1og / data.ww_gesamt,
        "2OG": data.ww_2og / data.ww_gesamt,
    }

    amounts = {
        u: round(kosten_hz * share_hz[u] + kosten_ww * share_ww[u], 2)
        for u in ("EG", "1OG", "2OG")
    }
    drift = round(amount - sum(amounts.values()), 2)
    if drift:
        amounts["2OG"] = round(amounts["2OG"] + drift, 2)

    total_shares = {u: amounts[u] / amount for u in amounts}

    details: dict[str, Any] = {
        "waerme_hz_kwh": waerme_hz,
        "waerme_ww_kwh": waerme_ww,
        "wmz_gesamt_kwh": data.wmz_gesamt,
        "anteil_hz": anteil_hz,
        "anteil_ww": anteil_ww,
        "kosten_hz": round(kosten_hz, 2),
        "kosten_ww": round(kosten_ww, 2),
        "share_hz": share_hz,
        "share_ww": share_ww,
        "deltas": {
            "wmz_eg": data.wmz_eg,
            "wmz_1og": data.wmz_1og,
            "wmz_2og": data.wmz_2og,
            "wmz_gesamt": data.wmz_gesamt,
            "ww_eg": data.ww_eg,
            "ww_1og": data.ww_1og,
            "ww_2og": data.ww_2og,
            "ww_gesamt": data.ww_gesamt,
        },
    }

    return AllocationResult(
        method=Method.VERBRAUCH,
        scope=Scope.FERNWAERME,
        amount=amount,
        amounts=amounts,
        shares=total_shares,
        details=details,
    )
