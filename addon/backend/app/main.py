from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import router
from .config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "invoices").mkdir(parents=True, exist_ok=True)
    await db.init_db()
    yield


app = FastAPI(title="Abrechnung Vitroler", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.middleware("http")
async def ingress_guard(request: Request, call_next):
    # In add-on production, prefer ingress IP; local/dev allows all.
    if not settings.allow_all_hosts:
        client = request.client.host if request.client else ""
        if client not in (settings.ingress_only_ip, "127.0.0.1", "::1"):
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


static_dir = Path(settings.static_dir)
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = static_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")
else:

    @app.get("/")
    async def index_fallback() -> dict[str, str]:
        return {
            "message": "Abrechnung Vitroler API",
            "hint": "Frontend nicht gebaut — siehe /api/health",
        }
