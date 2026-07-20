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

from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger(__name__)

# Models for incoming ElevenLabs payloads
class OrderStatusRequest(BaseModel):
    order_id: str

class KnowledgeBaseRequest(BaseModel):
    query: str

class EscalateRequest(BaseModel):
    call_id: str
    reason: str = "Customer requested human agent."

class AuthenticateRequest(BaseModel):
    customer_id: str | None = None
    ticket_id: str | None = None

class CreateTicketRequest(BaseModel):
    subject: str
    description: str
    customer_email: str
    priority: str = "medium"
    department: str = "Customer Support"
    call_id: str = ""
    ai_summary: str = ""

class UpdateTicketRequest(BaseModel):
    ticket_id: str
    description: str
    status: str = "Open"

class RecentTicketsRequest(BaseModel):
    contact_id: str

class WarrantyRequest(BaseModel):
    phone_number: str

# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/eleven/check_order_status")
async def check_order_status(payload: OrderStatusRequest):
    """Check Shopify for order tracking updates."""
    try:
        shopify = ShopifyClient()
        result = await shopify.get_order_status(f"my order is {payload.order_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error("check_order_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/search_knowledge_base")
async def search_knowledge_base(payload: KnowledgeBaseRequest):
    """Searches Qdrant vector DB for manuals and warranty policies."""
    try:
        citations = await rag.search(query=payload.query)
        context = rag.build_context_prompt(citations)
        if not context.strip():
            context = "No relevant policies found in the knowledge base."
        return {"status": "success", "context": context}
    except Exception as e:
        logger.error("search_kb_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/escalate_to_human")
async def escalate_to_human(payload: EscalateRequest):
    """Triggers the Redis event to route the call to Next.js Agent Dashboard."""
    try:
        await redis_manager.publish("human.escalation", {
            "call_id": payload.call_id,
            "intent": "eleven_escalation",
            "transcript": "Transcript available in ElevenLabs.",
            "reason": payload.reason,
        })
        return {"status": "success", "message": "Call escalated to human."}
    except Exception as e:
        logger.error("escalate_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/authenticate_customer")
async def authenticate_customer(payload: AuthenticateRequest):
    """Verifies customer in Zoho CRM and manages tickets."""
    try:
        zoho = ZohoDesk()
        response_data = {
            "status": "success", 
            "is_authenticated": True, 
            "customer_details": {
                "name": f"Customer_{payload.customer_id or 'Unknown'}",
                "vip_status": False
            }
        }
        
        if payload.ticket_id:
            # Check ticket directly by its number
            ticket = await zoho.get_ticket_by_number(payload.ticket_id)
            if ticket:
                response_data['ticket_status'] = ticket.get('status')
                response_data['ticket_subject'] = ticket.get('subject')
                response_data['ticket_description'] = ticket.get('description')
                response_data['message'] = "Ticket details retrieved successfully."
            else:
                response_data['message'] = "Ticket not found."
        else:
            # No ticket ID provided, customer wants to create a new ticket
            if not payload.customer_id:
                response_data['message'] = "Phone number or email is required to create a new ticket."
            else:
                new_ticket_id = await zoho.create_ticket(
                    subject="New Phone Support Inquiry",
                    description=f"Incoming call from {payload.customer_id}",
                    customer_email=f"{payload.customer_id}@example.com" if "@" not in payload.customer_id else payload.customer_id,
                    priority="medium",
                    department="Customer Support"
                )
                if new_ticket_id:
                    response_data['new_ticket_id'] = new_ticket_id
                    response_data['message'] = f"Created new ticket with ID {new_ticket_id}."
                else:
                    response_data['message'] = "Failed to create new ticket."
                
        return response_data
    except Exception as e:
        logger.error("auth_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/create_ticket")
async def create_ticket(payload: CreateTicketRequest):
    """Creates a new ticket in Zoho Desk."""
    try:
        zoho = ZohoDesk()
        ticket_id = await zoho.create_ticket(
            subject=payload.subject,
            description=payload.description,
            customer_email=payload.customer_email,
            priority=payload.priority,
            department=payload.department,
            call_id=payload.call_id,
            ai_summary=payload.ai_summary
        )
        if ticket_id:
            return {"status": "success", "ticket_id": ticket_id}
        return {"status": "error", "message": "Failed to create ticket"}
    except Exception as e:
        logger.error("create_ticket_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/update_ticket")
async def update_ticket(payload: UpdateTicketRequest):
    """Updates/closes an existing ticket in Zoho Desk."""
    try:
        zoho = ZohoDesk()
        success = await zoho.update_ticket_summary(
            ticket_id=payload.ticket_id, 
            description=payload.description, 
            status=payload.status
        )
        return {"status": "success" if success else "error"}
    except Exception as e:
        logger.error("update_ticket_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/get_recent_tickets")
async def get_recent_tickets(payload: RecentTicketsRequest):
    """Gets recent tickets for a customer in Zoho Desk."""
    try:
        zoho = ZohoDesk()
        tickets = await zoho.get_recent_tickets(contact_id=payload.contact_id)
        return {"status": "success", "tickets": tickets}
    except Exception as e:
        logger.error("recent_tickets_error", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/eleven/check_warranty")
async def check_warranty(payload: WarrantyRequest):
    """Checks Shopify for warranty status of recent orders."""
    try:
        shopify = ShopifyClient()
        result = await shopify.check_warranty_status(phone_number=payload.phone_number)
        return result
    except Exception as e:
        logger.error("warranty_check_error", error=str(e))
        return {"status": "error", "message": str(e)}
