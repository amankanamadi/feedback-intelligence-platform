from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.schemas import AnalyticsSummary, HostPerformance, ThemeFrequency
from app.analytics.service import get_analytics_summary, get_host_performance, get_theme_frequencies
from app.core.security import RequireStaff, require_role
from app.database.models import Role, User
from app.database.session import get_db

router = APIRouter(tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsSummary)
def analytics_summary(current_user: User = Depends(RequireStaff), db: Session = Depends(get_db)) -> AnalyticsSummary:
    return get_analytics_summary(db)


@router.get("/analytics/host-performance", response_model=Optional[HostPerformance])
def host_performance(
    current_user: User = Depends(require_role(Role.HOST)),
    db: Session = Depends(get_db),
) -> Optional[HostPerformance]:
    # 200 + null (not 404) for "you're a host, you just have no
    # properties yet" - a valid state, not an error.
    return get_host_performance(db, current_user.id)


@router.get("/themes", response_model=list[ThemeFrequency])
def theme_frequencies(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(RequireStaff),
    db: Session = Depends(get_db),
) -> list[ThemeFrequency]:
    return get_theme_frequencies(db, limit=limit)
