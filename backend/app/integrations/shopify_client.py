"""
Shopify Admin API Client for Warranty and Order tracking.
"""

import httpx
import structlog
from typing import Optional, Dict, Any
from app.config import settings

logger = structlog.get_logger(__name__)


class ShopifyClient:
    def __init__(self):
        self.shop_url = settings.SHOPIFY_SHOP_URL
        self.access_token = settings.SHOPIFY_ACCESS_TOKEN
        
    @property
    def is_configured(self) -> bool:
        return bool(self.shop_url and self.access_token)
        
    async def get_customer_orders(self, phone_number: str) -> list:
        """Fetch a customer's recent orders from Shopify by phone number."""
        if not self.is_configured:
            logger.warning("shopify_not_configured_returning_mock")
            # Mock response if not configured
            return [
                {
                    "id": "MOCK-ORDER-999",
                    "name": "#1099",
                    "financial_status": "paid",
                    "fulfillment_status": "fulfilled",
                    "created_at": "2024-01-15T10:00:00Z",
                    "line_items": [
                        {"title": "Ambrane 20000mAh Power Bank", "sku": "PB-20K-BLK", "warranty_months": 12}
                    ]
                }
            ]

        # Clean the phone number (remove + if necessary, ensure format matches Shopify)
        clean_phone = phone_number.replace(" ", "")
        if not clean_phone.startswith("+"):
            clean_phone = f"+91{clean_phone}" if len(clean_phone) == 10 else f"+{clean_phone}"

        url = f"https://{self.shop_url}/admin/api/2024-01/customers/search.json"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Find customer by phone
                res = await client.get(url, params={"query": f"phone:{clean_phone}"}, headers=headers, timeout=10.0)
                res.raise_for_status()
                customers = res.json().get("customers", [])
                
                if not customers:
                    return []
                    
                customer_id = customers[0]["id"]
                
                # Fetch their orders
                orders_url = f"https://{self.shop_url}/admin/api/2024-01/customers/{customer_id}/orders.json"
                orders_res = await client.get(orders_url, headers=headers, timeout=10.0)
                orders_res.raise_for_status()
                
                return orders_res.json().get("orders", [])
                
        except Exception as e:
            logger.error("shopify_fetch_error", error=str(e), phone=phone_number)
            return []

    async def check_warranty_status(self, phone_number: str) -> Dict[str, Any]:
        """
        Check if any recent product bought by this phone number is still under warranty.
        Returns a summary dictionary suitable for the AI to read.
        """
        orders = await self.get_customer_orders(phone_number)
        
        if not orders:
            return {"status": "no_purchases_found", "message": "No purchases found for this phone number."}
            
        from datetime import datetime, timezone
        from dateutil import parser
        
        now = datetime.now(timezone.utc)
        warranty_items = []
        
        for order in orders:
            order_date_str = order.get("created_at")
            if not order_date_str:
                continue
                
            try:
                order_date = parser.parse(order_date_str)
            except:
                continue
                
            # Default to 12 months if not specified in SKU/metafields
            # In a real setup, you might fetch product metafields for exact warranty duration
            for item in order.get("line_items", []):
                warranty_months = item.get("warranty_months", 12) 
                
                # Calculate months elapsed
                delta = now - order_date
                months_elapsed = delta.days / 30.44
                
                is_active = months_elapsed <= warranty_months
                
                warranty_items.append({
                    "product": item.get("title"),
                    "order_name": order.get("name"),
                    "purchase_date": order_date.strftime("%Y-%m-%d"),
                    "warranty_status": "Active" if is_active else "Expired",
                    "months_remaining": max(0, round(warranty_months - months_elapsed, 1))
                })
                
        if not warranty_items:
             return {"status": "no_warranty_items_found", "message": "No eligible warranty products found."}
             
        # Sort by most recent purchase
        warranty_items.sort(key=lambda x: x["purchase_date"], reverse=True)
        
        return {
            "status": "success",
            "items": warranty_items
        }
