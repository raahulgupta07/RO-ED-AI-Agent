#!/usr/bin/env python3
"""
RO-ED AI Agent — FastAPI Backend
Myanmar PDF Data Extraction Pipeline
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    database.init_database()
    yield


app = FastAPI(
    title="RO-ED AI Agent",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000", "http://localhost:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routes ---
from routes import auth as auth_routes
from routes import jobs as job_routes
from routes import users as user_routes
from routes import data as data_routes
from routes import ws as ws_routes
from routes import settings as settings_routes
from routes import groups as group_routes
from routes import corrections as correction_routes
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(job_routes.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(user_routes.router, prefix="/api/users", tags=["users"])
app.include_router(data_routes.router, prefix="/api/data", tags=["data"])
app.include_router(ws_routes.router, prefix="/api/ws", tags=["pipeline"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["settings"])
app.include_router(group_routes.router, prefix="/api/groups", tags=["groups"])
app.include_router(correction_routes.router, prefix="/api/corrections", tags=["corrections"])


@app.post("/api/extract")
async def extract_pdf(
    file: "UploadFile" = None,
    mode: str = "ro_ed",
):
    """T4.1 — REST API Mode: Upload PDF, run extraction, return JSON results.
    No WebSocket needed. For external system integration.

    Args:
        file: PDF file upload
        mode: pipeline mode
    """
    from fastapi import File, UploadFile, HTTPException
    import asyncio
    import shutil
    import uuid

    if file is None:
        raise HTTPException(400, "No file uploaded")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files accepted")

    # Save to temp
    import config
    config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = config.UPLOAD_FOLDER / safe_name
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        from pipeline.pipeline import run_pipeline
        result = await asyncio.to_thread(run_pipeline, str(save_path))

        if not result:
            raise HTTPException(500, "Extraction failed")

        return {
            "status": "ok",
            "filename": file.filename,
            "mode": mode,
            "items_count": result.get("items_count", len(result.get("items", []))),
            "accuracy": result.get("accuracy", 0),
            "duration": result.get("duration_seconds", 0),
            "cost": result.get("cost_usd", 0),
            "declaration": result.get("declaration", {}),
            "items": result.get("items", []),
            "cross_validation": result.get("cross_validation"),
        }
    finally:
        # Cleanup temp file
        try:
            save_path.unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/api/health")
async def health_check():
    """Health check with system stats."""
    import os
    stats = database.get_stats()

    # DB size
    db_path = database.DB_PATH
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0

    return {
        "status": "ok",
        "version": "3.0.0",
        "pipeline": "LLM Assembler + Verifier",
        "database": {
            "total_jobs": stats["total_jobs"],
            "completed_jobs": stats["completed_jobs"],
            "size_mb": round(db_size_mb, 2),
        },
    }


# --- Serve Frontend Static Files (SPA fallback) ---
# In Docker: /app/frontend-build (copied during build)
# In dev: ../frontend/build (after npm run build)
FRONTEND_BUILD = Path(__file__).parent / "frontend-build"
if not FRONTEND_BUILD.exists():
    FRONTEND_BUILD = Path(__file__).parent.parent / "frontend" / "build"

if FRONTEND_BUILD.exists():
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import Response as StarletteResponse

    # Mount /_app for JS/CSS bundles
    _app_dir = FRONTEND_BUILD / "_app"
    if _app_dir.exists():
        app.mount("/_app", StaticFiles(directory=str(_app_dir)), name="static-app")

    @app.middleware("http")
    async def spa_middleware(request: StarletteRequest, call_next):
        """SPA fallback: serve index.html for non-API GET 404s."""
        response = await call_next(request)
        path = request.url.path

        # Let API, docs, static assets, and redirects through
        if (path.startswith("/api")
            or path.startswith("/docs")
            or path.startswith("/openapi")
            or path.startswith("/_app")
            or response.status_code < 400):
            return response

        # For GET 404s on non-API paths, serve SPA
        if request.method == "GET" and response.status_code == 404:
            file_path = FRONTEND_BUILD / path.lstrip("/")
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_BUILD / "index.html")

        return response
else:
    @app.get("/")
    async def root():
        return {"message": "RO-ED AI Agent API", "docs": "/docs", "health": "/api/health"}
