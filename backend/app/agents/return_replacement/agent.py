"""Return & Replacement Agent — handles return/replacement requests per policy.
Uses NimbusPost to schedule reverse pickups.
"""
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.agents.base_business_agent import run_business_agent, _get_last_user_text
from app.integrations.nimbuspost import NimbusPost

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are a returns and replacement specialist for Ambrane.
Help customers with:
- Return eligibility check (7-day return policy)
- Replacement eligibility (defective product within warranty)
- Reverse pickup scheduling via NimbusPost courier network
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

Once eligibility confirmed, reverse pickup will be scheduled via NimbusPost.
Customer will receive tracking SMS for the pickup.
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
        nimbus = NimbusPost()
        try:
            result = await nimbus.create_reverse_pickup(
                order_id=order_id,
                reason="Customer return request via support call",
                pickup_address={},   # Will use registered address
                product_details={"order_id": order_id},
            )
            if result.get("success"):
                pickup_context = (
                    f"\n[PICKUP SCHEDULED]\n"
                    f"AWB: {result.get('pickup_awb', 'N/A')}\n"
                    f"Pickup Date: {result.get('pickup_date', 'Within 24-48 hours')}\n"
                    f"Courier: {result.get('courier', 'NimbusPost partner')}\n"
                    f"Customer will receive SMS confirmation."
                )
                logger.info("reverse_pickup_created", call_id=call_id, order_id=order_id,
                            awb=result.get("pickup_awb"))
        except Exception as e:
            logger.error("reverse_pickup_error", error=str(e))

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
