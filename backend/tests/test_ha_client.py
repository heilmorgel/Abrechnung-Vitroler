from datetime import datetime, timezone

import pytest

from backend.app.ha_client import MockHaClient
from backend.app.models import MissingReadingError


@pytest.mark.asyncio
async def test_delta_from_history():
    series = {
        "sensor.wmz_eg": [
            (datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0),
            (datetime(2024, 2, 1, tzinfo=timezone.utc), 150.0),
        ]
    }
    ha = MockHaClient(series)
    points, interp = await ha.get_deltas(
        {"wmz_eg": "sensor.wmz_eg"},
        datetime(2024, 1, 1).date(),
        datetime(2024, 2, 1).date(),
        allow_interpolation=False,
    )
    assert points["wmz_eg"].delta == 50.0
    assert interp is False


@pytest.mark.asyncio
async def test_missing_asks_for_interpolation():
    ha = MockHaClient({"sensor.x": []})
    with pytest.raises(MissingReadingError) as exc:
        await ha.get_deltas(
            {"wmz_eg": "sensor.x"},
            datetime(2024, 1, 1).date(),
            datetime(2024, 2, 1).date(),
            allow_interpolation=False,
        )
    assert "Interpolation" in exc.value.message


@pytest.mark.asyncio
async def test_interpolation_when_gap_outside_default_lookback():
    """Reading before target is older than 90d lookback; wider 365d window interpolates."""
    series = {
        "sensor.wmz_eg": [
            # Outside 90d lookback from 2020-02-01, but inside 365d wider window
            (datetime(2019, 6, 1, tzinfo=timezone.utc), 0.0),
            (datetime(2020, 3, 1, tzinfo=timezone.utc), 100.0),
        ]
    }
    ha = MockHaClient(series)
    reading = await ha.state_at(
        "sensor.wmz_eg",
        datetime(2020, 2, 1, tzinfo=timezone.utc),
        allow_interpolation=True,
        role="wmz_eg",
    )
    assert reading.interpolated is True
    assert 0 < reading.value < 100
