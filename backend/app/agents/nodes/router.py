"""
Pure routing logic for LangGraph.
This module only contains conditional edges, NO business logic.
"""

from typing import Literal
import structlog
from app.agents.state import CallState

logger = structlog.get_logger(__name__)

def route_intent(state: CallState) -> str:
    """
    Route based on detected intent and confidence.
    If confidence < 0.6, go to human escalation.
    """
    intent = state.get("intent")
    confidence = state.get("intent_confidence", 0.0)
    
    if confidence < 0.6 or intent == "escalate":
        logger.info("routing_to_escalation", intent=intent, confidence=confidence)
        return "human_escalation"
        
    routes = {
        "faq": "faq_agent",
        "order_status": "order_agent",
        "complaint": "complaint_agent",
        "technical_support": "tech_support_agent",
        "registration": "registration_agent",
        "sales": "sales_agent",
        "warranty": "warranty_agent",
        "invoice": "invoice_agent",
        "return": "return_agent",
        "replacement": "return_agent",
    }
    
    target = routes.get(intent, "faq_agent")  # Default to FAQ if unknown
    logger.info("routing_decision", intent=intent, target=target)
    return target

