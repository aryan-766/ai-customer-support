"""
ElevenLabs Conversational AI Webhook endpoint.
Simplified flow:
  - Authenticate via Ticket ID OR Order ID (NimbusPost)
  - If not found → auto-create ticket → ask query → update ticket
  - Order status tracked via Order ID / AWB
"""

from fastapi import APIRouter, Request
import structlog
from typing import Any

from app.integrations.nimbus_post_client import NimbusPostClient
from app.integrations.zoho_desk import ZohoDesk
from app.core.rag.retriever import rag
from app.core.cache import redis_manager

from pydantic import BaseModel

router = APIRouter()
logger = structlog.get_logger(__name__)


# ── Request Models ─────────────────────────────────────────────────────────────

class AuthenticateRequest(BaseModel):
    ticket_id: str | None = None   # Zoho Desk ticket number (e.g. "83097")
    order_id: str | None = None    # NimbusPost order / AWB number
    customer_id: str | None = None # Fallback field if ElevenLabs sends customer_id
    identifier: str | None = None  # Fallback field if ElevenLabs sends identifier

class CreateTicketRequest(BaseModel):
    subject: str = "Support Inquiry - Voice Call"
    description: str = "New customer support ticket created via Voice Agent."
    customer_name: str = "Voice Customer"
    customer_email: str = "voice@ambraneindia.in"
    priority: str = "medium"
    call_id: str = ""

class UpdateTicketRequest(BaseModel):
    ticket_id: str = ""
    query_description: str = "Customer inquiry details updated."
    status: str = "Open"

class OrderStatusRequest(BaseModel):
    order_id: str           # AWB or Order ID

class KnowledgeBaseRequest(BaseModel):
    query: str

class EscalateRequest(BaseModel):
    call_id: str
    reason: str = "Customer requested human agent."

class WarrantyRequest(BaseModel):
    phone_number: str

# ── Endpoints ──────────────────────────────────────────────────────────────────

