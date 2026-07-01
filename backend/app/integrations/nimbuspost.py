"""
NimbusPost Integration Client
NimbusPost is a courier aggregator platform used by Ambrane for:
- Order tracking across multiple courier partners
- Shipment creation and management
- Return/reverse pickup scheduling
- NDR (Non-Delivery Report) management

API Docs: https://api.nimbuspost.com/
"""

import httpx
import structlog
from typing import Optional
from app.config import settings

logger = structlog.get_logger(__name__)


class NimbusPost:
    """
    Async client for NimbusPost courier aggregator API.
    Handles order tracking, shipment status, and return pickups.
    """

    def __init__(self):
        self.base_url = settings.NIMBUSPOST_BASE_URL
        self.api_key = settings.NIMBUSPOST_API_KEY
        self._token: Optional[str] = None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ── Order Tracking ─────────────────────────────────────────────────────────

    async def track_shipment(self, tracking_id: str) -> dict:
        """
        Track a shipment by AWB/tracking number.
        Returns status, location, estimated delivery, and event history.
        """
        if not self.api_key:
            logger.warning("nimbuspost_not_configured")
            return self._mock_tracking(tracking_id)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/tracking/{tracking_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "tracking_id": tracking_id,
                    "status": data.get("status", "unknown"),
                    "current_location": data.get("current_location", ""),
                    "eta": data.get("estimated_delivery", ""),
                    "courier": data.get("courier_name", ""),
                    "events": data.get("tracking_events", []),
                    "is_rto": data.get("is_rto", False),
                }
        except Exception as e:
            logger.error("nimbuspost_track_error", tracking_id=tracking_id, error=str(e))
            return {"tracking_id": tracking_id, "status": "error", "message": str(e)}

    async def get_order_status(self, order_id: str) -> dict:
        """
        Get order status by Ambrane order ID.
        Looks up the shipment associated with this order.
        """
        if not self.api_key:
            return self._mock_order_status(order_id)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "order_id": order_id,
                    "status": data.get("order_status", "unknown"),
                    "tracking_id": data.get("awb_number", ""),
                    "courier": data.get("courier_name", ""),
                    "shipped_at": data.get("shipped_date", ""),
                    "expected_delivery": data.get("expected_delivery", ""),
                    "delivery_address": data.get("delivery_address", {}),
                    "is_rto": data.get("is_rto", False),
                    "rto_reason": data.get("ndr_reason", ""),
                }
        except Exception as e:
            logger.error("nimbuspost_order_error", order_id=order_id, error=str(e))
            return {"order_id": order_id, "status": "error", "message": str(e)}

    # ── Return / Reverse Pickup ────────────────────────────────────────────────

    async def create_reverse_pickup(
        self,
        order_id: str,
        reason: str,
        pickup_address: dict,
        product_details: dict,
    ) -> dict:
        """
        Schedule a reverse pickup (return) for an order.
        Returns: pickup AWB number and scheduled date.
        """
        if not self.api_key:
            return {"success": False, "message": "NimbusPost not configured"}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.base_url}/reverse-pickup",
                    headers=self._headers(),
                    json={
                        "reference_order_id": order_id,
                        "return_reason": reason,
                        "pickup_address": pickup_address,
                        "product": product_details,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "success": True,
                    "pickup_awb": data.get("awb_number", ""),
                    "pickup_date": data.get("pickup_date", ""),
                    "courier": data.get("courier_name", ""),
                    "message": "Reverse pickup scheduled successfully.",
                }
        except Exception as e:
            logger.error("nimbuspost_reverse_error", order_id=order_id, error=str(e))
            return {"success": False, "message": str(e)}

    async def get_ndr_details(self, tracking_id: str) -> dict:
        """
        Get NDR (Non-Delivery Report) details for a failed delivery.
        NDR contains reason for failure and action options.
        """
        if not self.api_key:
            return {}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/ndr/{tracking_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("nimbuspost_ndr_error", tracking_id=tracking_id, error=str(e))
            return {}

    # ── Mock responses (when API not configured) ───────────────────────────────

    def _mock_tracking(self, tracking_id: str) -> dict:
        """Returns demo data when NimbusPost is not yet configured."""
        return {
            "tracking_id": tracking_id,
            "status": "in_transit",
            "current_location": "Delhi Hub",
            "eta": "Tomorrow by 9 PM",
            "courier": "Delhivery",
            "events": [
                {"status": "Picked Up", "location": "Warehouse", "time": "Yesterday 10:00 AM"},
                {"status": "In Transit", "location": "Delhi Hub", "time": "Today 6:00 AM"},
            ],
            "is_rto": False,
            "_note": "DEMO DATA — configure NIMBUSPOST_API_KEY in .env",
        }

    def _mock_order_status(self, order_id: str) -> dict:
        return {
            "order_id": order_id,
            "status": "shipped",
            "tracking_id": "DEMO123456",
            "courier": "Delhivery",
            "expected_delivery": "Tomorrow",
            "is_rto": False,
            "_note": "DEMO DATA — configure NIMBUSPOST_API_KEY in .env",
        }
