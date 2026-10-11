from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from .config import settings
from .models import AppSettings, Scope


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    number TEXT NOT NULL DEFAULT '',
    invoice_date TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    file_path TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL UNIQUE,
    result_json TEXT NOT NULL,
    calculated_at TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);
"""


def _db_path() -> Path:
    path = settings.data_dir / "abrechnung.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "invoices").mkdir(parents=True, exist_ok=True)
    return path


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    db = await aiosqlite.connect(_db_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    async with connect() as db:
        await db.executescript(SCHEMA)
        cur = await db.execute("SELECT data FROM settings WHERE id = 1")
        row = await cur.fetchone()
        if not row:
            default = AppSettings().model_dump(mode="json", by_alias=True)
            await db.execute(
                "INSERT INTO settings (id, data) VALUES (1, ?)",
                (json.dumps(default, ensure_ascii=False),),
            )
        await db.commit()


async def get_settings() -> AppSettings:
    async with connect() as db:
        cur = await db.execute("SELECT data FROM settings WHERE id = 1")
        row = await cur.fetchone()
        if not row:
            return AppSettings()
        return AppSettings.model_validate_json(row["data"])


async def save_settings(app_settings: AppSettings) -> AppSettings:
    payload = app_settings.model_dump(mode="json", by_alias=True)
    async with connect() as db:
        await db.execute(
            "INSERT INTO settings (id, data) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data",
            (json.dumps(payload, ensure_ascii=False),),
        )
        await db.commit()
    return app_settings


def _row_to_invoice(row: aiosqlite.Row, allocation: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "scope": row["scope"],
        "number": row["number"],
        "invoice_date": date.fromisoformat(row["invoice_date"]),
        "period_start": date.fromisoformat(row["period_start"]),
        "period_end": date.fromisoformat(row["period_end"]),
        "amount": row["amount"],
        "note": row["note"],
        "file_path": row["file_path"],
        "status": row["status"],
        "created_at": datetime.fromisoformat(row["created_at"]),
        "allocation": allocation,
    }


async def list_invoices(scope: Scope | None = None) -> list[dict[str, Any]]:
    async with connect() as db:
        if scope:
            cur = await db.execute(
                "SELECT * FROM invoices WHERE scope = ? ORDER BY invoice_date DESC, id DESC",
                (scope.value,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM invoices ORDER BY invoice_date DESC, id DESC"
            )
        rows = await cur.fetchall()
        result = []
        for row in rows:
            alloc_cur = await db.execute(
                "SELECT result_json FROM allocations WHERE invoice_id = ?",
                (row["id"],),
            )
            alloc_row = await alloc_cur.fetchone()
            alloc = json.loads(alloc_row["result_json"]) if alloc_row else None
            result.append(_row_to_invoice(row, alloc))
        return result


async def get_invoice(invoice_id: int) -> dict[str, Any] | None:
    async with connect() as db:
        cur = await db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        row = await cur.fetchone()
        if not row:
            return None
        alloc_cur = await db.execute(
            "SELECT result_json FROM allocations WHERE invoice_id = ?",
            (invoice_id,),
        )
        alloc_row = await alloc_cur.fetchone()
        alloc = json.loads(alloc_row["result_json"]) if alloc_row else None
        return _row_to_invoice(row, alloc)


async def create_invoice(data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    async with connect() as db:
        cur = await db.execute(
            """
            INSERT INTO invoices
            (scope, number, invoice_date, period_start, period_end, amount, note, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["scope"],
                data.get("number", ""),
                data["invoice_date"],
                data["period_start"],
                data["period_end"],
                data["amount"],
                data.get("note", ""),
                data.get("file_path"),
                data.get("status", "calculated"),
                now,
            ),
        )
        await db.commit()
        invoice_id = cur.lastrowid
    return await get_invoice(invoice_id)  # type: ignore[return-value]


async def update_invoice(invoice_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    existing = await get_invoice(invoice_id)
    if not existing:
        return None
    fields = []
    values: list[Any] = []
    for key in ("number", "invoice_date", "period_start", "period_end", "amount", "note", "file_path", "status"):
        if key in data and data[key] is not None:
            fields.append(f"{key} = ?")
            val = data[key]
            if isinstance(val, date):
                val = val.isoformat()
            values.append(val)
    if fields:
        values.append(invoice_id)
        async with connect() as db:
            await db.execute(
                f"UPDATE invoices SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            await db.commit()
    return await get_invoice(invoice_id)


async def delete_invoice(invoice_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        await db.commit()
        return cur.rowcount > 0


async def save_allocation(invoice_id: int, result: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with connect() as db:
        await db.execute(
            """
            INSERT INTO allocations (invoice_id, result_json, calculated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(invoice_id) DO UPDATE SET
              result_json = excluded.result_json,
              calculated_at = excluded.calculated_at
            """,
            (invoice_id, json.dumps(result, ensure_ascii=False, default=str), now),
        )
        await db.execute(
            "UPDATE invoices SET status = ? WHERE id = ?",
            ("calculated", invoice_id),
        )
        await db.commit()
