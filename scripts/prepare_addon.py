"""Copy backend + built frontend into addon/app for HA Docker build context."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON_APP = ROOT / "addon" / "app"


def main() -> None:
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        raise SystemExit("frontend/dist fehlt — zuerst: cd frontend && npm run build")

    if ADDON_APP.exists():
        shutil.rmtree(ADDON_APP)
    ADDON_APP.mkdir(parents=True)

    shutil.copytree(ROOT / "backend", ADDON_APP / "backend", ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "tests", ".env"))
    shutil.copytree(dist, ADDON_APP / "www")
    print(f"Prepared {ADDON_APP}")


if __name__ == "__main__":
    main()
