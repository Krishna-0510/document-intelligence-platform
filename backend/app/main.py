"""
Application entrypoint.

Wires together config, logging, the database, routers, and — per the
mandatory code-quality rule — global exception handling so failures return
consistent, safe JSON instead of leaking stack traces.
"""
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Intelligent Document Extraction, Validation & API Platform",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI — mandatory per spec
    redoc_url="/redoc",
)


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting %s [env=%s]", settings.app_name, settings.environment)
    init_db()
    logger.info("Database initialised at %s", settings.database_url)


# --- Request logging middleware (observability) ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    logger.info("[%s] %s %s - started", request_id, request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("[%s] Unhandled error during request", request_id)
        raise
    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        "[%s] %s %s - %s (%.1fms)",
        request_id, request.method, request.url.path, response.status_code, duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# --- Global exception handlers: consistent, safe error responses ---
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    logger.warning("Controlled error [%s]: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    # Never leak stack traces / internals to the client — log full detail server-side only.
    logger.exception("Unexpected error while handling %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while processing the request.",
            }
        },
    )


# --- Routers ---
from app.api.routes import documents, frontend  # noqa: E402  (after app/logging init by design)

app.include_router(documents.router, prefix="/api/v1")
app.include_router(frontend.router)

# --- Static frontend (optional single-deployment convenience) ---
# Resolved relative to this file, not the process's working directory, so it
# works the same whether you run `uvicorn app.main:app` from backend/ or
# elsewhere (e.g. a deployment platform's build step).
_STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "static"
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
else:
    logger.warning("Static directory not found at %s; skipping mount.", _STATIC_DIR)


@app.get("/api/v1/health", tags=["health"])
def health_check():
    """Mandatory health endpoint."""
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
