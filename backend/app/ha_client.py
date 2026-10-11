from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from .config import settings
from .models import MeterReading, MissingReadingError


@dataclass
class PeriodPoints:
    start: MeterReading
    end: MeterReading

    @property
    def delta(self) -> float:
        return self.end.value - self.start.value


class HaClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = (base_url or settings.ha_url).rstrip("/")
        self.token = token if token is not None else settings.ha_token
        self._client = client

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client:
            return self._client
        return httpx.AsyncClient(base_url=self.base_url, headers=self._headers(), timeout=60.0)

    async def history_period(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        """Fetch recorder history for entity between start and end (inclusive buffer)."""
        # HA history API: /api/history/period/<timestamp>?filter_entity_id=
        start_iso = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        params = {
            "filter_entity_id": entity_id,
            "end_time": end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "significant_changes_only": "0",
        }
        owns_client = self._client is None
        client = await self._get_client()
        try:
            resp = await client.get(f"/api/history/period/{start_iso}", params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return []
            return data[0]
        finally:
            if owns_client:
                await client.aclose()

    async def state_at(
        self,
        entity_id: str,
        at: datetime,
        *,
        lookback_days: int = 90,
        allow_interpolation: bool = False,
        role: str = "",
    ) -> MeterReading:
        """Last known numeric state at or before `at`. Optionally interpolate."""
        window_start = at - timedelta(days=lookback_days)
        window_end = at + timedelta(days=1)
        history = await self.history_period(entity_id, window_start, window_end)

        before: tuple[datetime, float] | None = None
        after: tuple[datetime, float] | None = None

        for item in history:
            state = item.get("state")
            if state in (None, "unknown", "unavailable"):
                continue
            try:
                value = float(state)
            except (TypeError, ValueError):
                continue
            ts = datetime.fromisoformat(item["last_changed"].replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts <= at:
                before = (ts, value)
            elif after is None:
                after = (ts, value)

        if before is not None:
            return MeterReading(
                entity_id=entity_id,
                role=role,
                at=before[0],
                value=before[1],
                interpolated=False,
            )

        if allow_interpolation and after is not None:
            # No reading before: cannot truly interpolate without a prior point.
            # Use nearest after only if also have a later? Without before, refuse.
            pass

        if allow_interpolation:
            # Try wider history for points around `at`
            wider = await self.history_period(
                entity_id, at - timedelta(days=365), at + timedelta(days=365)
            )
            pts: list[tuple[datetime, float]] = []
            for item in wider:
                state = item.get("state")
                try:
                    value = float(state)
                except (TypeError, ValueError):
                    continue
                ts = datetime.fromisoformat(item["last_changed"].replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                pts.append((ts, value))
            pts.sort(key=lambda x: x[0])
            prev = next((p for p in reversed(pts) if p[0] <= at), None)
            nxt = next((p for p in pts if p[0] > at), None)
            if prev and nxt and nxt[0] != prev[0]:
                ratio = (at - prev[0]).total_seconds() / (nxt[0] - prev[0]).total_seconds()
                value = prev[1] + ratio * (nxt[1] - prev[1])
                return MeterReading(
                    entity_id=entity_id,
                    role=role,
                    at=at,
                    value=value,
                    interpolated=True,
                )
            if prev:
                return MeterReading(
                    entity_id=entity_id,
                    role=role,
                    at=prev[0],
                    value=prev[1],
                    interpolated=False,
                )

        raise MissingReadingError([f"{role or entity_id}@{at.date().isoformat()}"])

    async def get_deltas(
        self,
        role_to_entity: dict[str, str],
        period_start: date,
        period_end: date,
        *,
        allow_interpolation: bool = False,
    ) -> tuple[dict[str, PeriodPoints], bool]:
        start_dt = datetime.combine(period_start, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        # period_end inclusive as end-of-day
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )

        result: dict[str, PeriodPoints] = {}
        missing: list[str] = []
        any_interp = False

        for role, entity_id in role_to_entity.items():
            try:
                start_r = await self.state_at(
                    entity_id,
                    start_dt,
                    allow_interpolation=allow_interpolation,
                    role=f"{role}_start",
                )
                end_r = await self.state_at(
                    entity_id,
                    end_dt,
                    allow_interpolation=allow_interpolation,
                    role=f"{role}_end",
                )
                if start_r.interpolated or end_r.interpolated:
                    any_interp = True
                result[role] = PeriodPoints(start=start_r, end=end_r)
            except MissingReadingError as exc:
                missing.extend(exc.missing)

        if missing:
            raise MissingReadingError(missing)

        return result, any_interp


class MockHaClient(HaClient):
    """In-memory HA client for tests / offline preview with provided readings."""

    def __init__(self, series: dict[str, list[tuple[datetime, float]]]):
        super().__init__(base_url="http://mock", token="")
        self.series = series

    async def history_period(
        self, entity_id: str, start: datetime, end: datetime
    ) -> list[dict[str, Any]]:
        out = []
        for ts, value in self.series.get(entity_id, []):
            if start <= ts <= end:
                out.append(
                    {
                        "state": str(value),
                        "last_changed": ts.isoformat().replace("+00:00", "Z"),
                    }
                )
        return out
