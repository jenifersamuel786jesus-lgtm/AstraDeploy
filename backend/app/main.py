from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.app.api.routes import router

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"


def apply_schema_migrations() -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    apply_schema_migrations()
    yield


app = FastAPI(
    title="AstraDeploy API",
    version="0.1.0",
    description="Context-aware MLOps resource planning with clearly labeled demo-mode workflows.",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/manus-routes.json", include_in_schema=False)
def route_manifest() -> FileResponse:
    return FileResponse(ROOT / "public" / "manus-routes.json", media_type="application/json")


if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def frontend(full_path: str):
    if full_path == "" or full_path == "index.html":
        candidate = STATIC_DIR / "index.html"
    else:
        candidate = (STATIC_DIR / full_path).resolve()
        if not str(candidate).startswith(str(STATIC_DIR.resolve())):
            raise HTTPException(status_code=404, detail="Not found")
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    if candidate.is_file():
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "AstraDeploy frontend build is not ready. Run pnpm build."}, status_code=503)
