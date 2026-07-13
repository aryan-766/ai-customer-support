"""
FastMCP server for CRM and Support tools.
"""

from fastmcp import FastMCP
from typing import Optional, Dict, Any
from app.integrations.zoho_desk import ZohoDesk
from app.integrations.shopify_client import ShopifyClient
from app.core.rag.retriever import rag

# Create the MCP server for CRM operations
crm_mcp = FastMCP("Ambrane-Enterprise-Support")

# --- Zoho Desk Tools ---

@crm_mcp.tool()
async def zoho_create_ticket_tool(
    subject: str, 
    description: str, 
    customer_email: str, 
    priority: str = "medium",
    call_id: str = "",
    ai_summary: str = ""
) -> str:
    """Create a new ticket in Zoho Desk."""
    zoho = ZohoDesk()
    ticket_id = await zoho.create_ticket(
        subject=subject,
        description=description,
        customer_email=customer_email,
        priority=priority,
        call_id=call_id,
        ai_summary=ai_summary
    )
    if ticket_id:
        return f"Ticket created successfully with ID: {ticket_id}"
    return "Failed to create ticket."

@crm_mcp.tool()
async def zoho_lookup_contact_tool(search_value: str) -> Dict[str, Any]:
    """Look up a customer contact in Zoho Desk by email, phone, or ID."""
    zoho = ZohoDesk()
    contact = await zoho.search_contact(search_value)
    if contact:
        return {"found": True, "contact": contact}
    return {"found": False, "message": "Contact not found."}

@crm_mcp.tool()
async def zoho_update_ticket_tool(ticket_id: str, description: str, status: str = "Open") -> str:
    """Update an existing Zoho Desk ticket description and status."""
    zoho = ZohoDesk()
    success = await zoho.update_ticket_summary(ticket_id, description, status)
    if success:
        return f"Ticket {ticket_id} updated successfully."
    return f"Failed to update ticket {ticket_id}."

# --- Shopify API Tools ---

@crm_mcp.tool()
async def shopify_order_status_tool(customer_phone: str) -> str:
    """Check the status of a customer's recent orders using Shopify API."""
    shopify = ShopifyClient()
    orders = await shopify.get_customer_orders(customer_phone)
    if orders:
        latest = orders[0]
        return (f"Found order {latest.get('name')}. "
                f"Financial status: {latest.get('financial_status')}. "
                f"Fulfillment status: {latest.get('fulfillment_status')}.")
    return "No recent orders found."

@crm_mcp.tool()
async def shopify_tracking_tool(order_name: str) -> Dict[str, Any]:
    """Get tracking and shipping information for a specific Shopify order."""
    shopify = ShopifyClient()
    status = await shopify.get_order_status(order_name)
    return status

# --- RAG & Logic Tools ---

@crm_mcp.tool()
async def knowledge_search_tool(query: str, category: Optional[str] = None) -> str:
    """Search the Qdrant knowledge base for policies, manuals, or FAQ."""
    citations = await rag.search(query=query, category=category)
    return rag.build_context_prompt(citations)

@crm_mcp.tool()
async def human_handoff_tool(reason: str) -> str:
    """Trigger a handoff to a live human agent."""
    # In practice, LangGraph routing handles this, but returning this token helps the agent explicitly signal it
    return "[ESCALATE] Triggering human handoff due to: " + reason
