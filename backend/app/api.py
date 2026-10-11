from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from . import db
from .calc import allocate
from .config import settings
from .ha_client import HaClient
from .models import (
    AllocationPreviewRequest,
    AllocationResult,
    AppSettings,
    InvoiceCreate,
    InvoiceOut,
    InvoiceUpdate,
    MissingReadingError,
    Scope,
)

router = APIRouter(prefix="/api")


def ha_client() -> HaClient:
    return HaClient()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/settings", response_model=AppSettings)
async def get_settings() -> AppSettings:
    return await db.get_settings()


@router.put("/settings", response_model=AppSettings)
async def put_settings(body: AppSettings) -> AppSettings:
    return await db.save_settings(body)


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(scope: Scope | None = Query(default=None)) -> list[InvoiceOut]:
    rows = await db.list_invoices(scope)
    return [InvoiceOut.model_validate(r) for r in rows]


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(invoice_id: int) -> InvoiceOut:
    row = await db.get_invoice(invoice_id)
    if not row:
        raise HTTPException(404, "Rechnung nicht gefunden")
    return InvoiceOut.model_validate(row)


@router.post("/allocate/preview")
async def preview_allocation(body: AllocationPreviewRequest) -> dict:
    app_settings = await db.get_settings()
    try:
        result = await allocate(
            scope=body.scope,
            amount=body.amount,
            period_start=body.period_start,
            period_end=body.period_end,
            app_settings=app_settings,
            ha=ha_client(),
            allow_interpolation=body.allow_interpolation,
        )
        return result.model_dump(mode="json")
    except MissingReadingError as exc:
        return {
            "error": "missing_readings",
            "message": exc.message,
            "missing": exc.missing,
            "can_interpolate": True,
        }
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Home-Assistant-Zugriff fehlgeschlagen: {exc}") from exc


@router.post("/invoices", response_model=InvoiceOut)
async def create_invoice(
    scope: str = Form(...),
    invoice_date: str = Form(...),
    period_start: str = Form(...),
    period_end: str = Form(...),
    amount: float = Form(...),
    number: str = Form(""),
    note: str = Form(""),
    allow_interpolation: bool = Form(False),
    file: UploadFile | None = File(None),
) -> InvoiceOut:
    try:
        payload = InvoiceCreate(
            scope=Scope(scope),
            number=number,
            invoice_date=invoice_date,  # type: ignore[arg-type]
            period_start=period_start,  # type: ignore[arg-type]
            period_end=period_end,  # type: ignore[arg-type]
            amount=amount,
            note=note,
            allow_interpolation=allow_interpolation,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc

    app_settings = await db.get_settings()
    try:
        result = await allocate(
            scope=payload.scope,
            amount=payload.amount,
            period_start=payload.period_start,
            period_end=payload.period_end,
            app_settings=app_settings,
            ha=ha_client(),
            allow_interpolation=payload.allow_interpolation,
        )
    except MissingReadingError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "missing_readings",
                "message": exc.message,
                "missing": exc.missing,
                "can_interpolate": True,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Home-Assistant-Zugriff fehlgeschlagen: {exc}") from exc

    file_path = None
    if file and file.filename:
        dest_dir = settings.data_dir / "invoices"
        dest_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename).suffix or ".bin"
        dest = dest_dir / f"{uuid.uuid4().hex}{suffix}"
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        file_path = str(dest.relative_to(settings.data_dir))

    row = await db.create_invoice(
        {
            "scope": payload.scope.value,
            "number": payload.number,
            "invoice_date": payload.invoice_date.isoformat(),
            "period_start": payload.period_start.isoformat(),
            "period_end": payload.period_end.isoformat(),
            "amount": payload.amount,
            "note": payload.note,
            "file_path": file_path,
            "status": "calculated",
        }
    )
    await db.save_allocation(row["id"], result.model_dump(mode="json"))
    row = await db.get_invoice(row["id"])
    return InvoiceOut.model_validate(row)


