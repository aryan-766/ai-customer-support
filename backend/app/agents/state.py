"""
Shared CallState — the single source of truth flowing through every agent.
All agents READ from this state and return UPDATES (immutable style).
"""

from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from langgraph.graph.message import add_messages


class CustomerContext(TypedDict, total=False):
    customer_id: Optional[str]
    mobile: Optional[str]
    name: Optional[str]
    email: Optional[str]
    is_authenticated: bool
    vip_status: bool
    crm_id: Optional[str]
    previous_tickets: List[Dict]
    orders: List[Dict]
    warranty_info: List[Dict]
    crm_profile: Dict[str, Any]


class BackgroundIntelligence(TypedDict, total=False):
    sentiment: Literal["positive", "neutral", "negative", "angry"]
    sentiment_score: float          # -1.0 to 1.0
    ai_confidence: float            # 0.0 to 1.0
    priority: Literal["low", "medium", "high", "critical"]
    escalation_reason: Optional[str]
    fraud_risk: float               # 0.0 to 1.0
    language: str                   # "en" | "hi"


class Citation(TypedDict):
    citation_id: str
    title: str
    source: str
    snippet: str
    relevance_score: float


class FollowUpAction(TypedDict):
    action_type: str                # "send_sms" | "send_email" | "schedule_callback"
    details: Dict[str, Any]
    due_at: Optional[str]


class CallState(TypedDict, total=False):
    # ── Core metadata ──────────────────────────────────────────────────────────
    call_id: str
    session_id: str
    started_at: str
    channel: str                    # "phone" | "whatsapp" | "web"

    # ── Conversation (LangGraph managed) ─────────────────────────────────────
    messages: Annotated[list, add_messages]
    transcript: List[Dict]          # [{speaker, text, timestamp}]

    # ── Authentication ────────────────────────────────────────────────────────
    customer_context: CustomerContext

    # ── Routing ───────────────────────────────────────────────────────────────
    intent: Optional[str]
    intent_confidence: float
    active_agent: Optional[str]
    routing_history: List[str]

    # ── Background intelligence ───────────────────────────────────────────────
    intelligence: BackgroundIntelligence

    # ── Escalation ────────────────────────────────────────────────────────────
    escalate: bool
    escalation_context: Dict[str, Any]

    # ── Resolution ────────────────────────────────────────────────────────────
    issue_resolved: bool
    resolution_summary: Optional[str]
    zoho_ticket_id: Optional[str]

    # ── RAG ───────────────────────────────────────────────────────────────────
    citations: List[Citation]

    # ── Agent Assist (live human agent) ──────────────────────────────────────
    human_agent_id: Optional[str]
    assist_suggestions: List[Dict]

    # ── Post-call ─────────────────────────────────────────────────────────────
    call_summary: Optional[Dict]
    follow_up_actions: List[FollowUpAction]


def initial_state(call_id: str, session_id: str, channel: str = "phone") -> CallState:
    """Factory for a fresh CallState at call start."""
    from datetime import datetime, timezone
    return CallState(
        call_id=call_id,
        session_id=session_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        channel=channel,
        messages=[],
        transcript=[],
        customer_context=CustomerContext(
            is_authenticated=False,
            vip_status=False,
            previous_tickets=[],
            orders=[],
            warranty_info=[],
            crm_profile={},
        ),
        intent=None,
        intent_confidence=0.0,
        active_agent=None,
        routing_history=[],
        intelligence=BackgroundIntelligence(
            sentiment="neutral",
            sentiment_score=0.0,
            ai_confidence=1.0,
            priority="low",
            fraud_risk=0.0,
            language="en",
        ),
        escalate=False,
        escalation_context={},
        issue_resolved=False,
        resolution_summary=None,
        zoho_ticket_id=None,
        citations=[],
        human_agent_id=None,
        assist_suggestions=[],
        call_summary=None,
        follow_up_actions=[],
    )
