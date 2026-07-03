"""
Human Escalation Node.
"""

from langchain_core.messages import AIMessage
import structlog
from app.agents.state import CallState

logger = structlog.get_logger(__name__)

async def human_escalation_agent(state: CallState) -> dict:
    """Escalates the call to a human agent."""
    logger.info("escalating_to_human", call_id=state.get("call_id"))
    
    # In a real app, this would push the state to Redis for the Dashboard
    # and notify a human agent via WebSocket.
    
    return {
        "messages": [AIMessage(content="I'm connecting you to a human agent who can help you further. Please hold.")],
        "active_agent": "human_escalation",
        "escalate": True
    }
