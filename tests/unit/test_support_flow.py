import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend directory to sys.path so we can import app
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from app.agents.state import initial_state
from app.agents.authentication.agent import authentication_agent, _extract_auth_id_from_messages
from app.agents.intent.agent import intent_detection_agent
from langchain_core.messages import HumanMessage, AIMessage

def test_extract_auth_id():
    # Test Customer ID extraction
    msg1 = [HumanMessage(content="My customer ID is CUST-10001")]
    assert _extract_auth_id_from_messages(msg1) == "CUST-10001"

    # Test Order ID extraction
    msg2 = [HumanMessage(content="Here is my order: AMB12345")]
    assert _extract_auth_id_from_messages(msg2) == "AMB-12345"

    # Test Invoice ID extraction
    msg3 = [HumanMessage(content="Invoice number is INV-98765")]
    assert _extract_auth_id_from_messages(msg3) == "INV-98765"

    # Test no ID
    msg4 = [HumanMessage(content="Hi support")]
    assert _extract_auth_id_from_messages(msg4) is None

@pytest.mark.asyncio
@patch("app.agents.authentication.agent._lookup_customer")
async def test_authentication_agent_success(mock_lookup):
    mock_lookup.return_value = {
        "id": "123-uuid",
        "name": "Test Customer",
        "email": "test@example.com",
        "mobile": "9876543210",
        "is_vip": True,
        "crm_id": "CUST-10001"
    }

    state = initial_state(call_id="call-123", session_id="sess-123")
    state["messages"].append(HumanMessage(content="My customer ID is CUST-10001"))

    result = await authentication_agent(state)
    
    assert result["customer_context"]["is_authenticated"] is True
    assert result["customer_context"]["name"] == "Test Customer"
    assert result["customer_context"]["vip_status"] is True
    assert "authentication" in result["routing_history"]

@pytest.mark.asyncio
@patch("app.core.models_loader.ModelRegistry.detect_intent")
async def test_intent_detection_escalation(mock_detect_intent):
    # If confidence is low, it should escalate
    mock_detect_intent.return_value = {
        "intent": "warranty",
        "confidence": 0.3,
        "all_scores": {}
    }

    state = initial_state(call_id="call-123", session_id="sess-123")
    state["messages"].append(HumanMessage(content="gibberish talk support"))

    result = await intent_detection_agent(state)
    
    assert result["intent"] == "talk_to_human"
    assert result["escalate"] is True
    assert result["escalation_context"]["reason"] == "unrecognized_intent"
