"""Zoho Desk integration client."""
import httpx
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)


class ZohoDesk:
    def __init__(self):
        self.base_url = settings.ZOHO_DESK_URL
        self.org_id = settings.ZOHO_ORG_ID
        self._access_token: str | None = None

    async def _get_token(self) -> str:
        """Get OAuth2 access token using refresh token."""
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://accounts.zoho.in/oauth/v2/token",
                params={
                    "refresh_token": settings.ZOHO_REFRESH_TOKEN,
                    "client_id": settings.ZOHO_CLIENT_ID,
                    "client_secret": settings.ZOHO_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    async def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: str,
        priority: str = "medium",
        department: str = "Customer Support",
        call_id: str = "",
        ai_summary: str = "",
    ) -> str | None:
        """Create a Zoho Desk ticket. Returns ticket ID."""
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            import uuid
            mock_id = f"MOCK-ZOHO-TKT-{uuid.uuid4().hex[:6].upper()}"
            logger.warning("zoho_not_configured_using_mock", mock_id=mock_id)
            return mock_id

        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/tickets",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    json={
                        "subject": subject,
                        "description": f"{description}\n\nCall ID: {call_id}\n\nAI Summary: {ai_summary}",
                        "email": customer_email,
                        "priority": priority.capitalize(),
                        "departmentId": department,
                        "status": "Open",
                        "channel": "Phone",
                    },
                )
                resp.raise_for_status()
                return str(resp.json().get("id", ""))
        except Exception as e:
            logger.error("zoho_create_ticket_error", error=str(e))
            return None

    async def search_tickets(self, customer_email: str) -> list[dict]:
        """Search tickets by customer email."""
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            return []
        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    params={"email": customer_email, "limit": 5},
                )
                resp.raise_for_status()
                return resp.json().get("data", [])
        except Exception as e:
            logger.error("zoho_search_error", error=str(e))
            return []

    async def search_contact(self, search_value: str) -> dict | None:
        """
        Search contacts in Zoho Desk by Customer ID/Email/Order/Phone/etc.
        If Zoho Desk client is not configured, returns mock contact details.
        """
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            clean_val = search_value.upper().strip()
            if any(x in clean_val for x in ["CUST-10001", "ORD-12345", "AMB-12345", "INV-98765", "DEMO"]):
                return {
                    "id": "1000000001",
                    "firstName": "Rajesh",
                    "lastName": "Kumar",
                    "email": "rajesh.kumar@example.com",
                    "phone": "9876543210",
                    "crm_id": "CUST-10001",
                    "vip_status": True,
                }
            elif "CUST-" in clean_val or "ORD-" in clean_val or "AMB-" in clean_val or "INV-" in clean_val:
                import re
                digits = "".join(re.findall(r"\d+", clean_val)) or "9999"
                return {
                    "id": f"100000{digits}",
                    "firstName": f"Customer-{digits}",
                    "lastName": "User",
                    "email": f"customer.{digits}@example.com",
                    "phone": f"98765{digits[:5]:<05}",
                    "crm_id": f"CUST-{digits}",
                    "vip_status": False,
                }
            return None

        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/contacts/search",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    params={"searchVal": search_value, "limit": 1},
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                if data:
                    contact = data[0]
                    return {
                        "id": str(contact.get("id")),
                        "firstName": contact.get("firstName", ""),
                        "lastName": contact.get("lastName", ""),
                        "email": contact.get("email", ""),
                        "phone": contact.get("phone", ""),
                        "crm_id": contact.get("crmId", ""),
                        "vip_status": contact.get("isVip", False),
                    }
                return None
        except Exception as e:
            logger.error("zoho_search_contact_error", val=search_value, error=str(e))
            return None

    async def get_recent_tickets(self, contact_id: str) -> list:
        """Fetch recent tickets for a customer."""
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            return [
                {"ticketNumber": "1056", "subject": "Powerbank not charging", "status": "Closed", "createdTime": "2024-01-20T10:00:00Z"},
                {"ticketNumber": "1089", "subject": "Where is my order?", "status": "Open", "createdTime": "2024-02-15T14:30:00Z"}
            ]

        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    params={"contactId": contact_id, "limit": 3, "sortBy": "-createdTime"},
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                
                return [
                    {
                        "ticketNumber": t.get("ticketNumber"),
                        "subject": t.get("subject"),
                        "status": t.get("status"),
                        "createdTime": t.get("createdTime")
                    } for t in data
                ]
        except Exception as e:
            logger.error("zoho_get_tickets_error", contact_id=contact_id, error=str(e))
            return []

    async def update_ticket_contact(self, ticket_id: str, email: str, subject_update: str) -> bool:
        """Update an existing ticket's subject/email/contact info in Zoho Desk."""
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            logger.warning("zoho_not_configured_for_update", ticket_id=ticket_id)
            return True

        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{self.base_url}/tickets/{ticket_id}",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    json={
                        "email": email,
                        "subject": subject_update,
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("zoho_update_ticket_error", ticket_id=ticket_id, error=str(e))
            return False

    async def update_ticket_summary(self, ticket_id: str, description: str, status: str = "Open") -> bool:
        """Update Zoho Desk ticket description and status at call end."""
        if not settings.ZOHO_CLIENT_ID or "your_zoho" in settings.ZOHO_CLIENT_ID.lower():
            logger.warning("zoho_not_configured_for_summary_update", ticket_id=ticket_id)
            return True

        try:
            token = await self._get_token()
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{self.base_url}/tickets/{ticket_id}",
                    headers={
                        "Authorization": f"Zoho-oauthtoken {token}",
                        "orgId": self.org_id,
                    },
                    json={
                        "description": description,
                        "status": status.capitalize(),
                    },
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error("zoho_update_summary_error", ticket_id=ticket_id, error=str(e))
            return False
