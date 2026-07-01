"""
Agent Assist — runs alongside human agents, provides real-time suggestions.
Subscribes to live transcript and pushes AI suggestions to agent dashboard.
"""
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.core.llm.ollama import OllamaLLM
from app.core.rag.retriever import rag
from app.core.cache import redis_manager

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an AI assistant helping a human customer support agent at Ambrane.
Analyze the conversation and provide:
1. Next best response suggestion (1-2 sentences, ready to use)
2. Relevant policy or KB article to reference
3. Any compliance concern to flag

Be concise. The human agent needs quick, actionable help.
Output JSON format:
{
  "suggestion": "...",
  "kb_reference": "article title or citation",
  "compliance_alert": null or "concern text"
}
"""


async def agent_assist_agent(state: CallState) -> dict:
    """
    Generates AI suggestions for the human agent.
    Results pushed to Redis channel for real-time dashboard updates.
    """
    llm = OllamaLLM()
    call_id = state.get("call_id", "unknown")
    human_agent_id = state.get("human_agent_id")

    # Build conversation summary for assist
    recent_messages = state.get("messages", [])[-6:]
    conv_text = "\n".join([
        f"{getattr(m, 'name', 'unknown')}: {getattr(m, 'content', '')}"
        for m in recent_messages
    ])

    # RAG search for relevant KB
    last_user_text = _get_last_user_text(state.get("messages", []))
    citations = await rag.search(last_user_text) if last_user_text else []
    context = rag.build_context_prompt(citations[:2])

    try:
        response = await llm.generate(
            f"Conversation:\n{conv_text}\n\n{context}",
            system=SYSTEM_PROMPT,
        )
        suggestions = _parse_suggestions(response.text, citations)
    except Exception as e:
        logger.error("agent_assist_error", error=str(e))
        suggestions = [{"suggestion": "Unable to generate suggestion", "kb_reference": None}]

    # Push to human agent's channel
    if human_agent_id:
        await redis_manager.publish(
            f"assist.{human_agent_id}",
            {"type": "assist_suggestion", "data": suggestions, "call_id": call_id},
        )
        logger.info("assist_suggestion_sent", call_id=call_id, agent=human_agent_id)

    return {
        "assist_suggestions": suggestions,
        "routing_history": state.get("routing_history", []) + ["agent_assist"],
    }


def _parse_suggestions(text: str, citations: list) -> list[dict]:
    import json, re
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return [data]
    except Exception:
        pass
    return [{"suggestion": text[:200], "kb_reference": citations[0]["title"] if citations else None}]


def _get_last_user_text(messages: list) -> str:
    from langchain_core.messages import HumanMessage
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content or ""
    return ""
