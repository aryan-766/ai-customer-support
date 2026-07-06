"""
Business Agents for LangGraph.
Each agent handles a specific domain and has access to specific FastMCP tools.
"""

from langchain_core.messages import AIMessage, HumanMessage
import structlog
from app.agents.state import CallState
from app.core.llm.factory import LLMFactory
from app.tools import crm_mcp, rag_mcp, utility_mcp

logger = structlog.get_logger(__name__)

async def _generic_agent(state: CallState, role_prompt: str, tools_list: list) -> dict:
    """Helper to run a generic agent with specific prompt and tools."""
    llm = LLMFactory.get_provider()
    
    # In a real implementation, we would bind tools to the LLM here.
    # Ollama integration needs to support tool calling, or we manually parse.
    # For this demo, we'll construct a prompt that asks the LLM to respond.
    
    transcript = state.get("transcript", [])
    recent_text = "\n".join([f"{t['speaker']}: {t['text']}" for t in transcript[-5:]])
    
    # Inject Zoho Ticket History
    customer = state.get("customer_context", {})
    recent_tickets = customer.get("recent_tickets", [])
    ticket_history = ""
    if recent_tickets:
        ticket_history = "CUSTOMER RECENT SUPPORT TICKETS (Zoho Desk):\n"
        for t in recent_tickets:
            ticket_history += f"- Ticket {t.get('ticketNumber')}: {t.get('subject')} [{t.get('status')}]\n"
        ticket_history += "\n"
    
    system_prompt = f"{role_prompt}\n\n{ticket_history}Recent conversation:\n{recent_text}\n\nRespond conversationally as an AI voice assistant. Keep it concise."
    
    try:
        response = await llm.generate(
            prompt="Respond to the user.",
            system=system_prompt
        )
        
        return {
            "messages": [AIMessage(content=response.text)],
            "active_agent": "completed"
        }
    except Exception as e:
        logger.error("agent_execution_failed", error=str(e))
        return {
            "messages": [AIMessage(content="I'm having trouble connecting right now. Please hold.")],
            "escalate": True
        }


async def faq_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane FAQ Agent. Answer general questions using the knowledge base."
    return await _generic_agent(state, prompt, [])

async def order_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Order Support Agent. Help the user check their order status.\n\n"
    
    # Try to fetch Shopify Order Status Context
    customer = state.get("customer_context", {})
    phone = customer.get("mobile")
    
    if phone:
        from app.integrations.shopify_client import ShopifyClient
        shopify = ShopifyClient()
        orders = await shopify.get_customer_orders(phone)
        if orders:
            order = orders[0]  # Most recent
            prompt += f"LATEST SHOPIFY ORDER DATA:\nOrder Name: {order.get('name')}\nStatus: {order.get('fulfillment_status', 'Processing')}\nItems: {', '.join([i.get('title') for i in order.get('line_items', [])])}\n\n"
        else:
            prompt += "LATEST SHOPIFY ORDER DATA:\nNo recent orders found in Shopify.\n\n"
            
    # Placeholder for future OMS (e.g. NimbusPost) order tracking logic
    prompt += "[Future OMS Tracking Status: Pending Integration]\n\n"
    
    return await _generic_agent(state, prompt, [])

async def complaint_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Complaint Resolution Agent. Be empathetic and register their complaint."
    return await _generic_agent(state, prompt, [])

async def tech_support_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Technical Support Agent. Help troubleshoot device issues and handle warranty queries.\n\n"
    
    # Try to fetch Shopify Warranty Context
    customer = state.get("customer_context", {})
    phone = customer.get("mobile")
    
    if phone:
        from app.integrations.shopify_client import ShopifyClient
        shopify = ShopifyClient()
        warranty_info = await shopify.check_warranty_status(phone)
        prompt += f"SHOPIFY WARRANTY STATUS FOR THIS CUSTOMER:\n{warranty_info}\n\n"
        
    return await _generic_agent(state, prompt, [])

async def registration_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Registration Agent. Help the user register their product or account."
    return await _generic_agent(state, prompt, [])

async def sales_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Sales Agent. Help the user choose a product to buy."
    return await _generic_agent(state, prompt, [])

