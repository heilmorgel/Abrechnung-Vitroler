from __future__ import annotations

from datetime import date

from ..ha_client import HaClient
from ..models import (
    AllocationResult,
    AppSettings,
    MeterReading,
    Method,
    Scope,
)
from .fernwaerme import FernwaermeInput, allocate_fernwaerme
from .fixed import allocate_fixed
from .proportional import allocate_proportional


FERNWAERME_ROLES = [
    "wmz_eg",
    "wmz_1og",
    "wmz_2og",
    "wmz_gesamt",
    "ww_eg",
    "ww_2og",
    "ww_gesamt",
]

WASSER_ROLES = ["wasser_eg", "wasser_1og", "wasser_2og"]
STROM_ROLES = ["strom_eg", "strom_1og", "strom_2og"]


async def allocate(
    *,
    scope: Scope,
    amount: float,
    period_start: date,
    period_end: date,
    app_settings: AppSettings,
    ha: HaClient,
    allow_interpolation: bool = False,
) -> AllocationResult:
    scope_cfg = app_settings.scope_settings(scope)

    if scope_cfg.method == Method.FIX_PROZENT:
        return allocate_fixed(scope, amount, scope_cfg.percent)

    if scope == Scope.FERNWAERME:
        return await _allocate_fernwaerme(
            amount, period_start, period_end, app_settings, ha, allow_interpolation
        )
    if scope == Scope.WASSER_ABWASSER:
        return await _allocate_meter_scope(
            Scope.WASSER_ABWASSER,
            amount,
            period_start,
            period_end,
            app_settings,
            ha,
            WASSER_ROLES,
            {"wasser_eg": "EG", "wasser_1og": "1OG", "wasser_2og": "2OG"},
            allow_interpolation,
        )
    if scope == Scope.STROM:
        return await _allocate_meter_scope(
            Scope.STROM,
            amount,
            period_start,
            period_end,
            app_settings,
            ha,
            STROM_ROLES,
            {"strom_eg": "EG", "strom_1og": "1OG", "strom_2og": "2OG"},
            allow_interpolation,
        )
    raise ValueError(f"Unbekannter Scope: {scope}")


async def _readings_for_roles(
    ha: HaClient,
    entities: dict[str, str],
    roles: list[str],
    period_start: date,
    period_end: date,
    allow_interpolation: bool,
) -> tuple[dict[str, float], list[MeterReading], bool]:
    mapping: dict[str, str] = {}
    missing_config: list[str] = []
    for role in roles:
        eid = entities.get(role, "")
        if not eid:
            missing_config.append(role)
        else:
            mapping[role] = eid
    if missing_config:
        raise ValueError(
            "Entity-Mapping unvollständig für: " + ", ".join(missing_config)
        )

    points, interpolated = await ha.get_deltas(
        mapping, period_start, period_end, allow_interpolation=allow_interpolation
    )

    deltas = {role: points[role].delta for role in roles}
    readings_out: list[MeterReading] = []
    for role, p in points.items():
        readings_out.append(p.start)
        readings_out.append(p.end)
    return deltas, readings_out, interpolated


async def _allocate_fernwaerme(
    amount: float,
    period_start: date,
    period_end: date,
    app_settings: AppSettings,
    ha: HaClient,
    allow_interpolation: bool,
) -> AllocationResult:
    entities = app_settings.entities.model_dump()
    roles = list(FERNWAERME_ROLES)
    if not app_settings.ww_1og_residual:
        roles.append("ww_1og")

    deltas, readings, interpolated = await _readings_for_roles(
        ha, entities, roles, period_start, period_end, allow_interpolation
    )

    data = FernwaermeInput(
        wmz_eg=deltas["wmz_eg"],
        wmz_1og=deltas["wmz_1og"],
        wmz_2og=deltas["wmz_2og"],
        wmz_gesamt=deltas["wmz_gesamt"],
        ww_eg=deltas["ww_eg"],
        ww_1og=deltas.get("ww_1og"),
        ww_2og=deltas["ww_2og"],
        ww_gesamt=deltas["ww_gesamt"],
        ww_1og_residual=app_settings.ww_1og_residual,
    )
    result = allocate_fernwaerme(amount, data)
    result.readings = readings
    result.interpolated = interpolated
    return result


async def _allocate_meter_scope(
    scope: Scope,
    amount: float,
    period_start: date,
    period_end: date,
    app_settings: AppSettings,
    ha: HaClient,
    roles: list[str],
    role_to_unit: dict[str, str],
    allow_interpolation: bool,
) -> AllocationResult:
    entities = app_settings.entities.model_dump()
    deltas, readings, interpolated = await _readings_for_roles(
        ha, entities, roles, period_start, period_end, allow_interpolation
    )
    consumption = {role_to_unit[r]: deltas[r] for r in roles}
    result = allocate_proportional(scope, amount, consumption)
    result.readings = readings
    result.interpolated = interpolated
    return result
