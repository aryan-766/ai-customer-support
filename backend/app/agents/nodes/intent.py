"""
Intent Detection Node.
Uses LLM to classify the user's intent from the transcript.
"""

import json
from langchain_core.messages import AIMessage
import structlog
from app.agents.state import CallState
from app.core.llm.factory import LLMFactory

logger = structlog.get_logger(__name__)

INTENT_PROMPT = """
Analyze the conversation transcript and determine the user's PRIMARY intent.
Respond with a JSON object ONLY. Do not include markdown formatting or extra text.

Allowed intents:
- faq (general questions, policies, store locations, business hours)
- order_status (checking where an order is, tracking)
- complaint (unhappy customer, damaged product, missing items, bad service)
- technical_support (device not working, setup help, troubleshooting)
- registration (registering warranty, creating account)
- sales (wanting to buy something, asking about product features for purchase)
- escalate (explicitly asking to speak to a human or manager)

Format:
{
    "intent": "one_of_the_allowed_intents",
    "confidence": 0.0_to_1.0_float
}
"""

async def detect_intent(state: CallState) -> dict:
    """Detects intent and updates state."""
    llm = LLMFactory.get_provider()
    
    # Extract last few messages from transcript
    transcript = state.get("transcript", [])
    recent_text = "\n".join([f"{t['speaker']}: {t['text']}" for t in transcript[-3:]])
    
    if not recent_text:
        return {"intent": "faq", "intent_confidence": 1.0}
        
    try:
        response = await llm.generate(
            prompt=recent_text,
            system=INTENT_PROMPT
        )
        
        # Clean up potential markdown formatting from LLM
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        
        intent = data.get("intent", "faq")
        confidence = float(data.get("confidence", 0.8))
        
        logger.info("intent_detected", intent=intent, confidence=confidence)
        return {
            "intent": intent,
            "intent_confidence": confidence
        }
    except Exception as e:
        logger.error("intent_detection_failed", error=str(e))
        return {
            "intent": "escalate", # Fail-safe
            "intent_confidence": 0.0
        }
