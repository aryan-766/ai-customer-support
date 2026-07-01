"""Call Summary Agent — generates structured post-call summary using LLM."""
from datetime import datetime, timezone
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.core.llm.ollama import OllamaLLM

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a call summary specialist. Generate a structured JSON summary of the customer support call.
Output ONLY valid JSON in this exact format:
{
  "customer_issue": "One sentence describing the customer's problem",
  "resolution": "What was done to resolve it (or 'Escalated to human agent')",
  "outcome": "resolved" or "escalated" or "pending",
  "action_items": ["list of follow-up actions"],
  "product_mentioned": "product name if mentioned",
  "zoho_category": "most appropriate Zoho category",
  "internal_note": "Note for internal team"
}
"""


async def call_summary_agent(state: CallState) -> dict:
    llm = OllamaLLM()
    call_id = state.get("call_id", "unknown")

    # Build conversation transcript for summarization
    transcript = state.get("transcript", [])
    messages = state.get("messages", [])

    conv_text = "\n".join([
        f"{getattr(m, 'name', 'unknown')}: {getattr(m, 'content', '')}"
        for m in messages[-20:]
    ])

    ctx = state.get("customer_context", {})
    intel = state.get("intelligence", {})

    prompt = f"""
Customer: {ctx.get('name', 'Unknown')} | Mobile: {ctx.get('mobile', 'N/A')}
Intent: {state.get('intent', 'unknown')} | Sentiment: {intel.get('sentiment', 'neutral')}
Resolved: {state.get('issue_resolved', False)} | Agent path: {' → '.join(state.get('routing_history', []))}

Conversation:
{conv_text}

Generate the call summary JSON:
"""

    try:
        response = await llm.generate(prompt, system=SYSTEM_PROMPT)
        summary = _parse_summary(response.text, state)
    except Exception as e:
        logger.error("call_summary_error", error=str(e))
        summary = {
            "customer_issue": "Unable to generate summary",
            "resolution": "See transcript",
            "outcome": "escalated" if state.get("escalate") else "pending",
            "action_items": [],
        }

    logger.info("call_summary_generated", call_id=call_id, outcome=summary.get("outcome"))

    return {
        "call_summary": summary,
        "routing_history": state.get("routing_history", []) + ["call_summary"],
    }


def _parse_summary(text: str, state: CallState) -> dict:
    import json, re
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {
        "customer_issue": "See transcript",
        "resolution": text[:200],
        "outcome": "escalated" if state.get("escalate") else "resolved",
        "action_items": [],
    }
