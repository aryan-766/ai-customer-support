"""Return & Replacement Agent — handles return/replacement requests per policy.
Uses NimbusPost to schedule reverse pickups.
"""
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.agents.base_business_agent import run_business_agent, _get_last_user_text
from app.integrations.zoho_desk import ZohoDesk

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a returns and replacement specialist for Ambrane.
Help customers with:
- Return eligibility check (7-day return policy)
- Replacement eligibility (defective product within warranty)
- Reverse pickup scheduling by creating a Zoho Desk ticket
- Replacement order creation

Ambrane Return Policy:
- 7 days from delivery for returns
- Product must be unused and in original packaging
- Some categories excluded (check policy)

Replacement Policy:
- Defective within 7 days: replacement
- Defective within warranty: repair or replacement
- Physical damage: not eligible

To process a return/replacement, collect:
1. Order ID
2. Reason for return/replacement
3. Product condition
4. Pickup address (if different from delivery address)

Once eligibility confirmed, a reverse pickup ticket will be logged via Zoho Desk.
Customer will be contacted by our logistics team for pickup.
Always check policy using knowledge base before confirming eligibility [citation_id].
"""


async def return_replacement_agent(state: CallState) -> dict:
    """
    Extended agent that:
    1. Checks eligibility from policy (via RAG)
    2. If eligible and customer confirms, schedules NimbusPost reverse pickup
    3. Returns structured response with pickup details
    """
    call_id = state.get("call_id", "unknown")
    last_text = _get_last_user_text(state.get("messages", []))

    # Check if customer is explicitly confirming a pickup request
    confirm_keywords = ["yes", "confirm", "schedule", "pickup", "haan", "ok", "theek hai"]
    customer_confirming = any(kw in last_text.lower() for kw in confirm_keywords)

    # Get call state for order context
    state_data = state.get("escalation_context", {})
    order_id = _extract_order_id(last_text) or state_data.get("order_id")

    pickup_context = ""
    if customer_confirming and order_id:
        zoho = ZohoDesk()
        try:
            # Create a Zoho Desk ticket for logistics team to handle the return pickup
            ticket_id = await zoho.create_ticket(
                subject=f"Reverse Pickup Request - Order {order_id}",
                description=f"Customer requested reverse pickup via voice support for order {order_id}.",
                customer_email="customer@example.com", # Placeholder
                priority="high",
                department="Logistics",
                call_id=call_id,
            )
            if ticket_id:
                pickup_context = (
                    f"\n[PICKUP REQUEST LOGGED]\n"
                    f"Ticket ID: {ticket_id}\n"
                    f"Status: Sent to logistics team.\n"
                    f"Customer will receive confirmation shortly."
                )
                logger.info("reverse_pickup_ticket_created", call_id=call_id, order_id=order_id,
                            ticket_id=ticket_id)
        except Exception as e:
            logger.error("reverse_pickup_ticket_error", error=str(e))

    # Inject pickup info if available
    if pickup_context:
        from langchain_core.messages import SystemMessage
        state_copy = dict(state)
        state_copy["messages"] = list(state.get("messages", [])) + [
            SystemMessage(content=pickup_context)
        ]
        return await run_business_agent(state_copy, "return_replacement", SYSTEM_PROMPT, "policy")

    return await run_business_agent(state, "return_replacement", SYSTEM_PROMPT, "policy")


def _extract_order_id(text: str) -> str | None:
    import re
    patterns = [
        r"\bAMB[-\s]?\d{5,10}\b",
        r"\bORD[-\s]?\d{5,10}\b",
        r"\border[:\s]+(\d{6,12})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group().strip()
    return None
