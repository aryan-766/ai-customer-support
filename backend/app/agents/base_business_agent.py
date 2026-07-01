"""
Shared base for all business agents.
Provides: RAG retrieval + LLM response + common state update pattern.
Each business agent calls this with its own system prompt and category.
"""

from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.core.llm.ollama import OllamaLLM
from app.core.rag.retriever import rag

logger = structlog.get_logger(__name__)


async def run_business_agent(
    state: CallState,
    agent_name: str,
    system_prompt: str,
    kb_category: str | None = None,
) -> dict:
    """
    Template for ALL business agents:
    1. Get last user message
    2. Retrieve relevant KB chunks (RAG)
    3. Build prompt with context
    4. Call LLM (Qwen2.5)
    5. Return updated state
    """
    llm = OllamaLLM()
    call_id = state.get("call_id", "unknown")
    language = state.get("intelligence", {}).get("language", "en")

    # Get last user message
    last_message = _get_last_user_text(state.get("messages", []))

    if not last_message:
        return _no_input_response(state, agent_name, language)

    # RAG: find relevant knowledge
    citations = await rag.search(query=last_message, category=kb_category)
    context_text = rag.build_context_prompt(citations)

    # Build customer context summary with previous history (tickets and call logs)
    ctx = state.get("customer_context", {})
    history_lines = []

    # 1. Format previous tickets
    if ctx.get("previous_tickets"):
        history_lines.append("\nPrevious Tickets:")
        for t in ctx["previous_tickets"]:
            t_id = t.get("zoho_ticket_id") or str(t.get("id"))[:8]
            history_lines.append(f"- Ticket {t_id}: {t.get('subject')} (Status: {t.get('status')})")

    # 2. Format recent calls and summaries
    recent_calls = ctx.get("crm_profile", {}).get("recent_calls", [])
    if recent_calls:
        history_lines.append("\nRecent Support Calls:")
        for c in recent_calls:
            date_str = c.get("started_at", "")[:10]
            resolved_str = "Resolved" if c.get("resolved") else "Unresolved/Escalated"
            history_lines.append(
                f"- Call on {date_str}: Intent: {c.get('detected_intent')}, "
                f"Status: {resolved_str}, Summary: {c.get('ai_summary', 'N/A')}"
            )

    history_text = "\n".join(history_lines) if history_lines else "\nNo previous tickets or call history."

    customer_info = (
        f"Customer: {ctx.get('name', 'Unknown')}\n"
        f"Authenticated: {ctx.get('is_authenticated', False)}\n"
        f"VIP Status: {ctx.get('vip_status', False)}\n"
        f"{history_text}"
    )

    # Full prompt
    user_prompt = f"""
{customer_info}

{context_text}

Customer says: "{last_message}"

Language: Respond in {"Hindi" if language == "hi" else "English"}.
Be helpful, concise, and cite sources using [citation_id] format when using knowledge base info.
"""

    # Append resolution/escalation guidance to system prompt
    system_prompt_guided = system_prompt + (
        "\n\nIf the customer's issue is fully resolved, they thank you, or indicate they have no further questions, "
        "always append [RESOLVED] at the end of your response.\n"
        "If you cannot resolve their issue, if the request is out of your scope, or if they need to speak with a human, "
        "always append [ESCALATE] at the end of your response."
    )

    # LLM generation
    try:
        response = await llm.generate(user_prompt, system=system_prompt_guided)
        response_text = response.text
        logger.info(f"{agent_name}_response_generated",
                    call_id=call_id, tokens=response.completion_tokens)
    except Exception as e:
        logger.error(f"{agent_name}_llm_error", error=str(e))
        response_text = (
            "Main abhi aapki madad karne mein asmarth hoon. Ek minute rukein."
            if language == "hi" else
            "I'm unable to process that right now. Please hold for a moment."
        )

    # Detect resolution or escalation tags in output
    issue_resolved = False
    escalate = False

    if "[RESOLVED]" in response_text:
        issue_resolved = True
        response_text = response_text.replace("[RESOLVED]", "").strip()
    if "[ESCALATE]" in response_text:
        escalate = True
        response_text = response_text.replace("[ESCALATE]", "").strip()

    # Satisfaction keywords backup check on last user text
    satisfaction_keywords = [
        "thank you", "thanks", "dhanyawad", "shukriya", "solved", 
        "solve ho gaya", "no other question", "no help needed", "bye", "okay thanks", "ok thanks"
    ]
    if any(kw in last_message.lower() for kw in satisfaction_keywords):
        issue_resolved = True

    # Merge new citations with existing
    existing_citations = list(state.get("citations", []))
    for c in citations:
        if c["citation_id"] not in [ec["citation_id"] for ec in existing_citations]:
            existing_citations.append(c)

    return {
        "active_agent": agent_name,
        "citations": existing_citations,
        "routing_history": state.get("routing_history", []) + [agent_name],
        "messages": [AIMessage(content=response_text, name=agent_name)],
        "issue_resolved": issue_resolved,
        "escalate": escalate,
    }


def _get_last_user_text(messages: list) -> str:
    from langchain_core.messages import HumanMessage
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content or ""
        if isinstance(msg, dict) and msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _no_input_response(state: CallState, agent_name: str, language: str) -> dict:
    msg = (
        "Kripya apni samasya batayein." if language == "hi"
        else "Please describe your issue and I'll be happy to help."
    )
    return {
        "active_agent": agent_name,
        "routing_history": state.get("routing_history", []) + [agent_name],
        "messages": [AIMessage(content=msg, name=agent_name)],
    }
