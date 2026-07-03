"""
Master LangGraph Supervisor Graph.
Orchestrates independent nodes. 
Router contains NO business logic, only conditional edges.
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import CallState
from app.agents.nodes.intent import detect_intent
from app.agents.nodes.router import route_intent
from app.agents.nodes.business_agents import (
    faq_agent, order_agent, complaint_agent,
    tech_support_agent, registration_agent, sales_agent
)
from app.agents.nodes.escalation import human_escalation_agent

logger = structlog.get_logger(__name__)

def check_resolution(state: CallState) -> str:
    """Check if the issue was resolved or if we need to escalate."""
    if state.get("escalate", False):
        return "human_escalation"
    if state.get("active_agent") == "completed":
        return "end"
    
    # Loop protection
    if len(state.get("routing_history", [])) > 5:
        return "human_escalation"
        
    return "end"

def build_graph() -> StateGraph:
    graph = StateGraph(CallState)

    # ── Add Nodes ─────────────────────────────────────────────────────────────
    graph.add_node("intent_detection", detect_intent)
    
    # Business logic nodes
    graph.add_node("faq_agent", faq_agent)
    graph.add_node("order_agent", order_agent)
    graph.add_node("complaint_agent", complaint_agent)
    graph.add_node("tech_support_agent", tech_support_agent)
    graph.add_node("registration_agent", registration_agent)
    graph.add_node("sales_agent", sales_agent)
    
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
            "human_escalation": "human_escalation",
        }
    )

    # ── Return Paths ──────────────────────────────────────────────────────────
    # Check resolution after every business agent
    BUSINESS_AGENTS = [
        "faq_agent", "order_agent", "complaint_agent",
        "tech_support_agent", "registration_agent", "sales_agent"
    ]
    
    for agent in BUSINESS_AGENTS:
        graph.add_conditional_edges(
            agent,
            check_resolution,
            {
                "end": END,
                "human_escalation": "human_escalation"
            }
        )
        
    graph.add_edge("human_escalation", END)

    return graph.compile()


call_graph = build_graph()