@router.post("/invoices/json", response_model=InvoiceOut)
async def create_invoice_json(body: InvoiceCreate) -> InvoiceOut:
    """JSON create without file (for tests / API clients)."""
    app_settings = await db.get_settings()
    try:
        result = await allocate(
            scope=body.scope,
            amount=body.amount,
            period_start=body.period_start,
            period_end=body.period_end,
            app_settings=app_settings,
            ha=ha_client(),
            allow_interpolation=body.allow_interpolation,
        )
    except MissingReadingError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "missing_readings",
                "message": exc.message,
                "missing": exc.missing,
                "can_interpolate": True,
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    row = await db.create_invoice(
        {
            "scope": body.scope.value,
            "number": body.number,
            "invoice_date": body.invoice_date.isoformat(),
            "period_start": body.period_start.isoformat(),
            "period_end": body.period_end.isoformat(),
            "amount": body.amount,
            "note": body.note,
            "file_path": None,
            "status": "calculated",
        }
    )
    await db.save_allocation(row["id"], result.model_dump(mode="json"))
    row = await db.get_invoice(row["id"])
    return InvoiceOut.model_validate(row)


@router.patch("/invoices/{invoice_id}", response_model=InvoiceOut)
async def patch_invoice(invoice_id: int, body: InvoiceUpdate) -> InvoiceOut:
    data = body.model_dump(exclude_unset=True)
    allow_interpolation = data.pop("allow_interpolation", False) or False
    row = await db.update_invoice(invoice_id, data)
    if not row:
        raise HTTPException(404, "Rechnung nicht gefunden")

    # Recalculate if period/amount changed
    if any(k in data for k in ("period_start", "period_end", "amount")):
        app_settings = await db.get_settings()
        try:
            result = await allocate(
                scope=Scope(row["scope"]),
                amount=row["amount"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                app_settings=app_settings,
                ha=ha_client(),
                allow_interpolation=allow_interpolation,
            )
            await db.save_allocation(invoice_id, result.model_dump(mode="json"))
        except MissingReadingError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "missing_readings",
                    "message": exc.message,
                    "missing": exc.missing,
                    "can_interpolate": True,
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        row = await db.get_invoice(invoice_id)

    return InvoiceOut.model_validate(row)


@router.delete("/invoices/{invoice_id}")
async def remove_invoice(invoice_id: int) -> dict[str, bool]:
    row = await db.get_invoice(invoice_id)
    if not row:
        raise HTTPException(404, "Rechnung nicht gefunden")
    if row.get("file_path"):
        path = settings.data_dir / row["file_path"]
        if path.exists():
            path.unlink()
    ok = await db.delete_invoice(invoice_id)
    return {"ok": ok}


@router.get("/invoices/{invoice_id}/file")
async def download_file(invoice_id: int) -> FileResponse:
    row = await db.get_invoice(invoice_id)
    if not row or not row.get("file_path"):
        raise HTTPException(404, "Datei nicht gefunden")
    path = settings.data_dir / row["file_path"]
    if not path.exists():
        raise HTTPException(404, "Datei nicht gefunden")
    return FileResponse(path)


@router.get("/summary")
async def summary() -> dict:
    rows = await db.list_invoices()
    totals = {"EG": 0.0, "1OG": 0.0, "2OG": 0.0, "all": 0.0}
    by_scope: dict[str, dict[str, float]] = {}
    for row in rows:
        alloc = row.get("allocation") or {}
        amounts = alloc.get("amounts") or {}
        scope = row["scope"] if isinstance(row["scope"], str) else row["scope"].value
        by_scope.setdefault(scope, {"EG": 0.0, "1OG": 0.0, "2OG": 0.0, "all": 0.0})
        for u in ("EG", "1OG", "2OG"):
            v = float(amounts.get(u, 0))
            totals[u] += v
            by_scope[scope][u] += v
        totals["all"] += float(row["amount"])
        by_scope[scope]["all"] += float(row["amount"])
    return {"totals": totals, "by_scope": by_scope, "count": len(rows)}
