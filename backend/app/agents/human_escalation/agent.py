"""Human Escalation Agent — packages full context for human agent handoff."""
from langchain_core.messages import AIMessage
from datetime import datetime, timezone
import structlog

from app.agents.state import CallState
from app.core.cache import redis_manager

logger = structlog.get_logger(__name__)

HANDOFF_EN = (
    "I'm connecting you to one of our human agents right now. "
    "They will have your complete call history and won't ask you to repeat anything. "
    "Please hold for a moment."
)
HANDOFF_HI = (
    "Main aapko abhi hamare human agent se connect kar rahi hoon. "
    "Unhe aapki poori call history milegi, aapko kuch dobara batana nahi padega. "
    "Kripya ek pal rukein."
)


async def human_escalation_agent(state: CallState) -> dict:
    """
    1. Build complete handoff context package
    2. Push to Redis for agent dashboard
    3. Notify human agent via Pub/Sub
    """
    call_id = state.get("call_id", "unknown")
    language = state.get("intelligence", {}).get("language", "en")
    intel = state.get("intelligence", {})
    ctx = state.get("customer_context", {})

    # Build complete escalation package
    handoff_package = {
        "call_id": call_id,
        "escalated_at": datetime.now(timezone.utc).isoformat(),
        "escalation_reason": state.get("escalation_context", {}).get("reason", "unknown"),
        "customer": {
            "name": ctx.get("name", "Unknown"),
            "mobile": ctx.get("mobile", ""),
            "email": ctx.get("email", ""),
            "is_authenticated": ctx.get("is_authenticated", False),
            "vip_status": ctx.get("vip_status", False),
        },
        "intelligence": {
            "sentiment": intel.get("sentiment", "neutral"),
            "sentiment_score": intel.get("sentiment_score", 0.0),
            "priority": intel.get("priority", "medium"),
            "language": intel.get("language", "en"),
        },
        "intent": state.get("intent"),
        "routing_history": state.get("routing_history", []),
        "transcript": state.get("transcript", []),
        "previous_tickets": ctx.get("previous_tickets", []),
        "recent_calls": ctx.get("crm_profile", {}).get("recent_calls", []),
        "citations_used": state.get("citations", []),
        "suggested_resolution": _build_suggested_resolution(state),
    }

    # Push to Redis for human agent dashboard
    await redis_manager.save_call_state(
        f"{call_id}:handoff",
        handoff_package
    )

    # Broadcast to agent channel
    await redis_manager.publish("human.escalation", handoff_package)

    logger.info("escalation_complete",
                call_id=call_id,
                reason=handoff_package["escalation_reason"],
                priority=intel.get("priority"))

    handoff_msg = HANDOFF_HI if language == "hi" else HANDOFF_EN

    return {
        "active_agent": "human_escalation",
        "escalation_context": handoff_package,
        "routing_history": state.get("routing_history", []) + ["human_escalation"],
        "messages": [AIMessage(content=handoff_msg, name="human_escalation")],
    }


def _build_suggested_resolution(state: CallState) -> str:
    """Generate a brief suggested resolution based on intent and context."""
    intent = state.get("intent", "unknown")
    suggestions = {
        "warranty": "Verify warranty via My Product Care, check purchase date against policy.",
        "product_support": "Check product manual, attempt reset/restart steps first.",
        "order_status": "Pull order from NimbusPost, check courier tracking link.",
        "return": "Verify 7-day return window, check product condition.",
        "complaint": "Acknowledge, create Zoho ticket, offer callback.",
    }
    return suggestions.get(intent, "Review customer history and address concern directly.")