def parse_spoken_number(val: str) -> str:
    """Convert spoken number words (e.g., 'eight nine five five six') or digits to clean digit string."""
    if not val:
        return ""
    
    word_map = {
        "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    }
    tokens = str(val).lower().replace("-", " ").replace(".", " ").split()
    digits = []
    for token in tokens:
        if token in word_map:
            digits.append(word_map[token])
        elif token.isdigit():
            digits.append(token)
        else:
            # Check individual characters if mixed
            for char in token:
                if char.isdigit():
                    digits.append(char)

    result = "".join(digits)
    return result if result else str(val).strip()


@router.post("/eleven/authenticate_customer")
async def authenticate_customer(request: Request):
    """
    Authenticate customer using ticket_id or order_id/AWB.
    Parses flat or nested payloads from ElevenLabs Webhooks.
    """
    import re
    try:
        data = await request.json()
    except Exception:
        data = {}

    logger.info("eleven_auth_incoming_payload", payload=data)
    print("ELEVEN AUTH INCOMING PAYLOAD:", data, flush=True)

    # Flatten nested payload if ElevenLabs wraps in 'body', 'params', 'data', etc.
    if "body" in data and isinstance(data["body"], dict):
        data = {**data, **data["body"]}
    if "params" in data and isinstance(data["params"], dict):
        data = {**data, **data["params"]}

    # Collect any provided identifier
    raw_val = (
        data.get("ticket_id")
        or data.get("order_id")
        or data.get("customer_id")
        or data.get("identifier")
        or data.get("query")
        or data.get("value")
    )

    if not raw_val:
        for k, v in data.items():
            if isinstance(v, str) and v.strip():
                raw_val = v
                break

    response: dict[str, Any] = {
        "status": "success",
        "is_authenticated": False,
        "auth_method": None,
        "ticket_details": None,
        "order_details": None,
        "create_new_ticket": False,
        "message": "",
    }

    if not raw_val:
        response["create_new_ticket"] = True
        response["message"] = (
            "No ticket or AWB number provided. "
            "Creating a new support ticket for you. "
            "Please describe your issue."
        )
        return response

    clean_id = parse_spoken_number(raw_val)
    raw_clean = str(raw_val).strip()
    logger.info("auth_clean_identifier_parsed", raw=raw_val, clean=clean_id)
    print(f"AUTH PARSED IDENTIFIER: raw='{raw_val}' -> clean='{clean_id}'", flush=True)

    zoho = ZohoDesk()
    nimbus = NimbusPostClient()

    # Step 1: If 6 digits or less, try Zoho Desk first
    if len(clean_id) <= 6 and clean_id.isdigit():
        try:
            ticket = await zoho.get_ticket_by_number(clean_id)
            if ticket:
                response["is_authenticated"] = True
                response["auth_method"] = "ticket_id"
                response["ticket_details"] = {
                    "zoho_id": ticket.get("id") or "",
                    "ticket_number": ticket.get("ticketNumber"),
                    "subject": ticket.get("subject"),
                    "status": ticket.get("status"),
                    "description": ticket.get("description") or "No previous description.",
                    "email": ticket.get("email", ""),
                }
                response["message"] = (
                    f"Ticket #{ticket.get('ticketNumber')} found. "
                    f"Subject: {ticket.get('subject')}. "
                    f"Status: {ticket.get('status')}. "
                    f"How can I help you today?"
                )
                return response
        except Exception as e:
            logger.error("auth_zoho_error", error=str(e))

    # Step 2: Try NimbusPost AWB Tracking (Try raw_clean first, then clean_id)
    for try_awb in [raw_clean, clean_id]:
        if not try_awb:
            continue
        try:
            order = await nimbus.get_order_status(try_awb)
            if "error" not in order:
                response["is_authenticated"] = True
                response["auth_method"] = "awb"
                response["order_details"] = order
                response["message"] = (
                    f"AWB '{try_awb}' found. "
                    f"Status: {order.get('status', 'Unknown')}. "
                    f"Courier: {order.get('courier', 'N/A')}. "
                    f"Expected delivery: {order.get('delivery_date', 'Pending')}. "
                    f"How can I assist you further?"
                )
                return response
        except Exception as e:
            logger.error("auth_nimbus_error", try_awb=try_awb, error=str(e))

    # Step 3: Fallback check Zoho Desk if not checked previously (>6 digits case)
    if len(clean_id) > 6:
        try:
            ticket = await zoho.get_ticket_by_number(clean_id)
            if ticket:
                response["is_authenticated"] = True
                response["auth_method"] = "ticket_id"
                response["ticket_details"] = {
                    "zoho_id": ticket.get("id") or "",
                    "ticket_number": ticket.get("ticketNumber"),
                    "subject": ticket.get("subject"),
                    "status": ticket.get("status"),
                    "description": ticket.get("description") or "No previous description.",
                    "email": ticket.get("email", ""),
                }
                response["message"] = (
                    f"Ticket #{ticket.get('ticketNumber')} found. "
                    f"Subject: {ticket.get('subject')}. "
                    f"Status: {ticket.get('status')}. "
                    f"How can I help you today?"
                )
                return response
        except Exception as e:
            logger.error("auth_zoho_fallback_error", error=str(e))

    # If neither Zoho nor Nimbus found anything
    response["create_new_ticket"] = True
    response["message"] = (
        f"Number '{clean_id}' not found in our ticket or shipping records. "
        "Creating a new support ticket for you right away."
    )
    return response


@router.post("/eleven/check_order_status")
async def check_order_status(request: Request):
    """
    Track a shipment by AWB number via NimbusPost.
    If AWB not found → returns escalate_to_human=True signal.
    """
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        raw_order = (
            data.get("order_id")
            or data.get("awb_number")
            or data.get("ticket_id")
            or data.get("identifier")
            or data.get("query")
            or data.get("value")
        )
        if not raw_order:
            for k, v in data.items():
                if isinstance(v, str) and v.strip():
                    raw_order = v
                    break

        raw_str = str(raw_order).strip() if raw_order else ""
        clean_awb = parse_spoken_number(raw_order) if raw_order else ""

        nimbus = NimbusPostClient()
        result = await nimbus.get_order_status(raw_str) if raw_str else {"error": "no_awb"}

        # Fallback to clean_awb if raw_str returned error and clean_awb is different
        if "error" in result and clean_awb and clean_awb != raw_str:
            result = await nimbus.get_order_status(clean_awb)

        if "error" in result:
            return {
                "status": "not_found",
                "escalate_to_human": True,
                "message": (
                    "I'm unable to track your order using the AWB number right now. "
                    "Let me connect you directly to our shipping team who can assist you further."
                ),
            }
        return {
            "status": "success",
            "escalate_to_human": False,
            "order_status": result.get("status"),
            "awb_number": result.get("awb_number"),
            "courier": result.get("courier"),
            "delivery_date": result.get("delivery_date"),
            "rto_status": result.get("rto_status"),
            "ndr_status": result.get("ndr_status"),
            "message": (
                f"Your order status is '{result.get('status')}'. "
                f"Courier: {result.get('courier', 'N/A')}. "
                f"Expected delivery: {result.get('delivery_date', 'Pending')}."
            ),
        }
    except Exception as e:
        logger.error("check_order_error", error=str(e))
        return {
            "status": "error",
            "escalate_to_human": True,
            "message": "Order details abhi available nahi hain. Aapko human agent se connect kar raha hun.",
        }


@router.post("/eleven/create_ticket")
async def create_ticket(request: Request):
    """
    Create a new Zoho Desk support ticket.
    Called when customer cannot be authenticated via ticket/order ID.
    Returns the new Zoho ticket ID (internal) for subsequent update_ticket calls.
    """
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        subject = data.get("subject") or "Support Inquiry - Voice Call"
        description = data.get("description") or "New customer support ticket created via Voice Agent."
        customer_name = data.get("customer_name") or "Voice Customer"
        customer_email = data.get("customer_email") or "voice@ambraneindia.in"
        priority = data.get("priority") or "medium"
        call_id = data.get("call_id") or ""

        zoho = ZohoDesk()
        ticket_id = await zoho.create_ticket(
            subject=subject,
            description=description,
            customer_email=customer_email,
            priority=priority,
            call_id=call_id,
            ai_summary=f"New ticket created via AI Voice Agent. Customer: {customer_name}.",
        )
        if ticket_id:
            return {
                "status": "success",
                "ticket_id": ticket_id,
                "message": (
                    f"A new support ticket has been created. "
                    f"Your reference ID is {ticket_id}. "
                    "Please go ahead and describe your issue."
                ),
            }
        return {"status": "error", "message": "Failed to create support ticket. Please try again."}
    except Exception as e:
        logger.error("create_ticket_error", error=str(e))
        return {"status": "error", "message": "Unable to create ticket at this time."}


@router.post("/eleven/update_ticket")
async def update_ticket(request: Request):
    """
    Update an existing ticket with the customer's query/description.
    Called after customer describes their issue.
    """
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        ticket_id = data.get("ticket_id") or ""
        query_description = data.get("query_description") or data.get("description") or data.get("query") or "Customer query updated."
        status = data.get("status") or "Open"

        zoho = ZohoDesk()
        success = await zoho.update_ticket_summary(
            ticket_id=ticket_id,
            description=query_description,
            status=status,
        )
        if success:
            return {
                "status": "success",
                "message": "Your query has been recorded in the ticket. Our support team will review it shortly.",
            }
        return {"status": "error", "message": "Failed to update ticket with your query."}
    except Exception as e:
        logger.error("update_ticket_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/eleven/search_knowledge_base")
async def search_knowledge_base(request: Request):
    """Search Qdrant vector DB for product manuals, warranty policies, FAQs."""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        query_str = data.get("query") or data.get("prompt") or data.get("question") or ""

        citations = await rag.search(query=query_str) if query_str else []
        context = rag.build_context_prompt(citations) if citations else "No relevant information found in the knowledge base."
        return {"status": "success", "context": context}
    except Exception as e:
        logger.error("search_kb_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/eleven/escalate_to_human")
async def escalate_to_human(request: Request):
    """Escalate call to a live human agent via Redis."""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        call_id = data.get("call_id") or "call_voice_123"
        reason = data.get("reason") or "Customer requested human agent."

        await redis_manager.publish("human.escalation", {
            "call_id": call_id,
            "intent": "eleven_escalation",
            "reason": reason,
        })
        return {"status": "success", "message": "Connecting you to a human agent. Please hold."}
    except Exception as e:
        logger.error("escalate_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/eleven/check_warranty")
async def check_warranty(request: Request):
    """Check warranty status via NimbusPost."""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        if "body" in data and isinstance(data["body"], dict):
            data = {**data, **data["body"]}
        if "params" in data and isinstance(data["params"], dict):
            data = {**data, **data["params"]}

        phone_number = data.get("phone_number") or data.get("phone") or ""

        nimbus = NimbusPostClient()
        result = await nimbus.check_warranty_status(phone_number=phone_number)
        return result
    except Exception as e:
        logger.error("check_warranty_error", error=str(e))
        return {"status": "error", "message": str(e)}
