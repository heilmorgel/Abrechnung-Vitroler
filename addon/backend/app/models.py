from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Scope(str, Enum):
    FERNWAERME = "fernwaerme"
    WASSER_ABWASSER = "wasser_abwasser"
    STROM = "strom"


class Method(str, Enum):
    VERBRAUCH = "verbrauch"
    FIX_PROZENT = "fix_prozent"


UNITS = ("EG", "1OG", "2OG")


class PercentShares(BaseModel):
    EG: float = 50.0
    unit_1og: float = Field(25.0, serialization_alias="1OG", validation_alias="1OG")
    unit_2og: float = Field(25.0, serialization_alias="2OG", validation_alias="2OG")

    model_config = {"populate_by_name": True}

    def as_unit_dict(self) -> dict[str, float]:
        return {"EG": self.EG, "1OG": self.unit_1og, "2OG": self.unit_2og}

    @model_validator(mode="after")
    def sum_100(self) -> PercentShares:
        total = self.EG + self.unit_1og + self.unit_2og
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Prozentanteile müssen 100 ergeben, aktuell {total}")
        return self


class EntityMapping(BaseModel):
    wmz_eg: str = ""
    wmz_1og: str = ""
    wmz_2og: str = ""
    wmz_gesamt: str = ""
    ww_eg: str = ""
    ww_1og: str = ""
    ww_2og: str = ""
    ww_gesamt: str = ""
    wasser_eg: str = ""
    wasser_1og: str = ""
    wasser_2og: str = ""
    strom_eg: str = ""
    strom_1og: str = ""
    strom_2og: str = ""
    strom_gesamt: str = ""


class ScopeSettings(BaseModel):
    method: Method = Method.VERBRAUCH
    percent: PercentShares = Field(default_factory=PercentShares)


def default_scopes() -> dict[str, ScopeSettings]:
    return {
        Scope.FERNWAERME.value: ScopeSettings(method=Method.VERBRAUCH),
        Scope.WASSER_ABWASSER.value: ScopeSettings(method=Method.FIX_PROZENT),
        Scope.STROM.value: ScopeSettings(method=Method.FIX_PROZENT),
    }


class AppSettings(BaseModel):
    scopes: dict[str, ScopeSettings] = Field(default_factory=default_scopes)
    entities: EntityMapping = Field(default_factory=EntityMapping)
    ww_1og_residual: bool = True

    def scope_settings(self, scope: Scope) -> ScopeSettings:
        key = scope.value
        if key not in self.scopes:
            self.scopes[key] = ScopeSettings()
        return self.scopes[key]


class InvoiceCreate(BaseModel):
    scope: Scope
    number: str = ""
    invoice_date: date
    period_start: date
    period_end: date
    amount: float = Field(gt=0)
    note: str = ""
    allow_interpolation: bool = False

    @model_validator(mode="after")
    def end_after_start(self) -> InvoiceCreate:
        if self.period_end < self.period_start:
            raise ValueError("period_end muss >= period_start sein")
        return self


class InvoiceUpdate(BaseModel):
    number: str | None = None
    invoice_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    amount: float | None = Field(default=None, gt=0)
    note: str | None = None
    allow_interpolation: bool | None = None


class InvoiceOut(BaseModel):
    id: int
    scope: Scope
    number: str
    invoice_date: date
    period_start: date
    period_end: date
    amount: float
    note: str
    file_path: str | None
    status: str
    created_at: datetime
    allocation: dict[str, Any] | None = None


class AllocationPreviewRequest(BaseModel):
    scope: Scope
    period_start: date
    period_end: date
    amount: float = Field(gt=0)
    allow_interpolation: bool = False


class MeterReading(BaseModel):
    entity_id: str
    role: str
    at: datetime
    value: float
    interpolated: bool = False


class MissingReadingError(Exception):
    def __init__(self, missing: list[str], message: str | None = None):
        self.missing = missing
        self.message = message or (
            "Zählerstände fehlen an den Periodengrenzen. "
            "Soll eine lineare Interpolation zwischen bekannten Ständen verwendet werden?"
        )
        super().__init__(self.message)


class AllocationResult(BaseModel):
    method: Method
    scope: Scope
    amount: float
    amounts: dict[str, float]
    shares: dict[str, float]
    details: dict[str, Any] = Field(default_factory=dict)
    readings: list[MeterReading] = Field(default_factory=list)
    interpolated: bool = False
