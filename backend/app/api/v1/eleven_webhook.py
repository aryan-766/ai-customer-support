"""
ElevenLabs Conversational AI Webhook endpoint.
Receives tool invocation requests from ElevenLabs Agents,
calls the appropriate backend integration, and returns the result.
"""

from fastapi import APIRouter, Request, HTTPException
import structlog
import traceback

from app.integrations.shopify_client import ShopifyClient
from app.integrations.zoho_desk import ZohoDesk
from app.core.rag.retriever import rag
from app.core.cache import redis_manager

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/eleven/webhook")
async def eleven_webhook(request: Request):
    """
    Handles tool calls from ElevenLabs Conversational AI.
    Expected JSON payload format from ElevenLabs:
    {
       "tool_name": "name_of_tool",
       "parameters": {
           "param1": "value1"
       }
    }
    """
    try:
        payload = await request.json()
        logger.info("eleven_webhook_received", payload=payload)
        
        tool_name = payload.get("tool_name")
        params = payload.get("parameters", {})
        
        if not tool_name:
            # Maybe it's a different structure, log it
            return {"status": "error", "message": "Missing tool_name in payload"}

        # Route to appropriate tool function
        if tool_name == "check_order_status":
            order_id = params.get("order_id", "")
            return await _tool_check_order_status(order_id)
            
        elif tool_name == "search_knowledge_base":
            query = params.get("query", "")
            return await _tool_search_knowledge_base(query)
            
        elif tool_name == "escalate_to_human":
            reason = params.get("reason", "Customer requested human agent.")
            call_id = params.get("call_id", "eleven_call")
            return await _tool_escalate_to_human(call_id, reason)
            
        elif tool_name == "authenticate_customer":
            customer_id = params.get("customer_id", "")
            return await _tool_authenticate_customer(customer_id)
            
        else:
            logger.warning("unknown_tool_called", tool=tool_name)
            return {"status": "error", "message": f"Tool '{tool_name}' is not supported by backend."}
            
    except Exception as e:
        logger.error("eleven_webhook_error", error=str(e), traceback=traceback.format_exc())
        return {"status": "error", "message": "Internal Server Error during tool execution."}


# ── Tool Implementations ──────────────────────────────────────────────────────

async def _tool_check_order_status(order_id: str) -> dict:
    try:
        shopify = ShopifyClient()
        # You can use the order_id directly here if shopify_client supports it
        # Or pass a mock query text that the client parses
        result = await shopify.get_order_status(f"my order is {order_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_search_knowledge_base(query: str) -> dict:
    try:
        citations = await rag.search(query=query)
        context = rag.build_context_prompt(citations)
        if not context.strip():
            context = "No relevant policies found in the knowledge base."
        return {"status": "success", "context": context}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_escalate_to_human(call_id: str, reason: str) -> dict:
    try:
        await redis_manager.publish("human.escalation", {
            "call_id": call_id,
            "intent": "eleven_escalation",
            "transcript": "Transcript available in ElevenLabs.",
            "reason": reason,
        })
        return {"status": "success", "message": "Call has been escalated to the human dashboard."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_authenticate_customer(customer_id: str) -> dict:
    try:
        zoho = ZohoDesk()
        # Mocking auth logic
        return {
            "status": "success", 
            "is_authenticated": True, 
            "customer_details": {
                "name": f"Customer_{customer_id}",
                "vip_status": False
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
