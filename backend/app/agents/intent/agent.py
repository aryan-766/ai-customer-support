"""
Intent Detection Agent — classifies what the customer wants.
Uses HuggingFace zero-shot classification (no fine-tuning needed!).
"""

from langchain_core.messages import HumanMessage
import structlog

from app.agents.state import CallState
from app.core.models_loader import ModelRegistry

logger = structlog.get_logger(__name__)


async def intent_detection_agent(state: CallState) -> dict:
    """
    Extracts last customer message and classifies intent.
    Updates: state.intent, state.intent_confidence, state.escalate
    """
    models = ModelRegistry()
    call_id = state.get("call_id", "unknown")

    # Get the last human message
    last_user_text = _get_last_user_message(state.get("messages", []))

    if not last_user_text:
        logger.warning("intent_no_text", call_id=call_id)
        return {
            "intent": "complaint",
            "intent_confidence": 0.5,
            "routing_history": state.get("routing_history", []) + ["intent_detection"],
        }

    # Zero-shot classification
    result = models.detect_intent(last_user_text)
    intent = result["intent"]
    confidence = result["confidence"]

    logger.info("intent_detected",
                call_id=call_id,
                intent=intent,
                confidence=confidence,
                text_preview=last_user_text[:60])

    # Trigger 1: Escalation if intent is not clear (confidence < 0.5)
    escalate = False
    escalation_context = {}
    if confidence < 0.5:
        logger.info("low_intent_confidence_escalating", call_id=call_id, confidence=confidence)
        intent = "talk_to_human"
        escalate = True
        escalation_context = {"reason": "unrecognized_intent"}

    return {
        "intent": intent,
        "intent_confidence": confidence,
        "escalate": escalate,
        "escalation_context": escalation_context,
        "routing_history": state.get("routing_history", []) + ["intent_detection"],
    }


def _get_last_user_message(messages: list) -> str:
    """Find the most recent human/customer message."""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content or ""
        # Handle dict format
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
    return ""
