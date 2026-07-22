import logging

from fastapi import Depends, FastAPI

from app.api.analytics import router as analytics_router
from app.api.feedback import router as feedback_router
from app.core.config import Settings, get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Customer Feedback Intelligence Platform")
app.include_router(feedback_router)
app.include_router(analytics_router)


@app.get("/health")
def health_check(settings: Settings = Depends(get_settings)) -> dict:
    logger.info("Health check requested")
    return {"status": "ok", "app_name": settings.app_name}
