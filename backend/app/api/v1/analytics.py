"""Analytics API — KPIs, trends, agent performance."""
from datetime import date, timedelta
from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.core.database import get_db
from app.models import Call, AnalyticsEvent

router = APIRouter(prefix="/analytics")


@router.get("/kpis")
async def get_kpis(
    from_date: date = Query(default=date.today() - timedelta(days=30)),
    to_date: date = Query(default=date.today()),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard KPIs for a date range."""
    from_dt = from_date.isoformat()
    to_dt = to_date.isoformat()

    result = await db.execute(text("""
        SELECT
            COUNT(*)                                      AS total_calls,
            COUNT(*) FILTER (WHERE resolved = TRUE)       AS ai_resolved,
            COUNT(*) FILTER (WHERE status = 'escalated')  AS escalated,
            AVG(EXTRACT(EPOCH FROM (ended_at - started_at))) AS avg_handle_time_sec,
            AVG(CASE WHEN sentiment = 'positive' THEN 1
                     WHEN sentiment = 'neutral'  THEN 0
                     ELSE -1 END)                         AS avg_sentiment_score
        FROM calls
        WHERE started_at >= :from_dt AND started_at < :to_dt
    """), {"from_dt": from_dt, "to_dt": to_dt})

    row = result.fetchone()

    total = row.total_calls or 0
    ai_resolved = row.ai_resolved or 0
    escalated = row.escalated or 0

    return {
        "period": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "total_calls": total,
        "ai_resolution_rate": round(ai_resolved / total, 3) if total else 0,
        "human_transfer_rate": round(escalated / total, 3) if total else 0,
        "avg_handle_time_sec": round(float(row.avg_handle_time_sec or 0), 1),
        "csat_score": None,  # populated after CSAT integration
        "avg_sentiment_score": round(float(row.avg_sentiment_score or 0), 3),
    }


@router.get("/intents")
async def get_intent_distribution(db: AsyncSession = Depends(get_db)):
    """Most common intents across all calls."""
    result = await db.execute(text("""
        SELECT detected_intent, COUNT(*) as count
        FROM calls
        WHERE detected_intent IS NOT NULL
        GROUP BY detected_intent
        ORDER BY count DESC
        LIMIT 10
    """))
    return {"intents": [{"intent": r.detected_intent, "count": r.count} for r in result]}


@router.get("/sentiment")
async def get_sentiment_trends(db: AsyncSession = Depends(get_db)):
    """Sentiment distribution."""
    result = await db.execute(text("""
        SELECT sentiment, COUNT(*) as count
        FROM calls
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
    """))
    return {"sentiment": [{"label": r.sentiment, "count": r.count} for r in result]}


@router.get("/escalations")
async def get_escalation_reasons(db: AsyncSession = Depends(get_db)):
    """Escalation reason breakdown."""
    result = await db.execute(text("""
        SELECT 
            event_data->>'reason' AS reason,
            COUNT(*) AS count
        FROM analytics_events
        WHERE event_type = 'escalation'
        GROUP BY reason
        ORDER BY count DESC
    """))
    return {"escalations": [{"reason": r.reason, "count": r.count} for r in result]}
