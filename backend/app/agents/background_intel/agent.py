"""
Background Intelligence Agent — runs sentiment analysis, confidence scoring, priority detection.
This runs AFTER intent detection and feeds the Decision Engine.
"""

import structlog
from app.agents.state import CallState, BackgroundIntelligence
from app.core.models_loader import ModelRegistry

logger = structlog.get_logger(__name__)

# Escalation thresholds
CONFIDENCE_THRESHOLD = 0.45     # escalate if AI confidence < this
ANGRY_KEYWORDS = [
    "escalate", "manager", "supervisor", "useless", "pathetic",
    "worst", "terrible", "cheating", "fraud", "consumer court",
    # Hindi keywords
    "bakwaas", "bekar", "manager bulao", "scam", "dhoka",
]


async def background_intelligence_agent(state: CallState) -> dict:
    """
    Analyzes the call context and populates BackgroundIntelligence.
    Determines if escalation is needed.
    """
    models = ModelRegistry()
    call_id = state.get("call_id", "unknown")

    # Collect recent conversation text for analysis
    all_text = _get_conversation_text(state.get("messages", []))

    intel = dict(state.get("intelligence", {}))
    should_escalate = False
    escalation_reason = None

    # ── Sentiment Analysis ─────────────────────────────────────────────────────
    if all_text and models._initialized:
        sentiment_result = models.detect_sentiment(all_text[-512:])
        intel["sentiment"] = sentiment_result["sentiment"]
        intel["sentiment_score"] = sentiment_result["score"]

        if intel["sentiment"] == "angry":
            should_escalate = True
            escalation_reason = "angry_customer"

    # ── Keyword escalation triggers ───────────────────────────────────────────
    if all_text and not should_escalate:
        lowered = all_text.lower()
        for kw in ANGRY_KEYWORDS:
            if kw in lowered:
                should_escalate = True
                escalation_reason = "escalation_keyword"
                break

    # ── AI Confidence (based on intent confidence) ────────────────────────────
    intent_conf = state.get("intent_confidence", 1.0)
    intel["ai_confidence"] = intent_conf

    if intent_conf < CONFIDENCE_THRESHOLD:
        should_escalate = True
        escalation_reason = escalation_reason or "low_ai_confidence"

    # ── Priority Detection ────────────────────────────────────────────────────
    intel["priority"] = _detect_priority(state, intel)

    # ── VIP customer escalation ────────────────────────────────────────────────
    if state.get("customer_context", {}).get("vip_status", False):
        should_escalate = True
        escalation_reason = escalation_reason or "vip_customer"

    if should_escalate:
        intel["escalation_reason"] = escalation_reason

    logger.info("background_intel_done",
                call_id=call_id,
                sentiment=intel.get("sentiment"),
                priority=intel.get("priority"),
                escalate=should_escalate,
                reason=escalation_reason)

    return {
        "intelligence": intel,
        "escalate": should_escalate,
        "escalation_context": {"reason": escalation_reason} if should_escalate else {},
        "routing_history": state.get("routing_history", []) + ["background_intel"],
    }


def _detect_priority(state: CallState, intel: dict) -> str:
    sentiment = intel.get("sentiment", "neutral")
    has_prev_tickets = len(state.get("customer_context", {}).get("previous_tickets", [])) > 0
    vip = state.get("customer_context", {}).get("vip_status", False)

    if vip or sentiment == "angry":
        return "critical"
    if has_prev_tickets or sentiment == "negative":
        return "high"
    if sentiment == "neutral":
        return "medium"
    return "low"


def _get_conversation_text(messages: list) -> str:
    """Concatenate all message content for analysis."""
    parts = []
    for msg in messages[-10:]:  # last 10 messages only
        content = getattr(msg, "content", "") or ""
        if content:
            parts.append(content)
    return " ".join(parts)
