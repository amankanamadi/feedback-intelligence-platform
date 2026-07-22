import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.weekly_report import generate_weekly_narrative
from app.analytics.schemas import WeeklyReportResponse
from app.analytics.service import get_analytics_summary, get_notable_feedback
from app.database.models import Priority, Sentiment
from app.database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])

REPORT_WINDOW_DAYS = 7


@router.get("/reports/weekly", response_model=WeeklyReportResponse)
def weekly_report(db: Session = Depends(get_db)) -> WeeklyReportResponse:
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=REPORT_WINDOW_DAYS)

    metrics = get_analytics_summary(db, since=period_start)
    top_concerns = get_notable_feedback(
        db, since=period_start, priority_in=[Priority.HIGH, Priority.CRITICAL], limit=5
    )
    positive_highlights = get_notable_feedback(
        db, since=period_start, sentiment=Sentiment.POSITIVE, limit=3
    )

    try:
        narrative = generate_weekly_narrative(metrics, top_concerns, positive_highlights)
    except Exception:
        logger.exception("Weekly narrative generation failed; returning metrics-only report")
        narrative = None

    return WeeklyReportResponse(
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        top_concerns=top_concerns,
        positive_highlights=positive_highlights,
        executive_summary=narrative.executive_summary if narrative else "Executive summary unavailable.",
        key_wins=narrative.key_wins if narrative else [],
        key_concerns=narrative.key_concerns if narrative else [],
        recommended_actions=narrative.recommended_actions if narrative else [],
    )
