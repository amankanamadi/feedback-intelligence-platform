import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError

from app.api.analytics import router as analytics_router
from app.api.attachments import router as attachments_router
from app.api.auth import router as auth_router
from app.api.bookings import router as bookings_router
from app.api.feedback import router as feedback_router
from app.api.feedback_export import router as feedback_export_router
from app.api.notifications import router as notifications_router
from app.api.properties import router as properties_router
from app.api.reports import router as reports_router
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Airbnb Guest Experience Intelligence Platform")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS allowlist is explicit (never "*") since allow_credentials=True is
# required for the Next.js app's cookie-based auth to survive its
# cross-port dev setup - this pairing is also this project's primary CSRF
# defense (see app/core/security.py's cookie SameSite settings for the
# other half): a browser won't attach these cookies to a request from any
# origin not in this list, so classic cross-site form/fetch CSRF isn't
# exploitable even without a double-submit token. Deliberately not adding
# one on top of this for a same-site SPA + API pair.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)

app.include_router(auth_router)
app.include_router(feedback_router)
app.include_router(feedback_export_router)
app.include_router(analytics_router)
app.include_router(reports_router)
app.include_router(attachments_router)
app.include_router(properties_router)
app.include_router(bookings_router)
app.include_router(notifications_router)


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


@app.get("/")
def root() -> RedirectResponse:
    # This is a pure JSON API now - the product surface is the Next.js
    # app in web/, on its own origin. The old static dashboard
    # (frontend/index.html, served from here) has been retired.
    return RedirectResponse(url="/docs")
