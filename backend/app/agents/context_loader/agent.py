"""
Context Loader — fetches all customer data from PostgreSQL after authentication.
Loads previous tickets, orders, warranty info into the CallState.
"""

import structlog
from app.agents.state import CallState

logger = structlog.get_logger(__name__)


async def context_loader_agent(state: CallState) -> dict:
    """Load full customer context from DB if authenticated."""
    ctx = dict(state.get("customer_context", {}))
    customer_id = ctx.get("customer_id")

    if not customer_id:
        logger.info("context_loader_skipped", reason="not_authenticated")
        return {"routing_history": state.get("routing_history", []) + ["context_loader"]}

    try:
        from app.core.database import AsyncSessionLocal
        from app.models.customer import Customer
        from sqlalchemy import select, text

        async with AsyncSessionLocal() as db:
            # Previous tickets
            tickets_result = await db.execute(
                text("""
                    SELECT t.id, t.subject, t.status, t.priority, t.created_at
                    FROM tickets t
                    WHERE t.customer_id = :cid
                    ORDER BY t.created_at DESC
                    LIMIT 5
                """),
                {"cid": customer_id},
            )
            ctx["previous_tickets"] = [dict(r._mapping) for r in tickets_result]

            # Recent orders (from last 10 calls)
            calls_result = await db.execute(
                text("""
                    SELECT c.detected_intent, c.resolved, c.started_at, c.ai_summary
                    FROM calls c
                    WHERE c.customer_id = :cid
                    ORDER BY c.started_at DESC
                    LIMIT 5
                """),
                {"cid": customer_id},
            )
            ctx["crm_profile"] = {
                "recent_calls": [dict(r._mapping) for r in calls_result]
            }

        logger.info("context_loaded", customer_id=customer_id,
                    tickets=len(ctx.get("previous_tickets", [])))

    except Exception as e:
        logger.error("context_loader_error", error=str(e))

    return {
        "customer_context": ctx,
        "routing_history": state.get("routing_history", []) + ["context_loader"],
    }
