"""Post-call automation — updates DB, creates Zoho ticket, triggers notifications."""
from datetime import datetime, timezone
import structlog

from app.agents.state import CallState
from app.core.cache import redis_manager

logger = structlog.get_logger(__name__)


async def post_call_agent(state: CallState) -> dict:
    """
    Runs after call ends:
    1. Update the pre-created Zoho Desk ticket with transcript and resolution status.
    2. Save transcript + summary to PostgreSQL CRM.
    3. Trigger CSAT survey SMS.
    """
    call_id = state.get("call_id", "unknown")
    logger.info("post_call_start", call_id=call_id)

    zoho_ticket_id = state.get("zoho_ticket_id")
    summary = state.get("call_summary", {}) or {}
    transcript = state.get("transcript", []) or []

    # Format the transcript text
    conv_lines = []
    for m in transcript:
        if isinstance(m, dict):
            conv_lines.append(f"{m.get('speaker', 'unknown')}: {m.get('text', '')}")
        else:
            conv_lines.append(f"{getattr(m, 'name', 'unknown')}: {getattr(m, 'content', '')}")
    conv_text = "\n".join(conv_lines)

    # Build final detailed description
    final_desc = (
        f"Customer Issue: {summary.get('customer_issue', 'N/A')}\n"
        f"Resolution Details: {summary.get('resolution', 'N/A')}\n"
        f"Outcome: {summary.get('outcome', 'pending')}\n"
        f"Product: {summary.get('product_mentioned', 'N/A')}\n"
        f"Internal Note: {summary.get('internal_note', 'N/A')}\n\n"
        f"--- FULL CALL TRANSCRIPT ---\n{conv_text}"
    )

    # Resolution status (Closed if resolved, Open if unresolved)
    zoho_status = "Closed" if state.get("issue_resolved") else "Open"

    if zoho_ticket_id:
        # Update existing ticket
        try:
            from app.integrations.zoho_desk import ZohoDesk
            zoho = ZohoDesk()
            await zoho.update_ticket_summary(
                ticket_id=zoho_ticket_id,
                description=final_desc,
                status=zoho_status
            )
            logger.info("zoho_ticket_updated_at_end", call_id=call_id, ticket_id=zoho_ticket_id, status=zoho_status)
        except Exception as e:
            logger.error("zoho_ticket_update_error", ticket_id=zoho_ticket_id, error=str(e))
    else:
        # Fallback: if no ticket existed at the start, create a new one (only if unresolved or complaint)
        if not state.get("issue_resolved") or state.get("intent") == "complaint":
            try:
                from app.integrations.zoho_desk import ZohoDesk
                zoho = ZohoDesk()
                ctx = state.get("customer_context", {})
                intel = state.get("intelligence", {})
                new_ticket_id = await zoho.create_ticket(
                    subject=f"Call: {state.get('intent', 'support')} - {ctx.get('name', 'Customer')}",
                    description=final_desc,
                    customer_email=ctx.get("email", "caller@unknown.com"),
                    priority=intel.get("priority", "medium"),
                    department=_intent_to_department(state.get("intent")),
                    call_id=call_id,
                )
                if new_ticket_id:
                    state["zoho_ticket_id"] = new_ticket_id
                    zoho_ticket_id = new_ticket_id
                    logger.info("zoho_ticket_created_fallback", call_id=call_id, ticket_id=new_ticket_id)
            except Exception as e:
                logger.error("zoho_ticket_create_fallback_error", error=str(e))

    # 2. Save to PostgreSQL CRM
    await _save_call_to_db(state)

    # 3. Trigger CSAT survey
    mobile = state.get("customer_context", {}).get("mobile")
    if mobile:
        await _trigger_csat(call_id, mobile)

    logger.info("post_call_complete", call_id=call_id)
    return {
        "zoho_ticket_id": zoho_ticket_id,
        "routing_history": state.get("routing_history", []) + ["post_call"]
    }


async def _save_call_to_db(state: CallState):
    try:
        from app.core.database import AsyncSessionLocal
        from app.models import Call
        from sqlalchemy import update
        import uuid

        ctx = state.get("customer_context", {})
        intel = state.get("intelligence", {})
        summary = state.get("call_summary", {})

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Call)
                .where(Call.id == state.get("call_id"))
                .values(
                    status="completed" if state.get("issue_resolved") else "escalated",
                    ended_at=datetime.now(timezone.utc),
                    detected_intent=state.get("intent"),
                    intent_confidence=state.get("intent_confidence"),
                    sentiment=intel.get("sentiment"),
                    sentiment_score=intel.get("sentiment_score"),
                    ai_confidence=intel.get("ai_confidence"),
                    priority=intel.get("priority"),
                    resolved=state.get("issue_resolved", False),
                    resolution_type="ai_resolved" if state.get("issue_resolved") else "escalated",
                    transcript=state.get("transcript", []),
                    ai_summary=summary.get("resolution", "") if summary else "",
                    citations=state.get("citations", []),
                    routing_path=state.get("routing_history", []),
                )
            )
            await db.commit()
    except Exception as e:
        logger.error("save_call_db_error", error=str(e))


async def _create_zoho_ticket(state: CallState) -> str | None:
    """Create Zoho Desk ticket (calls external API)."""
    try:
        from app.integrations.zoho_desk import ZohoDesk
        ctx = state.get("customer_context", {})
        summary = state.get("call_summary", {})
        intel = state.get("intelligence", {})

        zoho = ZohoDesk()
        ticket_id = await zoho.create_ticket(
            subject=f"Call: {state.get('intent', 'support')} - {ctx.get('name', 'Customer')}",
            description=summary.get("customer_issue", "Customer support call"),
            customer_email=ctx.get("email", ""),
            priority=intel.get("priority", "medium"),
            department=_intent_to_department(state.get("intent")),
            call_id=state.get("call_id"),
            ai_summary=str(summary),
        )
        return ticket_id
    except Exception as e:
        logger.error("zoho_ticket_error", error=str(e))
        return None


async def _trigger_csat(call_id: str, mobile: str):
    """Queue CSAT SMS (fire and forget)."""
    await redis_manager.publish("notifications.csat", {
        "call_id": call_id,
        "mobile": mobile,
        "type": "csat_survey",
    })


def _intent_to_department(intent: str | None) -> str:
    return {
        "product_support": "Technical Support",
        "warranty": "Warranty",
        "invoice": "Billing",
        "order_status": "Logistics",
        "return": "Returns",
        "replacement": "Returns",
        "complaint": "Customer Experience",
    }.get(intent or "", "Customer Support")
