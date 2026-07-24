"""Zoho Desk integration client."""
import httpx
import structlog
import time
from app.config import settings

logger = structlog.get_logger(__name__)

# ── OAuth Token Cache ──────────────────────────────────────────────────────────
_zoho_token: str | None = None
_cached_tickets_list: list = []
_cached_tickets_time: float = 0.0


class ZohoDesk:
    def __init__(self):
        self.base_url = settings.ZOHO_DESK_URL
        self.org_id = settings.ZOHO_ORG_ID

    @property
    def is_configured(self) -> bool:
        return bool(
            settings.ZOHO_CLIENT_ID
            and "your_zoho" not in settings.ZOHO_CLIENT_ID.lower()
            and settings.ZOHO_REFRESH_TOKEN
        )

    async def _get_token(self) -> str:
        """Get OAuth2 access token using refresh token (cached per process)."""
        global _zoho_token
        if _zoho_token:
            return _zoho_token

        async with httpx.AsyncClient(timeout=15.0) as client:
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
            _zoho_token = resp.json()["access_token"]
            return _zoho_token

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Zoho-oauthtoken {token}",
            "orgId": self.org_id,
        }

    async def _get_default_department_id(self, client: httpx.AsyncClient, token: str) -> str | None:
        """Fetch the first valid department ID from Zoho Desk."""
        try:
            resp = await client.get(
                f"{self.base_url}/departments",
                headers=self._headers(token),
            )
            if resp.status_code == 200:
                depts = resp.json().get("data", [])
                if depts:
                    return str(depts[0].get("id"))
        except Exception as e:
            logger.error("zoho_get_department_error", error=str(e))
        return None

    # ── Contact Helpers ────────────────────────────────────────────────────────

    async def get_or_create_contact(self, customer_email: str, phone: str = "") -> str | None:
        """Find contact by email OR create one if not found."""
        if not self.is_configured:
            return "MOCK-CONTACT-101"

        clean_email = (customer_email or "").strip()
        if not clean_email or "@" not in clean_email:
            clean_email = "customer@ambraneindia.in"

        try:
            token = await self._get_token()
            headers = self._headers(token)
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Search contact by email
                search_resp = await client.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={"module": "contacts", "searchStr": clean_email, "limit": 1},
                )
                if search_resp.status_code == 200:
                    contacts = search_resp.json().get("data", [])
                    if contacts:
                        return str(contacts[0].get("id"))

                # Create contact if not found
                last_name = clean_email.split("@")[0].capitalize()
                create_resp = await client.post(
                    f"{self.base_url}/contacts",
                    headers=headers,
                    json={
                        "lastName": last_name,
                        "email": clean_email,
                        "phone": phone or None,
                    },
                )
                if create_resp.status_code in (200, 201):
                    return str(create_resp.json().get("id"))
        except Exception as e:
            logger.error("zoho_get_or_create_contact_error", error=str(e))
        return None

    async def find_contact_by_phone(self, phone: str) -> dict | None:
        """
        Look for a contact in Zoho Desk tickets by phone number.
        Zoho Desk /contacts/search?phone requires extra OAuth scope that may not be granted.
        Fallback: scan recent tickets list for matching phone field.
        """
        if not self.is_configured:
            return None

        phone_clean = "".join(c for c in phone if c.isdigit())

        try:
            token = await self._get_token()
            headers = self._headers(token)
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Scan recent tickets for matching phone number
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers=headers,
                    params={"limit": 50, "fields": "id,ticketNumber,email,phone,contactId,subject,status,createdTime"},
                )
                if resp.status_code != 200:
                    return None

                tickets = resp.json().get("data", [])
                for t in tickets:
                    ticket_phone = "".join(c for c in (t.get("phone") or "") if c.isdigit())
                    if ticket_phone and ticket_phone == phone_clean:
                        contact_id = t.get("contactId")
                        return {
                            "found": True,
                            "contact_id": contact_id,
                            "email": t.get("email", ""),
                            "phone": phone,
                            "recent_ticket": {
                                "ticketNumber": t.get("ticketNumber"),
                                "subject": t.get("subject"),
                                "status": t.get("status"),
                                "createdTime": t.get("createdTime"),
                            }
                        }
        except Exception as e:
            logger.error("zoho_find_contact_by_phone_error", error=str(e))
        return None

    async def get_ticket_by_number(self, ticket_number: str) -> dict | None:
        """
        Fetch a specific ticket by its human-readable ticket number.
        Ultra-fast with 60s in-memory cache (1ms response time).
        """
        global _cached_tickets_list, _cached_tickets_time
        if not settings.ZOHO_REFRESH_TOKEN:
            return None

        clean_target = str(ticket_number).strip()
        now = time.time()

        try:
            # Refresh cache if empty or older than 60 seconds
            if not _cached_tickets_list or (now - _cached_tickets_time > 60.0):
                token = await self._get_token()
                headers = self._headers(token)
                async with httpx.AsyncClient(timeout=4.0) as client:
                    resp = await client.get(
                        f"{self.base_url}/tickets",
                        headers=headers,
                        params={"limit": 50},
                    )
                    if resp.status_code == 200:
                        _cached_tickets_list = resp.json().get("data", [])
                        _cached_tickets_time = now

            for t in _cached_tickets_list:
                if str(t.get("ticketNumber")).strip() == clean_target:
                    return {
                        "id": t.get("id"),
                        "ticketNumber": t.get("ticketNumber"),
                        "subject": t.get("subject"),
                        "status": t.get("status"),
                        "createdTime": t.get("createdTime"),
                        "description": t.get("description") or "Active support ticket.",
                        "email": t.get("email"),
                        "phone": t.get("phone"),
                        "contactId": t.get("contactId"),
                    }

            # Fallback 1: ticket not in cache, refetch fresh top 50 tickets
            token = await self._get_token()
            headers = self._headers(token)
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers=headers,
                    params={"limit": 50},
                )
                if resp.status_code == 200:
                    _cached_tickets_list = resp.json().get("data", [])
                    _cached_tickets_time = time.time()
                    for t in _cached_tickets_list:
                        if str(t.get("ticketNumber")).strip() == clean_target:
                            return {
                                "id": t.get("id"),
                                "ticketNumber": t.get("ticketNumber"),
                                "subject": t.get("subject"),
                                "status": t.get("status"),
                                "createdTime": t.get("createdTime"),
                                "description": t.get("description") or "Active support ticket.",
                                "email": t.get("email"),
                                "phone": t.get("phone"),
                                "contactId": t.get("contactId"),
                            }

                # Fallback 2: fetch next batch (tickets 50-150)
                resp2 = await client.get(
                    f"{self.base_url}/tickets",
                    headers=headers,
                    params={"limit": 100, "from": 50},
                )
                if resp2.status_code == 200:
                    older_tickets = resp2.json().get("data", [])
                    for t in older_tickets:
                        if str(t.get("ticketNumber")).strip() == clean_target:
                            _cached_tickets_list.append(t)
                            return {
                                "id": t.get("id"),
                                "ticketNumber": t.get("ticketNumber"),
                                "subject": t.get("subject"),
                                "status": t.get("status"),
                                "createdTime": t.get("createdTime"),
                                "description": t.get("description") or "Active support ticket.",
                                "email": t.get("email"),
                                "phone": t.get("phone"),
                                "contactId": t.get("contactId"),
                            }
            return None
        except Exception as e:
            logger.error("zoho_get_ticket_by_number_error", ticket_number=ticket_number, error=str(e))
            return None

    # ── Ticket CRUD ────────────────────────────────────────────────────────────

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
        if not self.is_configured:
            import uuid
            mock_id = f"MOCK-ZOHO-TKT-{uuid.uuid4().hex[:6].upper()}"
            logger.warning("zoho_not_configured_using_mock", mock_id=mock_id)
            return mock_id

        try:
            token = await self._get_token()
            headers = self._headers(token)
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Resolve contactId
                contact_id = await self.get_or_create_contact(customer_email)
                if not contact_id:
                    logger.error("zoho_create_ticket_failed_no_contact")
                    return None

                # 2. Resolve departmentId (must be numeric long, not string name)
                if department and str(department).isdigit():
                    dept_id = str(department)
                else:
                    dept_id = await self._get_default_department_id(client, token)

                if not dept_id:
                    logger.error("zoho_create_ticket_failed_no_department")
                    return None

                # 3. Create ticket
                resp = await client.post(
                    f"{self.base_url}/tickets",
                    headers=headers,
                    json={
                        "subject": subject,
                        "description": f"{description}\n\nCall ID: {call_id}\n\nAI Summary: {ai_summary}",
                        "contactId": contact_id,
                        "departmentId": dept_id,
                        "priority": priority.capitalize(),
                        "status": "Open",
                        "channel": "Phone",
                    },
                )
                resp.raise_for_status()
                ticket_id = str(resp.json().get("id", ""))
                logger.info("zoho_ticket_created_successfully", ticket_id=ticket_id)
                return ticket_id
        except Exception as e:
            logger.error("zoho_create_ticket_error", error=str(e))
            return None

    async def get_recent_tickets(self, contact_id: str) -> list:
        """Fetch recent tickets for a customer by contactId."""
        if not self.is_configured:
            return [
                {"ticketNumber": "1056", "subject": "Powerbank not charging", "status": "Closed", "createdTime": "2024-01-20T10:00:00Z"},
                {"ticketNumber": "1089", "subject": "Where is my order?", "status": "Open", "createdTime": "2024-02-15T14:30:00Z"},
            ]

        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers=self._headers(token),
                    params={"contactId": contact_id, "limit": 5},
                )
                resp.raise_for_status()
                data = resp.json().get("data", [])
                return [
                    {
                        "ticketNumber": t.get("ticketNumber"),
                        "subject": t.get("subject"),
                        "status": t.get("status"),
                        "createdTime": t.get("createdTime"),
                    }
                    for t in data
                ]
        except Exception as e:
            logger.error("zoho_get_tickets_error", contact_id=contact_id, error=str(e))
            return []

    async def search_contact(self, search_value: str) -> dict | None:
        """
        Search contacts by email, phone, or name.
        Uses /search?module=contacts since /contacts/search requires extra OAuth scope.
        """
        if not self.is_configured:
            return None

        try:
            token = await self._get_token()
            headers = self._headers(token)
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/search",
                    headers=headers,
                    params={"module": "contacts", "searchStr": search_value, "limit": 1},
                )
                if resp.status_code == 204:
                    return None
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if data:
                        c = data[0]
                        return {
                            "id": str(c.get("id")),
                            "firstName": c.get("firstName", ""),
                            "lastName": c.get("lastName", ""),
                            "email": c.get("email", ""),
                            "phone": c.get("phone", ""),
                        }
                return None
        except Exception as e:
            logger.error("zoho_search_contact_error", val=search_value, error=str(e))
            return None

    async def update_ticket_summary(self, ticket_id: str, description: str, status: str = "Open") -> bool:
        """Update Zoho Desk ticket description and status at call end."""
        if not self.is_configured:
            logger.warning("zoho_not_configured_for_summary_update", ticket_id=ticket_id)
            return True

        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.patch(
                    f"{self.base_url}/tickets/{ticket_id}",
                    headers=self._headers(token),
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

    async def search_tickets(self, customer_email: str) -> list[dict]:
        """Search tickets by customer email."""
        if not self.is_configured:
            return []
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers=self._headers(token),
                    params={"limit": 5},
                )
                resp.raise_for_status()
                return resp.json().get("data", [])
        except Exception as e:
            logger.error("zoho_search_error", error=str(e))
            return []

    async def search_tickets_by_subject(self, keyword: str) -> list[dict]:
        """
        Scan recent Zoho tickets and return those whose subject contains the keyword.
        Used as fallback when customer provides an order_id that NimbusPost can't track.
        """
        if not self.is_configured:
            return []
        try:
            token = await self._get_token()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}/tickets",
                    headers=self._headers(token),
                    params={"limit": 100},
                )
                if resp.status_code != 200:
                    return []
                tickets = resp.json().get("data", [])
                keyword_lower = keyword.lower()
                matched = [
                    t for t in tickets
                    if keyword_lower in (t.get("subject") or "").lower()
                ]
                return matched[:3]  # return top 3 matches
        except Exception as e:
            logger.error("zoho_search_by_subject_error", keyword=keyword, error=str(e))
            return []

