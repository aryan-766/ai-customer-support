"""Receptionist Agent — first point of contact. Greets, detects language."""

from datetime import datetime, timezone
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.core.models_loader import ModelRegistry
from app.core.llm.ollama import OllamaLLM

logger = structlog.get_logger(__name__)

GREETING_EN = (
    "Welcome to Ambrane customer support! How can I help you today?"
)
GREETING_HI = (
    "Ambrane customer support mein aapka swagat hai! Aaj main aapki kya sahayata kar sakti hoon?"
)


async def receptionist_agent(state: CallState) -> dict:
    """
    1. Detect language from initial message (if any).
    2. Greet the customer in their language.
    3. Update state with language and greeting.
    """
    models = ModelRegistry()
    call_id = state.get("call_id", "unknown")
    logger.info("receptionist_start", call_id=call_id)

    # Detect language from any initial text
    initial_text = ""
    for msg in state.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            initial_text = msg.content
            break

    language = "en"
    if initial_text and models._initialized:
        lang_code = models.detect_language(initial_text)
        language = "hi" if lang_code == "hi" else "en"

    greeting = GREETING_HI if language == "hi" else GREETING_EN

    intelligence = dict(state.get("intelligence", {}))
    intelligence["language"] = language

    routing_history = list(state.get("routing_history", []))
    routing_history.append("receptionist")

    logger.info("receptionist_done", call_id=call_id, language=language)

    return {
        "intelligence": intelligence,
        "routing_history": routing_history,
        "active_agent": "receptionist",
        "messages": [AIMessage(content=greeting, name="receptionist")],
    }
