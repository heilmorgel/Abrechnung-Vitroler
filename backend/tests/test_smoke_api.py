"""Smoke test: settings + fixed-percent invoice roundtrip without HA meters."""
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import settings


@pytest.mark.asyncio
async def test_health_and_fixed_invoice(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "allow_all_hosts", True)
    monkeypatch.setattr(settings, "static_dir", tmp_path / "missing-static")

    from backend.app import db
    from backend.app.main import app

    await db.init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        settings_body = {
            "scopes": {
                "fernwaerme": {
                    "method": "fix_prozent",
                    "percent": {"EG": 50, "1OG": 25, "2OG": 25},
                },
                "wasser_abwasser": {
                    "method": "fix_prozent",
                    "percent": {"EG": 50, "1OG": 25, "2OG": 25},
                },
                "strom": {
                    "method": "fix_prozent",
                    "percent": {"EG": 40, "1OG": 30, "2OG": 30},
                },
            },
            "entities": {},
            "ww_1og_residual": True,
        }
        r = await client.put("/api/settings", json=settings_body)
        assert r.status_code == 200, r.text

        r = await client.post(
            "/api/invoices/json",
            json={
                "scope": "strom",
                "invoice_date": "2024-06-01",
                "period_start": "2024-01-01",
                "period_end": "2024-03-31",
                "amount": 100,
                "number": "S-1",
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["allocation"]["amounts"]["EG"] == 40.0
        assert data["allocation"]["amounts"]["1OG"] == 30.0
        assert data["allocation"]["amounts"]["2OG"] == 30.0

        r = await client.get("/api/summary")
        assert r.status_code == 200
        assert r.json()["count"] == 1
