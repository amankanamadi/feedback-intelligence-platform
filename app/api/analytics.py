from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.schemas import AnalyticsSummary, ThemeFrequency
from app.analytics.service import get_analytics_summary, get_theme_frequencies
from app.core.security import RequireAdmin
from app.database.models import User
from app.database.session import get_db

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsSummary)
def analytics_summary(current_user: User = Depends(RequireAdmin), db: Session = Depends(get_db)) -> AnalyticsSummary:
    return get_analytics_summary(db)


@router.get("/themes", response_model=list[ThemeFrequency])
def theme_frequencies(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(RequireAdmin),
    db: Session = Depends(get_db),
) -> list[ThemeFrequency]:
    return get_theme_frequencies(db, limit=limit)
