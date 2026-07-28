import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.api.analytics import router as analytics_router
from app.api.attachments import router as attachments_router
from app.api.feedback import router as feedback_router
from app.api.feedback_export import router as feedback_export_router
from app.api.reports import router as reports_router
from app.core.config import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="AI Customer Feedback Intelligence Platform")
app.include_router(feedback_router)
app.include_router(feedback_export_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(attachments_router)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.middleware("http")
async def no_cache_for_frontend(request: Request, call_next):
    """The dashboard is under active development - without this, browsers'
    heuristic caching can keep serving an old dashboard.js/index.html for a
    tab that's never been hard-refreshed, silently desyncing from the
    server (e.g. new table columns rendered by old JS)."""
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/dashboard":
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database unavailable while handling %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable. Please try again shortly."},
    )


@app.get("/health")
def health_check(settings: Settings = Depends(get_settings)) -> dict:
    logger.info("Health check requested")
    return {"status": "ok", "app_name": settings.app_name}


@app.get("/dashboard")
def dashboard_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")
