"""Order Status Agent — tracks orders via NimbusPost + courier APIs."""
from langchain_core.messages import AIMessage
import structlog

from app.agents.state import CallState
from app.agents.base_business_agent import run_business_agent, _get_last_user_text
from app.integrations.shopify_client import ShopifyClient

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an order tracking specialist for Ambrane.
Help customers with:
- Order status and tracking
- Shipment updates and ETA
- Delivery confirmation
- RTO (Return to Origin) status — when delivery has failed and order is returning
- Missing/delayed delivery issues
- NDR (Non-Delivery Report) — when courier couldn't deliver

To check order: ask for order ID or tracking number.
Tracking is done via Shopify integration.
If order is delayed beyond expected date, offer to escalate to logistics team.
If RTO detected (order returning to warehouse), proactively inform customer and offer re-order or refund.
If NDR found, explain the delivery failure reason and next steps.
"""


async def order_status_agent(state: CallState) -> dict:
    """
    Extended agent that:
    1. Tries to extract order ID from conversation
    2. Calls NimbusPost API for live tracking data
    3. Augments LLM response with real tracking info
    """
    call_id = state.get("call_id", "unknown")
    language = state.get("intelligence", {}).get("language", "en")

    # Try to extract order ID from conversation
    last_text = _get_last_user_text(state.get("messages", []))
    order_id = _extract_order_id(last_text)
    tracking_id = _extract_tracking_id(last_text)

    tracking_context = ""

    if order_id or tracking_id:
        shopify = ShopifyClient()
        try:
            # We'll prioritize order_id if available, fallback to tracking_id
            search_val = order_id if order_id else tracking_id
            data = await shopify.get_order_status(search_val)

            tracking_context = _format_tracking_data(data, language)
            logger.info("shopify_data_fetched", call_id=call_id,
                        status=data.get("status"))
        except Exception as e:
            logger.error("shopify_fetch_error", error=str(e))
            tracking_context = ""

    # If we have live tracking data, inject it into messages as context
    if tracking_context:
        from langchain_core.messages import SystemMessage
        extra_context = SystemMessage(
            content=f"[LIVE TRACKING DATA FROM SHOPIFY]\n{tracking_context}"
        )
        state_copy = dict(state)
        state_copy["messages"] = list(state.get("messages", [])) + [extra_context]
        return await run_business_agent(state_copy, "order_status", SYSTEM_PROMPT, "faq")

    return await run_business_agent(state, "order_status", SYSTEM_PROMPT, "faq")


def _extract_order_id(text: str) -> str | None:
    """Extract Ambrane order ID pattern from text (e.g. AMB-12345, ORD123456)."""
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


def _extract_tracking_id(text: str) -> str | None:
    """Extract courier tracking/AWB number from text."""
    import re
    patterns = [
        r"\b[A-Z]{2,4}\d{8,15}\b",
        r"\b\d{12,15}\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None


def _format_tracking_data(data: dict, language: str) -> str:
    """Format Shopify response into a readable context string for LLM."""
    if data.get("status") == "error":
        return ""

    lines = [
        f"Order Name: {data.get('order_name', 'N/A')}",
        f"Financial Status: {data.get('financial_status', 'Unknown')}",
        f"Fulfillment Status: {data.get('fulfillment_status', 'Unknown')}",
        f"Current Shipment Status: {data.get('status', 'Unknown')}",
        f"Courier Partner: {data.get('tracking_company', 'Unknown')}",
        f"Tracking Number: {data.get('tracking_number', 'N/A')}",
        f"Tracking Link: {data.get('tracking_url', 'N/A')}",
    ]

    return "\n".join(lines)
