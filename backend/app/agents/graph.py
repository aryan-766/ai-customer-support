"""
Master LangGraph Supervisor Graph.
Orchestrates independent nodes.
Router contains NO business logic, only conditional edges.

Uses ADVANCED RAG-based agents from individual agent folders:
- Each agent has domain-specific system prompts
- RAG retrieval from Qdrant knowledge base with category filtering
- Customer history injection (previous tickets, calls)
- Citation tracking and source references
- Automatic resolution/escalation detection via [RESOLVED]/[ESCALATE] tags
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import CallState
from app.agents.nodes.intent import detect_intent
from app.agents.nodes.router import route_intent
from app.agents.nodes.escalation import human_escalation_agent

# ── Advanced RAG-based agents (from individual agent folders) ─────────────────
from app.agents.product_support.agent import product_support_agent
from app.agents.order_status.agent import order_status_agent
from app.agents.complaint.agent import complaint_agent
from app.agents.warranty.agent import warranty_agent
from app.agents.registration.agent import registration_agent
from app.agents.invoice.agent import invoice_agent
from app.agents.return_replacement.agent import return_replacement_agent

logger = structlog.get_logger(__name__)


def check_resolution(state: CallState) -> str:
    """Check if the issue was resolved or if we need to escalate."""
    if state.get("escalate", False):
        return "human_escalation"
    if state.get("issue_resolved", False):
        return "end"

    # Loop protection — if agent has been called too many times, escalate
    if len(state.get("routing_history", [])) > 5:
        return "human_escalation"

    return "end"


def build_graph() -> StateGraph:
    graph = StateGraph(CallState)

    # ── Add Nodes ─────────────────────────────────────────────────────────────
    graph.add_node("intent_detection", detect_intent)

    # Advanced RAG-based business agents (each uses base_business_agent with RAG)
    graph.add_node("faq_agent", product_support_agent)          # FAQ → product support with RAG
    graph.add_node("order_agent", order_status_agent)           # NimbusPost tracking + RAG
    graph.add_node("complaint_agent", complaint_agent)          # Complaint + escalation context
    graph.add_node("tech_support_agent", product_support_agent) # Tech support = product support with manuals
    graph.add_node("registration_agent", registration_agent)    # Registration + RAG
    graph.add_node("sales_agent", product_support_agent)        # Sales queries → product knowledge
    graph.add_node("warranty_agent", warranty_agent)            # Warranty check + policy RAG
    graph.add_node("invoice_agent", invoice_agent)              # Invoice lookup + RAG
    graph.add_node("return_agent", return_replacement_agent)    # Return/replacement + NimbusPost reverse pickup

    # Escalation
    graph.add_node("human_escalation", human_escalation_agent)

    # ── Set Entry ─────────────────────────────────────────────────────────────
    graph.set_entry_point("intent_detection")

    # ── Add Pure Routing Edge ─────────────────────────────────────────────────
    graph.add_conditional_edges(
        "intent_detection",
        route_intent,
        {
            "faq_agent": "faq_agent",
            "order_agent": "order_agent",
            "complaint_agent": "complaint_agent",
            "tech_support_agent": "tech_support_agent",
            "registration_agent": "registration_agent",
            "sales_agent": "sales_agent",
            "warranty_agent": "warranty_agent",
            "invoice_agent": "invoice_agent",
            "return_agent": "return_agent",
            "human_escalation": "human_escalation",
        }
    )

    # ── Return Paths ──────────────────────────────────────────────────────────
    # Check resolution after every business agent
    BUSINESS_AGENTS = [
        "faq_agent", "order_agent", "complaint_agent",
        "tech_support_agent", "registration_agent", "sales_agent",
        "warranty_agent", "invoice_agent", "return_agent",
    ]

    for agent in BUSINESS_AGENTS:
        graph.add_conditional_edges(
            agent,
            check_resolution,
            {
                "end": END,
                "human_escalation": "human_escalation",
            }
        )

    graph.add_edge("human_escalation", END)

    return graph.compile()


call_graph = build_graph()
