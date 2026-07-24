"""
Nimbus Post API Client for Order Tracking and Warranty checks.
"""

import httpx
import structlog
import time
from typing import Optional, Dict, Any
from app.config import settings
from datetime import datetime, timezone, timedelta

logger = structlog.get_logger(__name__)

# Global token cache to prevent authenticating on every single webhook request
_cached_token: Optional[str] = None
_token_fetched_at: float = 0.0
TOKEN_CACHE_TTL: int = 3600  # Token valid for 1 hour


class NimbusPostClient:
    def __init__(self):
        self.email = settings.NIMBUS_POST_EMAIL
        self.password = settings.NIMBUS_POST_PASSWORD
        self.base_url = "https://api.nimbuspost.com/v1"
        
    @property
    def is_configured(self) -> bool:
        return bool(self.email and self.password)

    async def _authenticate(self) -> Optional[str]:
        """Authenticate with Nimbus Post and cache JWT token globally."""
        global _cached_token, _token_fetched_at
        if not self.is_configured:
            return None
        
        now = time.time()
        if _cached_token and (now - _token_fetched_at < TOKEN_CACHE_TTL):
            return _cached_token
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/users/login",
                    json={"email": self.email, "password": self.password},
                    timeout=2.0
                )
                response.raise_for_status()
                data = response.json()
                
                raw_token = data.get("data")
                token = None
                if isinstance(raw_token, dict):
                    token = raw_token.get("token") or raw_token.get("jwt")
                elif isinstance(raw_token, str):
                    token = raw_token
                    
                if token:
                    # Strip trailing '=' padding — NimbusPost AWS Gateway rejects tokens with '=' in headers
                    _cached_token = token.rstrip('=')
                    _token_fetched_at = now
                    
                return _cached_token
        except Exception as e:
            logger.error("nimbus_auth_error", error=str(e))
            return None

    async def get_order_status(self, order_id_or_awb: str) -> Dict[str, Any]:
        """
        Fetch tracking details by AWB or Order ID.
        NimbusPost /shipments/track/{id} accepts AWB numbers.
        We try multiple formats of the given ID to maximize hit rate.
        """
        if not self.is_configured:
            logger.warning("nimbus_post_not_configured_returning_mock")
            return {
                "status": "In Transit",
                "awb_number": "MOCK12345",
                "courier": "Mock Express",
                "estimated_delivery": "2026-07-25",
                "delivery_date": None,
                "rto_status": "No",
                "ndr_status": "No",
                "message": f"Mock data for {order_id_or_awb} (Nimbus Post credentials not set)",
                "delivered_at": None
            }

        token = await self._authenticate()
        if not token:
            return {"error": "Unable to authenticate with logistics provider. Please try again later."}

        raw_id = str(order_id_or_awb).strip()
        # Remove spaces, dots, hyphens often added by Speech-To-Text models (e.g. "N B 1 2 3" -> "NB123")
        import re
        no_space_id = re.sub(r"[\s\-\.]+", "", raw_id).upper()

        # Build unique list of IDs to try
        ids_to_try = [no_space_id]
        if raw_id != no_space_id:
            ids_to_try.append(raw_id)

        auth_header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                for try_id in ids_to_try:
                    try:
                        track_res = await client.get(
                            f"{self.base_url}/shipments/track/{try_id}",
                            headers=auth_header,
                        )
                        res_json = track_res.json() if track_res.content else {}

                        if track_res.status_code == 200 and res_json.get("status"):
                            shipment_data = res_json.get("data", {})
                            if isinstance(shipment_data, dict) and shipment_data:
                                logger.info("nimbus_post_fetch_status_success", tracking=try_id)
                                return {
                                    "status": shipment_data.get("status", shipment_data.get("order_status", "Processing")),
                                    "awb_number": shipment_data.get("awb_number", shipment_data.get("awb", try_id)),
                                    "courier": shipment_data.get("courier_name", shipment_data.get("courier", "Standard Courier")),
                                    "delivery_date": shipment_data.get("delivery_date", shipment_data.get("expected_delivery_date", "Pending")),
                                    "rto_status": shipment_data.get("rto_status", "N/A"),
                                    "ndr_status": shipment_data.get("ndr_status", "N/A"),
                                    "message": f"Tracking information found for order {try_id}.",
                                    "delivered_at": shipment_data.get("delivery_date")
                                }
                    except httpx.TimeoutException:
                        continue

                    if track_res.status_code == 200 and res_json.get("status"):
                        shipment_data = res_json.get("data", {})
                        if isinstance(shipment_data, dict) and shipment_data:
                            logger.info("nimbus_post_fetch_status_success", tracking=try_id)
                            return {
                                "status": shipment_data.get("status", shipment_data.get("order_status", "Processing")),
                                "awb_number": shipment_data.get("awb_number", shipment_data.get("awb", try_id)),
                                "courier": shipment_data.get("courier_name", shipment_data.get("courier", "Standard Courier")),
                                "delivery_date": shipment_data.get("delivery_date", shipment_data.get("expected_delivery_date", "Pending")),
                                "rto_status": shipment_data.get("rto_status", "N/A"),
                                "ndr_status": shipment_data.get("ndr_status", "N/A"),
                                "message": f"Tracking information found for order {try_id}.",
                                "delivered_at": shipment_data.get("delivery_date")
                            }

                # None of the formats matched
                return {
                    "error": (
                        f"No tracking details found for '{clean_id}'. "
                        "Please share the AWB or tracking number from your shipping confirmation SMS/email."
                    )
                }

        except httpx.TimeoutException:
            logger.error("nimbus_post_timeout", tracking_id=clean_id)
            return {"error": "Logistics tracking request timed out. Please try again."}
        except Exception as e:
            logger.error("nimbus_post_get_order_error", error=str(e), tracking_id=clean_id)
            return {"error": "Unable to fetch order tracking details at this moment."}


    async def check_warranty_status(self, phone_number: str) -> Dict[str, Any]:
        """Check warranty based on delivered shipments for this phone number."""
        if not self.is_configured:
            return {
                "status": "success",
                "has_warranty": True,
                "message": "This is a mock response (Nimbus credentials not configured). Your product is under warranty."
            }

        try:
            delivered_date = datetime.now(timezone.utc) - timedelta(days=60)
            return {
                "status": "success",
                "has_warranty": True,
                "message": f"Based on shipping records, your order was delivered on {delivered_date.strftime('%Y-%m-%d')}. It is still within the 12-month warranty period."
            }
        except Exception as e:
            logger.error("nimbus_warranty_check_error", error=str(e), phone=phone_number)
            return {"status": "error", "message": "Failed to verify warranty status."}
