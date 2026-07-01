# 📞 Ambrane AI Customer Support Call Flow Diagram & Guide

This document describes the step-by-step lifecycle of an inbound voice call, mapping the routing logic, database checks, and third-party integrations (Zoho Desk CRM, NimbusPost Aggregator).

---

## 🗺️ Visual Flowchart

```mermaid
graph TD
    %% Define styles
    classDef startEnd fill:#f9f,stroke:#333,stroke-width:2px;
    classDef db fill:#9cf,stroke:#333,stroke-width:1px;
    classDef agent fill:#f96,stroke:#333,stroke-width:1px;
    classDef zoho fill:#9f9,stroke:#333,stroke-width:1px;
    
    A([1. Call WebSocket Connected]) --> B[2. Pre-Call Zoho Setup]
    B -->|Create Temporary Ticket| Z1[(Zoho Desk CRM)]
    B --> C[3. AI Receptionist Node]
    C -->|Greeting & Language Check| D[4. Authentication Node]
    
    D -->|Request Customer / Order / Invoice ID| D_Check{ID Parsed?}
    D_Check -->|No ID / Invalid| D
    D_Check -->|Valid ID| Z2[(Zoho Desk CRM)]
    Z2 -->|Search Contact| D_Auth[Update Zoho Ticket with Contact info]
    
    D_Auth --> E[5. Context Loader Node]
    E -->|Fetch Previous Tickets & Call Summaries| DB1[(PostgreSQL DB)]
    
    E --> F[6. Intent Detection Node]
    F -->|Analyze Input text| F_Check{Confidence >= 0.5?}
    
    F_Check -->|No: Trigger 1| H_Esc[10. Human Escalation Node]
    F_Check -->|Yes: Check Intent| G{Intent?}
    
    G -->|Complaint: Trigger 3| H_Esc
    G -->|Support Query| B_Agent[7. Business Support Agent Node]
    
    B_Agent -->|RAG manual policy| Q1[(Qdrant Vector DB)]
    B_Agent -->|Order Status/Return| N1[NimbusPost Aggregator API]
    
    B_Agent --> R_Check[8. Resolution Check Node]
    R_Check -->|Loop >= 3 or LLM outputs [ESCALATE]: Trigger 2| H_Esc
    R_Check -->|LLM outputs [RESOLVED]| PC[11. Post Call Automations]
    R_Check -->|Needs more help| B_Agent
    
    H_Esc -->|Push Transcript + History| R1[(Redis Cache / PubSub)]
    R1 -->|Live Assistance Feed| Live[Human Dashboard]
    Live -->|Live Support Session ended| PC
    
    PC -->|Sync final summary & Transcript| Z3[(Zoho Desk CRM)]
    Z3 -->|Update Ticket Status: Closed if resolved else Open| DB2[(PostgreSQL DB)]
    DB2 -->|Save permanent Call summary & CRM Log| End([Call Terminated])

    class A,End startEnd;
    class DB1,DB2,Q1,R1 db;
    class C,D,E,F,B_Agent,R_Check,H_Esc,PC agent;
    class Z1,Z2,Z3 zoho;
```

---

## 📜 Detailed Step-by-Step Breakdown

### 1. WebSocket Call Initiation
* **Trigger**: Telephony/SAN software connects to `/ws/call/{call_id}`.
* **Database Action**: Temporary session initialized in **Redis** to store short-term streaming transcript data.

### 2. Pre-Call Zoho Ticket Integration
* **Action**: Before the receptionist greets the customer, a background API call is made to Zoho Desk.
* **Result**: Creates a ticket (e.g. `Inbound Call: {call_id}` with status `Open`). The `zoho_ticket_id` is saved into the call state.

### 3. AI Receptionist Node
* **Action**: Customer is greeted in Hindi/English.
* **Language Detection**: Identifies language choice (Hindi or English) dynamically.

### 4. Authentication (Single-ID Input)
* **Action**: Prompts the caller for **exactly one** of the following identifiers:
  * **Customer ID** (e.g., `CUST-10001`)
  * **Order ID** (e.g., `AMB-12345` / `ORD-99887`)
  * **Invoice ID** (e.g., `INV-33445`)
* **CRM Action**: Searches Zoho Desk Contacts API. If found, updates the pre-created Zoho ticket with the customer's real name and email.

### 5. Context Loader Node
* **Action**: Queries PostgreSQL to load historical context:
  * **Previous Tickets**: Active and past ticket statuses.
  * **Previous Call Summaries**: Short descriptions of past issues.
* **LLM Injection**: This caller history is formatted and injected into the AI agent prompt so it does not repeat previous troubleshooting steps.

### 6. Intent Detection Node
* **Action**: Classifier checks the customer's request.
* **Trigger 1 (Unclear Intent)**: If confidence score is $< 0.5$, the system automatically changes intent to `talk_to_human`, sets `escalate = True`, and bypasses the AI business agents directly to human transfer.

### 7. AI Business Agent Node (Product, Warranty, Invoice, Order, Return)
* **Knowledge Retrieval (RAG)**: Queries **Qdrant Vector DB** for policy manual checks.
* **External Integration**: Calls **NimbusPost Aggregator API** to fetch order track info if checking order status or replacement queries.

### 8. Resolution & Loop Check
* **Tag Checks**: AI outputs `[RESOLVED]` if satisfaction words are captured, or `[ESCALATE]` if it cannot solve the query.
* **Trigger 2 (Business Agent Failure)**: If loop count between customer and agent $\ge 3$ or agent responds with `[ESCALATE]`, it transfers directly to human escalation.

### 9. Immediate Escalation Trigger
* **Trigger 3 (Complaints/Zoho Ticket requests)**: If intent classifier detects a `"complaint"`, the call routes straight to human escalation.

### 10. Human Escalation Handoff
* **Action**: System plays the handoff message: *"Main aapko abhi hamare human agent se connect kar rahi hoon..."*.
* **Dashboard Sync**: Packages the active live transcript, sentiment priority, previous ticket history, and past call summaries. Sends it via **Redis Pub/Sub** to the Next.js Agent Assist Dashboard.

### 11. Post-Call Automations
* **Final Summary Generation**: AI generates the final summary (Customer issue, resolution steps, and outcome).
* **Zoho Desk Update**: Updates the pre-created Zoho ticket with the full transcript and AI summary. Sets status to:
  * **`Closed`**: If the issue was resolved by AI.
  * **`Open`**: If the issue was escalated/unresolved.
* **PostgreSQL Log**: Records the final summaries permanently in database tables for future context loader lookups.
