"""
Master LangGraph Supervisor Graph.
Defines ALL nodes, edges, and routing logic for the multi-agent system.
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import CallState
from app.agents.receptionist.agent import receptionist_agent
from app.agents.authentication.agent import authentication_agent
from app.agents.context_loader.agent import context_loader_agent
from app.agents.intent.agent import intent_detection_agent
from app.agents.background_intel.agent import background_intelligence_agent
from app.agents.product_support.agent import product_support_agent
from app.agents.warranty.agent import warranty_agent
from app.agents.registration.agent import registration_agent
from app.agents.invoice.agent import invoice_agent
from app.agents.order_status.agent import order_status_agent
from app.agents.return_replacement.agent import return_replacement_agent
from app.agents.complaint.agent import complaint_agent
from app.agents.human_escalation.agent import human_escalation_agent
from app.agents.agent_assist.agent import agent_assist_agent
from app.agents.call_summary.agent import call_summary_agent
from app.agents.post_call.agent import post_call_agent

logger = structlog.get_logger(__name__)

# Intent → agent node name mapping
INTENT_TO_AGENT = {
    "product_support": "product_support",
    "warranty":        "warranty",
    "registration":    "registration",
    "invoice":         "invoice",
    "order_status":    "order_status",
    "return":          "return_replacement",
    "replacement":     "return_replacement",
    "complaint":       "complaint",
    "talk_to_human":   "human_escalation",
}


# ─────────────────────────────────────────────────────────────────────────────
# Routing functions (pure logic — NO LLM calls)
# ─────────────────────────────────────────────────────────────────────────────

def route_after_intelligence(state: CallState) -> str:
    """
    Decision Engine — runs after background intelligence.
    Escalate if any critical condition is met.
    Otherwise route to the right business agent.
    """
    intel = state.get("intelligence", {})
    ctx   = state.get("customer_context", {})

    # Escalation conditions
    should_escalate = (
        state.get("escalate", False)
        or intel.get("sentiment") == "angry"
        or intel.get("ai_confidence", 1.0) < 0.4
        or ctx.get("vip_status", False)
        or state.get("intent") == "talk_to_human"
    )

    if should_escalate:
        reason = (
            "angry_customer"   if intel.get("sentiment") == "angry"
            else "low_ai_confidence" if intel.get("ai_confidence", 1.0) < 0.4
            else "vip_customer"      if ctx.get("vip_status", False)
            else "customer_requested"
        )
        logger.info("escalating", call_id=state.get("call_id"), reason=reason)
        return "human_escalation"

    intent = state.get("intent", "complaint")
    return INTENT_TO_AGENT.get(intent, "complaint")


def check_resolution(state: CallState) -> str:
    """After each business agent — resolved? re-route? escalate?"""
    if state.get("escalate", False) or state.get("intent") == "complaint":
        return "escalate"
    if state.get("issue_resolved", False):
        return "resolved"
    # If routing history > 3, don't loop forever
    if len(state.get("routing_history", [])) >= 3:
        return "escalate"
    return "needs_more_help"


# ─────────────────────────────────────────────────────────────────────────────
# Graph builder
# ─────────────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(CallState)

    # ── Register all agent nodes ──────────────────────────────────────────────
    graph.add_node("receptionist",       receptionist_agent)
    graph.add_node("authentication",     authentication_agent)
    graph.add_node("context_loader",     context_loader_agent)
    graph.add_node("intent_detection",   intent_detection_agent)
    graph.add_node("background_intel",   background_intelligence_agent)
    graph.add_node("product_support",    product_support_agent)
    graph.add_node("warranty",           warranty_agent)
    graph.add_node("registration",       registration_agent)
    graph.add_node("invoice",            invoice_agent)
    graph.add_node("order_status",       order_status_agent)
    graph.add_node("return_replacement", return_replacement_agent)
    graph.add_node("complaint",          complaint_agent)
    graph.add_node("human_escalation",   human_escalation_agent)
    graph.add_node("agent_assist",       agent_assist_agent)
    graph.add_node("call_summarizer",    call_summary_agent)
    graph.add_node("post_call",          post_call_agent)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("receptionist")

    # ── Core flow (linear) ────────────────────────────────────────────────────
    graph.add_edge("receptionist",     "authentication")
    graph.add_edge("authentication",   "context_loader")
    graph.add_edge("context_loader",   "intent_detection")
    graph.add_edge("intent_detection", "background_intel")

    # ── Decision engine (conditional) ─────────────────────────────────────────
    graph.add_conditional_edges(
        "background_intel",
        route_after_intelligence,
        {
            "product_support":    "product_support",
            "warranty":           "warranty",
            "registration":       "registration",
            "invoice":            "invoice",
            "order_status":       "order_status",
            "return_replacement": "return_replacement",
            "complaint":          "complaint",
            "human_escalation":   "human_escalation",
        },
    )

    # ── Business agents → resolution check ───────────────────────────────────
    BUSINESS_AGENTS = [
        "product_support", "warranty", "registration",
        "invoice", "order_status", "return_replacement", "complaint",
    ]
    for agent_name in BUSINESS_AGENTS:
        graph.add_conditional_edges(
            agent_name,
            check_resolution,
            {
                "resolved":       "call_summarizer",
                "needs_more_help": "intent_detection",   # re-detect intent
                "escalate":       "human_escalation",
            },
        )

    # ── Human escalation → agent assist → summary ─────────────────────────────
    graph.add_edge("human_escalation", "agent_assist")
    graph.add_edge("agent_assist",     "call_summarizer")

    # ── Post-call pipeline ────────────────────────────────────────────────────
    graph.add_edge("call_summarizer", "post_call")
    graph.add_edge("post_call",    END)

    return graph.compile()


# Compiled graph — import this in API routes
call_graph = build_graph()
