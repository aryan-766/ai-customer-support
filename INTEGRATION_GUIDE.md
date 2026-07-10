# Integration Guide: Shopify, Zoho Desk & San Software SIP

This document provides detailed steps on how the three platforms connect and communicate with the Ambrane AI Customer Support application.

## 1. San Software (SIP via Asterisk Bridge)

San Software handles the phone network (telephony). However, it does not connect to WebSockets directly. Instead, it connects via SIP to an **Asterisk Server**, which acts as a bridge between the SIP call and our AI WebSocket.

### How it connects:
1. **Incoming Call:** A customer calls your Ambrane support number. San Software routes this SIP call to your Asterisk server.
2. **Asterisk Webhook:** Asterisk receives the call and makes an HTTP POST request to your backend to get routing instructions:
   - **Endpoint:** `http://<your-server-domain>/api/v1/sip/san-software/incoming`
   - **Payload:** Contains the caller's phone number (`caller_id`).
3. **Backend Response:** The backend creates a new Call Session and returns a JSON response containing the WebSocket URL (e.g., `ws://<your-server-domain>/ws/call/{call_id}`).
4. **Audio Bridging:** Asterisk reads this response and uses an application (like `AudioSocket` or `ExternalMedia` via ARI) to bridge the SIP audio stream to the provided WebSocket URL.
5. **AI Interaction:** Customer speech is streamed from Asterisk to the backend WebSocket, transcribed, processed by the AI agents, and the AI's audio response is streamed back through Asterisk to the customer.

**Next Steps for Setup:**
- Configure your Asterisk Dialplan or ARI script to hit the `/api/v1/sip/san-software/incoming` webhook upon receiving a call from the San Software SIP trunk.
- Ensure your Asterisk server is compiled with `res_audiosocket` or has ARI enabled for external media streaming.

---

## 2. Shopify API (Order & Warranty CRM)

Shopify acts as the central source of truth for all customer orders, tracking, and warranty checks.

### How it connects:
1. **Order Tracking Inquiry:** When a customer asks "Where is my order?", the AI extracts the Order ID (e.g., `AMB-12345`).
2. **API Request:** The `order_status` agent uses the `ShopifyClient` to securely call the Shopify Admin API (`/admin/api/2024-01/orders.json?name=AMB-12345`).
3. **Data Retrieval:** It reads the `financial_status`, `fulfillment_status`, and the `fulfillments` array to get the live tracking number and courier company (e.g., Delhivery, Bluedart).
4. **AI Context:** This data is injected directly into the AI's memory. The AI naturally tells the customer: *"Your order was shipped via Delhivery and will arrive soon."*

**Next Steps for Setup:**
- Go to your Shopify Admin Dashboard -> Settings -> Apps and sales channels -> Develop apps.
- Create a Custom App and give it `read_orders` and `read_customers` permissions.
- Copy the **Admin API Access Token** and the **Shop URL** and paste them into your `.env` file:
  ```env
  SHOPIFY_SHOP_URL="your-store.myshopify.com"
  SHOPIFY_ACCESS_TOKEN="shpat_xxxxx"
  ```

---

## 3. Zoho Desk (Ticketing & Reverse Pickups)

Zoho Desk is used to log tickets that require human intervention, such as scheduling a reverse pickup for defective items.

### How it connects:
1. **Return Request:** If a customer's product is defective and within warranty, the AI approves a return.
2. **Ticket Creation:** The `return_replacement` agent uses the `ZohoDesk` client to call the Zoho Desk API (`/api/v1/tickets`).
3. **Logistics Handoff:** It creates a high-priority ticket assigned to the **Logistics Department** with the subject `Reverse Pickup Request - Order <ID>`.
4. **Resolution:** Your human logistics team sees this ticket in Zoho Desk, schedules the actual pickup with the courier, and closes the ticket.

**Next Steps for Setup:**
- Go to the Zoho API Console and register a new client.
- Generate an OAuth Refresh Token with permissions for `Desk.tickets.CREATE`.
- Fill in these variables in your `.env` file:
  ```env
  ZOHO_CLIENT_ID="your_client_id"
  ZOHO_CLIENT_SECRET="your_client_secret"
  ZOHO_REFRESH_TOKEN="your_refresh_token"
  ZOHO_ORG_ID="your_org_id"
  ```
