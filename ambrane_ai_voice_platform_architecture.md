# Ambrane AI Voice Customer Support Platform
### Senior AI Architect Design — Production-Quality, Laptop-Friendly

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Complete Architecture Diagram](#2-complete-architecture-diagram)
3. [Data Flow](#3-data-flow)
4. [LangGraph State Graph](#4-langgraph-state-graph)
5. [MCP Server Structure](#5-mcp-server-structure)
6. [API Design](#6-api-design)
7. [Database Schema](#7-database-schema)
8. [Docker Setup](#8-docker-setup)
9. [Deployment Guide](#9-deployment-guide)
10. [Step-by-Step Implementation Plan](#10-step-by-step-implementation-plan)
11. [Recommended Coding Standards](#11-recommended-coding-standards)
12. [Future Scalability Strategy](#12-future-scalability-strategy)

---

## 1. Folder Structure

```
ambrane-voice-support/
│
├── .env                          # Environment variables
├── .env.example
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile                      # Developer shortcuts
├── README.md
│
├── backend/                      # FastAPI backend (Python)
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── alembic/                  # DB migrations
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Settings via pydantic-settings
│   │   ├── dependencies.py       # FastAPI dependency injection
│   │   │
│   │   ├── api/                  # Route layer
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── calls.py      # Call management endpoints
│   │   │   │   ├── agents.py     # Agent interaction endpoints
│   │   │   │   ├── analytics.py  # Dashboard endpoints
│   │   │   │   ├── tickets.py    # Zoho Desk integration endpoints
│   │   │   │   ├── knowledge.py  # KB management endpoints
│   │   │   │   └── websocket.py  # WS for real-time transcript/assist
│   │   │
│   │   ├── core/                 # Core infrastructure abstractions
│   │   │   ├── __init__.py
│   │   │   ├── stt/
│   │   │   │   ├── base.py       # Abstract STT provider
│   │   │   │   ├── faster_whisper.py
│   │   │   │   └── factory.py    # Provider factory (swap freely)
│   │   │   ├── llm/
│   │   │   │   ├── base.py       # Abstract LLM provider
│   │   │   │   ├── ollama.py     # Qwen2.5 via Ollama
│   │   │   │   ├── llamacpp.py   # Qwen2.5 via llama.cpp
│   │   │   │   └── factory.py
│   │   │   ├── tts/
│   │   │   │   ├── base.py       # Abstract TTS provider
│   │   │   │   ├── kokoro.py
│   │   │   │   └── factory.py
│   │   │   ├── rag/
│   │   │   │   ├── embedder.py   # BAAI/bge-small-en-v1.5
│   │   │   │   ├── retriever.py  # Qdrant retrieval + reranker
│   │   │   │   └── ingester.py   # Document ingestion pipeline
│   │   │   └── audio/
│   │   │       ├── processor.py  # Audio chunking & VAD
│   │   │       └── streamer.py   # WebSocket audio streaming
│   │   │
│   │   ├── agents/               # LangGraph multi-agent system
│   │   │   ├── __init__.py
│   │   │   ├── state.py          # Shared CallState TypedDict
│   │   │   ├── graph.py          # Master LangGraph supervisor
│   │   │   ├── receptionist/
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   ├── authentication/
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   ├── intent/
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   ├── product_support/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── warranty/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── registration/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── invoice/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── order_status/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── return_replacement/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── complaint/
│   │   │   │   ├── agent.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── tools.py
│   │   │   ├── human_escalation/
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   ├── agent_assist/
│   │   │   │   ├── agent.py
│   │   │   │   └── prompts.py
│   │   │   └── call_summary/
│   │   │       ├── agent.py
│   │   │       └── prompts.py
│   │   │
│   │   ├── mcp/                  # FastMCP server (tool calling)
│   │   │   ├── server.py         # MCP server definition
│   │   │   ├── tools/
│   │   │   │   ├── zoho_desk.py
│   │   │   │   ├── lymbus.py
│   │   │   │   ├── warranty_db.py
│   │   │   │   ├── courier.py
│   │   │   │   ├── knowledge_base.py
│   │   │   │   └── crm.py
│   │   │   └── resources/
│   │   │       ├── policies.py
│   │   │       └── faqs.py
│   │   │
│   │   ├── integrations/         # External service clients
│   │   │   ├── zoho_desk.py
│   │   │   ├── lymbus.py
│   │   │   ├── courier.py        # DHL, Delhivery, etc.
│   │   │   └── my_product_care.py
│   │   │
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── call.py
│   │   │   ├── customer.py
│   │   │   ├── ticket.py
│   │   │   ├── agent_session.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── schemas/              # Pydantic schemas (request/response)
│   │   │   ├── call.py
│   │   │   ├── customer.py
│   │   │   ├── agent.py
│   │   │   └── analytics.py
│   │   │
│   │   ├── services/             # Business logic services
│   │   │   ├── call_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── notification_service.py
│   │   │   └── post_call_service.py
│   │   │
│   │   └── utils/
│   │       ├── logger.py
│   │       ├── metrics.py        # Prometheus metrics
│   │       └── security.py
│   │
├── frontend/                     # Next.js 14+ App Router
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx          # Dashboard home
│       │   ├── calls/
│       │   │   └── [id]/page.tsx # Live call view
│       │   ├── analytics/
│       │   │   └── page.tsx
│       │   └── knowledge/
│       │       └── page.tsx
│       ├── components/
│       │   ├── ui/               # shadcn/ui components
│       │   ├── call/
│       │   │   ├── LiveTranscript.tsx
│       │   │   ├── AgentAssistPanel.tsx
│       │   │   ├── CustomerContext.tsx
│       │   │   └── CallControls.tsx
│       │   ├── analytics/
│       │   │   ├── KPICards.tsx
│       │   │   └── Charts.tsx
│       │   └── layout/
│       │       ├── Sidebar.tsx
│       │       └── Header.tsx
│       ├── hooks/
│       │   ├── useWebSocket.ts
│       │   ├── useCall.ts
│       │   └── useAgentAssist.ts
│       ├── lib/
│       │   ├── api.ts            # Typed API client
│       │   └── ws.ts             # WebSocket manager
│       └── types/
│           └── index.ts
│
├── knowledge/                    # Raw knowledge base files
│   ├── faqs/
│   ├── manuals/
│   ├── policies/
│   └── sops/
│
├── scripts/                      # One-time setup & utility scripts
│   ├── setup.sh
│   ├── ingest_knowledge.py       # Ingest KB into Qdrant
│   ├── download_models.sh        # Pull Ollama model + Kokoro weights
│   └── seed_db.py
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 2. Complete Architecture Diagram

```mermaid
graph TB
    subgraph TELEPHONY["☎️ Telephony Layer"]
        CALL["Customer Call"]
        SEN["SEN Calling Software"]
        CALL -->|SIP/WebRTC| SEN
    end

    subgraph GATEWAY["🎙️ AI Voice Gateway"]
        AUDIO_IN["Audio Stream In"]
        STT["Faster-Whisper STT\n(streaming)"]
        TTS["Kokoro TTS\n(streaming)"]
        AUDIO_OUT["Audio Stream Out"]
        SEN -->|Raw Audio| AUDIO_IN
        AUDIO_IN --> STT
        TTS --> AUDIO_OUT
        AUDIO_OUT -->|Synthesized Voice| SEN
    end

    subgraph AGENTS["🤖 LangGraph Multi-Agent System (FastAPI)"]
        GRAPH["Master Supervisor\nLangGraph Graph"]
        STT -->|Text Chunks| GRAPH

        subgraph CORE_AGENTS["Core Flow Agents"]
            REC["Receptionist\nAgent"]
            AUTH["Authentication\nAgent"]
            INTENT["Intent Detection\nAgent"]
            BG["Background Intelligence\n(Sentiment · Confidence · Priority)"]
        end

        subgraph BUSINESS_AGENTS["Business Agents"]
            PS["Product Support"]
            WA["Warranty"]
            REG["Registration"]
            INV["Invoice"]
            OS["Order Status"]
            RR["Return & Replacement"]
            COMP["Complaint"]
        end

        subgraph SPECIAL_AGENTS["Special Agents"]
            HE["Human Escalation\nAgent"]
            AA["Agent Assist\n(Live AI)"]
            CS["Call Summary\nAgent"]
        end

        GRAPH --> REC --> AUTH --> INTENT --> BG
        BG -->|Route| BUSINESS_AGENTS
        BG -->|Escalate| HE
        BUSINESS_AGENTS --> CS
        HE --> AA
    end

    subgraph MCP["🔧 FastMCP Tool Server"]
        MCP_ZOHO["zoho_desk tools"]
        MCP_LYM["lymbus tools"]
        MCP_WAR["warranty_db tools"]
        MCP_COR["courier tools"]
        MCP_KB["knowledge_base tools"]
        MCP_CRM["crm tools"]
    end

    subgraph RAG["📚 RAG Engine"]
        EMBED["BGE Embedder\nbge-small-en-v1.5"]
        QDRANT["Qdrant\nVector DB"]
        RERANK["Cross-Encoder\nReranker"]
        EMBED --> QDRANT --> RERANK
    end

    subgraph INFRA["🗄️ Infrastructure"]
        PG["PostgreSQL\n(Persistent Data)"]
        REDIS["Redis\n(Sessions · Cache · Pub/Sub)"]
        LLM["Ollama / llama.cpp\nQwen2.5 3B GGUF"]
    end

    subgraph INTEGRATIONS["🔌 Enterprise Integrations"]
        ZOHO["Zoho Desk"]
        LYMBUS["Lymbus OMS"]
        COURIER["Courier APIs"]
        MPC["My Product Care"]
    end

    subgraph FRONTEND["💻 Next.js Frontend"]
        DASH["Analytics Dashboard"]
        LIVE["Live Call View\n+ Agent Assist Panel"]
        KB_UI["Knowledge Base UI"]
    end

    AGENTS -->|Tool Calls| MCP
    AGENTS -->|Semantic Search| RAG
    AGENTS -->|Read/Write| INFRA
    MCP -->|API Calls| INTEGRATIONS
    GRAPH -->|LLM Inference| LLM
    AGENTS -->|WebSocket Events| FRONTEND
    FRONTEND -->|REST + WS| AGENTS
```

---

## 3. Data Flow

### 3.1 Inbound Call Flow (Happy Path — AI Resolves)

```
1.  Customer dials → SEN routes audio stream to FastAPI WebSocket /ws/call
2.  AudioProcessor: VAD (Voice Activity Detection) silences background noise
3.  Faster-Whisper: Streaming STT → text chunks → Redis Pub/Sub channel
4.  LangGraph Graph starts new CallState with call_id, session_id
5.  Receptionist Agent: Greets customer, detects language (Hindi/English)
6.  Authentication Agent: Collects mobile/order_id/serial_no → MCP tool verify_customer()
7.  Context Loader: Queries PostgreSQL for customer profile, previous tickets, orders
8.  Intent Detection Agent: Classifies intent from transcript (multi-label)
9.  Background Intelligence: Runs sentiment analysis, AI confidence scoring, priority detection
10. Decision Engine (LangGraph conditional_edges):
    - IF escalate conditions met → Human Escalation Agent
    - ELSE → Route to appropriate Business Agent
11. Business Agent: Retrieves relevant KB chunks from Qdrant via RAG
12. Business Agent: Calls MCP tools (e.g., get_order_status(), validate_warranty())
13. LLM (Qwen2.5): Generates grounded response with citations
14. Streaming response → Kokoro TTS → Audio stream → Customer
15. Post-resolution: Call Summary Agent generates structured summary
16. Post-Call Service: Updates PostgreSQL, Zoho Desk, CRM, triggers notifications
```

### 3.2 Human Escalation Flow

```
1.  Decision Engine flags escalation
2.  Human Escalation Agent packages full CallContext:
    - Authentication status
    - Full transcript (from Redis)
    - Detected intent + sentiment + priority
    - Previous tickets, warranty status, order info
    - Pre-fetched API results
    - AI suggested resolution
3.  Context pushed to agent desktop via WebSocket /ws/agent/{agent_id}
4.  Call transferred (SIP transfer via SEN)
5.  Agent Assist activates:
    - Real-time transcript fed to Agent Assist Agent
    - Next-best-response suggestions streamed to agent UI
    - KB articles surfaced in real time
    - Zoho Desk ticket auto-filled
    - Compliance monitoring running in background
6.  After call: Agent Assist auto-generates wrap-up notes, follow-up tasks
```

### 3.3 RAG Retrieval Flow

```
User Query Text
      │
      ▼
BGE Embedder (bge-small-en-v1.5) → 384-dim vector
      │
      ▼
Qdrant Hybrid Search (vector + BM25 keyword)
      │
      ▼
Top-K candidates (k=10)
      │
      ▼
Cross-Encoder Reranker → Top-3 chunks with scores
      │
      ▼
Prompt augmentation with citation metadata
      │
      ▼
LLM Response: "According to [FAQ-23] your warranty covers..."
```

### 3.4 Post-Call Automation Flow

```
Call Ends
    │
    ├── Call Summary Agent (LLM) → structured JSON summary
    ├── Full transcript from Redis → PostgreSQL (calls.transcript)
    ├── Zoho Desk ticket created/updated via MCP
    ├── CRM record updated (customer interaction history)
    ├── CSAT survey triggered via SMS/WhatsApp
    ├── Invoice PDF sent if requested (MCP → invoice tool)
    ├── Tracking link sent if order query (MCP → courier tool)
    └── Analytics events published to Redis → Analytics Service → PostgreSQL
```

---

## 4. LangGraph State Graph

### 4.1 Shared CallState

```python
# backend/app/agents/state.py

from typing import TypedDict, Annotated, Literal, Optional, List, Dict, Any
from langgraph.graph.message import add_messages

class CustomerContext(TypedDict):
    customer_id: Optional[str]
    mobile: Optional[str]
    name: Optional[str]
    email: Optional[str]
    is_authenticated: bool
    vip_status: bool
    previous_tickets: List[Dict]
    orders: List[Dict]
    warranty_info: List[Dict]
    crm_profile: Dict[str, Any]

class BackgroundIntelligence(TypedDict):
    sentiment: Literal["positive", "neutral", "negative", "angry"]
    sentiment_score: float          # -1.0 to 1.0
    ai_confidence: float            # 0.0 to 1.0
    priority: Literal["low", "medium", "high", "critical"]
    escalation_reason: Optional[str]
    fraud_risk: float               # 0.0 to 1.0

class CallState(TypedDict):
    # Core call metadata
    call_id: str
    session_id: str
    started_at: str
    language: Literal["en", "hi", "auto"]
    channel: str                    # "phone", "whatsapp", "web"

    # Conversation history (LangGraph managed)
    messages: Annotated[list, add_messages]
    transcript: List[Dict]          # [{speaker, text, timestamp}]

    # Authentication
    customer_context: CustomerContext

    # Routing
    intent: Optional[str]
    intent_confidence: float
    active_agent: Optional[str]
    routing_history: List[str]

    # Background intelligence
    intelligence: BackgroundIntelligence

    # Escalation
    escalate: bool
    escalation_context: Dict[str, Any]

    # Resolution
    issue_resolved: bool
    resolution_summary: Optional[str]
    zoho_ticket_id: Optional[str]

    # RAG citations
    citations: List[Dict]

    # Agent assist (only when human agent active)
    human_agent_id: Optional[str]
    assist_suggestions: List[Dict]

    # Post-call
    call_summary: Optional[Dict]
    follow_up_actions: List[Dict]
```

### 4.2 Master LangGraph Graph

```python
# backend/app/agents/graph.py

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from .state import CallState

def build_graph() -> StateGraph:
    graph = StateGraph(CallState)

    # ── Add nodes ──────────────────────────────────────────────────────────
    graph.add_node("receptionist",      receptionist_agent)
    graph.add_node("authentication",    authentication_agent)
    graph.add_node("context_loader",    context_loader_agent)
    graph.add_node("intent_detection",  intent_detection_agent)
    graph.add_node("background_intel",  background_intelligence_agent)
    graph.add_node("decision_engine",   decision_engine_node)       # pure router
    graph.add_node("product_support",   product_support_agent)
    graph.add_node("warranty",          warranty_agent)
    graph.add_node("registration",      registration_agent)
    graph.add_node("invoice",           invoice_agent)
    graph.add_node("order_status",      order_status_agent)
    graph.add_node("return_replacement",return_replacement_agent)
    graph.add_node("complaint",         complaint_agent)
    graph.add_node("human_escalation",  human_escalation_agent)
    graph.add_node("agent_assist",      agent_assist_agent)         # parallel
    graph.add_node("call_summary",      call_summary_agent)
    graph.add_node("post_call",         post_call_service_node)

    # ── Entry ──────────────────────────────────────────────────────────────
    graph.set_entry_point("receptionist")

    # ── Core flow edges ────────────────────────────────────────────────────
    graph.add_edge("receptionist",     "authentication")
    graph.add_edge("authentication",   "context_loader")
    graph.add_edge("context_loader",   "intent_detection")
    graph.add_edge("intent_detection", "background_intel")
    graph.add_edge("background_intel", "decision_engine")

    # ── Decision engine conditional routing ────────────────────────────────
    graph.add_conditional_edges(
        "decision_engine",
        route_decision,
        {
            "product_support":    "product_support",
            "warranty":           "warranty",
            "registration":       "registration",
            "invoice":            "invoice",
            "order_status":       "order_status",
            "return_replacement": "return_replacement",
            "complaint":          "complaint",
            "human_escalation":   "human_escalation",
        }
    )

    # ── Business agents → resolution check ────────────────────────────────
    BUSINESS_AGENTS = [
        "product_support", "warranty", "registration",
        "invoice", "order_status", "return_replacement", "complaint"
    ]
    for agent in BUSINESS_AGENTS:
        graph.add_conditional_edges(
            agent,
            check_resolution,
            {
                "resolved":          "call_summary",
                "needs_more_help":   "intent_detection",   # re-route
                "escalate":          "human_escalation",
            }
        )

    # ── Human escalation → agent assist (parallel) ─────────────────────────
    graph.add_edge("human_escalation", "agent_assist")
    graph.add_edge("agent_assist",     "call_summary")

    # ── Post-call ──────────────────────────────────────────────────────────
    graph.add_edge("call_summary", "post_call")
    graph.add_edge("post_call",    END)

    return graph.compile()


def route_decision(state: CallState) -> str:
    """Pure routing function — no LLM call."""
    if state["escalate"]:
        return "human_escalation"
    intent_map = {
        "product_support":    "product_support",
        "warranty":           "warranty",
        "registration":       "registration",
        "invoice":            "invoice",
        "order_status":       "order_status",
        "return":             "return_replacement",
        "replacement":        "return_replacement",
        "complaint":          "complaint",
        "talk_to_human":      "human_escalation",
    }
    return intent_map.get(state["intent"], "complaint")


def check_resolution(state: CallState) -> str:
    if state.get("escalate"):
        return "escalate"
    if state.get("issue_resolved"):
        return "resolved"
    return "needs_more_help"
```

---

## 5. MCP Server Structure

### 5.1 FastMCP Server Definition

```python
# backend/app/mcp/server.py

from fastmcp import FastMCP
from .tools import zoho_desk, lymbus, warranty_db, courier, knowledge_base, crm

mcp = FastMCP(
    name="ambrane-support-tools",
    version="1.0.0",
    description="Tool server for Ambrane AI Customer Support agents"
)

# ── Register all tool modules ──────────────────────────────────────────────
mcp.include(zoho_desk.router)
mcp.include(lymbus.router)
mcp.include(warranty_db.router)
mcp.include(courier.router)
mcp.include(knowledge_base.router)
mcp.include(crm.router)

if __name__ == "__main__":
    mcp.run(transport="stdio")   # or "streamable-http" for remote
```

### 5.2 Tool Definitions (Example — Zoho Desk)

```python
# backend/app/mcp/tools/zoho_desk.py

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional

router = FastMCP("zoho-desk")

class CreateTicketInput(BaseModel):
    customer_id: str
    subject: str
    description: str
    priority: str           # "low" | "medium" | "high" | "urgent"
    department: str
    call_id: str
    transcript_url: Optional[str] = None
    ai_summary: Optional[str] = None

@router.tool(description="Create a new support ticket in Zoho Desk")
async def create_ticket(input: CreateTicketInput) -> dict:
    """Creates ticket and returns ticket_id and ticket_url."""
    ...

@router.tool(description="Search for existing tickets by customer mobile or email")
async def search_tickets(customer_mobile: str, limit: int = 5) -> list[dict]:
    ...

@router.tool(description="Update ticket status and add resolution note")
async def update_ticket(
    ticket_id: str,
    status: str,
    resolution: Optional[str] = None,
    internal_note: Optional[str] = None
) -> dict:
    ...

@router.tool(description="Auto-fill Zoho Desk ticket fields from call context")
async def autofill_ticket(call_id: str) -> dict:
    """Reads CallState from Redis and fills ticket template."""
    ...
```

### 5.3 All MCP Tool Catalog

| Tool Module | Tools |
|---|---|
| **zoho_desk** | create_ticket, search_tickets, update_ticket, autofill_ticket, add_attachment |
| **lymbus** | get_order_by_id, get_orders_by_customer, get_shipment_status, initiate_return, request_replacement |
| **warranty_db** | validate_warranty, get_warranty_status, register_warranty, check_claim_eligibility, register_claim |
| **courier** | get_tracking_info, get_eta, get_rto_status, schedule_reverse_pickup |
| **knowledge_base** | search_kb, get_article, list_faqs, get_product_manual, get_policy |
| **crm** | get_customer_profile, update_customer, log_interaction, get_interaction_history |

### 5.4 MCP Resources

```python
# backend/app/mcp/resources/policies.py
# Exposes company policies as MCP resources (read-only)

@router.resource("policy://return_policy")
async def get_return_policy() -> str:
    return load_policy("return_policy.md")

@router.resource("policy://warranty_policy")
async def get_warranty_policy() -> str:
    ...
```

---

## 6. API Design

### 6.1 REST API (FastAPI — OpenAPI auto-generated)

```
Base URL: http://localhost:8000/api/v1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CALLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /calls/start              Start a new call session
GET    /calls/{call_id}          Get call details
GET    /calls/{call_id}/transcript  Full transcript
GET    /calls/{call_id}/summary  AI generated summary
POST   /calls/{call_id}/end      End call and trigger post-call
GET    /calls                    List calls (paginated, filterable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENTS (internal use by frontend)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /agents/status            Health of all agents
POST   /agents/escalate/{call_id}  Manually trigger escalation
GET    /agents/{call_id}/context   Full escalation context for human agent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KNOWLEDGE BASE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /knowledge/ingest         Upload & ingest documents
GET    /knowledge/search?q=...   Semantic search
GET    /knowledge/articles/{id}  Get article
DELETE /knowledge/articles/{id}  Remove article

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TICKETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /tickets                  Create Zoho Desk ticket
GET    /tickets/{id}             Get ticket details
PATCH  /tickets/{id}             Update ticket

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /analytics/kpis           Dashboard KPIs (date range)
GET    /analytics/calls          Call volume trends
GET    /analytics/sentiment      Sentiment trends
GET    /analytics/agents         Per-agent performance
GET    /analytics/intents        Intent distribution
GET    /analytics/escalations    Escalation reasons
GET    /analytics/kb-gaps        Knowledge base gap report
```

### 6.2 WebSocket API

```
WS /ws/call/{call_id}           ← Audio stream in (binary frames)
                                 → JSON events out

Event Types (server → client):
  { type: "transcript_chunk",   text: "...", speaker: "customer", ts: ... }
  { type: "agent_response",     text: "...", agent: "warranty" }
  { type: "tts_audio",          audio: <base64>, format: "pcm16" }
  { type: "intent_detected",    intent: "warranty", confidence: 0.92 }
  { type: "escalating",         reason: "angry_customer" }
  { type: "call_ended",         summary: {...} }

WS /ws/agent/{agent_id}         ← Human agent dashboard
                                 → Agent assist events

Event Types (server → client):
  { type: "customer_context",   data: {...} }
  { type: "assist_suggestion",  text: "...", confidence: 0.87 }
  { type: "kb_article",         title: "...", url: "...", snippet: "..." }
  { type: "compliance_alert",   message: "..." }
  { type: "transcript_live",    text: "...", speaker: "..." }
  { type: "ticket_autofill",    fields: {...} }
```

---

## 7. Database Schema

### 7.1 PostgreSQL Schema (SQLAlchemy Models)

```sql
-- customers
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mobile          VARCHAR(15) UNIQUE NOT NULL,
    email           VARCHAR(255),
    name            VARCHAR(255),
    is_vip          BOOLEAN DEFAULT FALSE,
    crm_id          VARCHAR(100),          -- Zoho CRM ID
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- calls
CREATE TABLE calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id     UUID REFERENCES customers(id),
    channel         VARCHAR(20) DEFAULT 'phone',  -- phone|whatsapp|web
    language        VARCHAR(5) DEFAULT 'en',
    status          VARCHAR(20) DEFAULT 'active', -- active|completed|escalated|abandoned
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    duration_sec    INT,

    -- Authentication
    auth_method     VARCHAR(50),
    is_authenticated BOOLEAN DEFAULT FALSE,

    -- Intent & routing
    detected_intent VARCHAR(100),
    intent_confidence FLOAT,
    routing_path    JSONB DEFAULT '[]',    -- ["receptionist","warranty","call_summary"]

    -- Intelligence
    sentiment       VARCHAR(20),
    sentiment_score FLOAT,
    ai_confidence   FLOAT,
    priority        VARCHAR(20),
    fraud_score     FLOAT,

    -- Resolution
    resolved        BOOLEAN DEFAULT FALSE,
    resolution_type VARCHAR(50),           -- ai_resolved|human_resolved|abandoned
    zoho_ticket_id  VARCHAR(100),
    human_agent_id  UUID,

    -- Content
    transcript      JSONB DEFAULT '[]',
    ai_summary      TEXT,
    citations       JSONB DEFAULT '[]',
    follow_up_tasks JSONB DEFAULT '[]',

    -- Recording
    recording_url   TEXT,
    transcript_url  TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- agent_sessions (human agent)
CREATE TABLE agent_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(100) NOT NULL,
    agent_name      VARCHAR(255),
    call_id         UUID REFERENCES calls(id),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    assist_suggestions_count INT DEFAULT 0,
    kb_articles_served INT DEFAULT 0
);

-- tickets (mirror of Zoho Desk)
CREATE TABLE tickets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zoho_ticket_id  VARCHAR(100) UNIQUE,
    call_id         UUID REFERENCES calls(id),
    customer_id     UUID REFERENCES customers(id),
    subject         VARCHAR(500),
    status          VARCHAR(50),
    priority        VARCHAR(20),
    department      VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- knowledge_base (metadata of ingested docs)
CREATE TABLE kb_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500) NOT NULL,
    category        VARCHAR(100),          -- faq|manual|policy|sop
    source_file     VARCHAR(500),
    qdrant_ids      JSONB DEFAULT '[]',   -- chunk IDs in Qdrant
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    version         INT DEFAULT 1
);

-- analytics_events (time-series, can migrate to TimescaleDB later)
CREATE TABLE analytics_events (
    id              BIGSERIAL PRIMARY KEY,
    call_id         UUID,
    event_type      VARCHAR(100),
    event_data      JSONB,
    occurred_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_analytics_events_occurred_at ON analytics_events (occurred_at DESC);
CREATE INDEX idx_analytics_events_type ON analytics_events (event_type);

-- csat_surveys
CREATE TABLE csat_surveys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id         UUID REFERENCES calls(id),
    customer_id     UUID REFERENCES customers(id),
    score           INT CHECK (score BETWEEN 1 AND 5),
    feedback        TEXT,
    sent_at         TIMESTAMPTZ DEFAULT NOW(),
    responded_at    TIMESTAMPTZ
);
```

### 7.2 Redis Key Schema

```
call:{call_id}:state          ← Full CallState JSON (TTL: 24h)
call:{call_id}:transcript     ← Redis List of transcript entries
call:{call_id}:audio_buffer   ← Redis Stream (audio chunks)
agent:{agent_id}:session      ← Human agent session data
session:{session_id}          ← Auth session (TTL: 30min)

Pub/Sub Channels:
  transcript.{call_id}        ← Transcript chunks for WebSocket
  assist.{agent_id}           ← Agent assist events
  call.events                 ← Global call event bus
```

### 7.3 Qdrant Collection Schema

```python
# Collection: "ambrane_kb"
# Vector size: 384 (bge-small-en-v1.5)
# Distance: Cosine

payload_schema = {
    "doc_id":       str,    # kb_documents.id
    "chunk_id":     str,    # unique chunk identifier
    "category":     str,    # "faq" | "manual" | "policy" | "sop"
    "title":        str,    # document title
    "source_file":  str,    # original filename
    "page":         int,    # page number
    "chunk_text":   str,    # raw chunk text (for citation display)
    "language":     str,    # "en" | "hi"
}
```

---

## 8. Docker Setup

### 8.1 docker-compose.yml (Production-style, laptop-optimized)

```yaml
# docker-compose.yml
version: "3.9"

services:

  # ── Infrastructure ────────────────────────────────────────────────────────

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ambrane_support
      POSTGRES_USER: ambrane
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ambrane"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
    deploy:
      resources:
        limits:
          memory: 300M

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
    deploy:
      resources:
        limits:
          memory: 512M

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    environment:
      OLLAMA_NUM_PARALLEL: 1
      OLLAMA_MAX_LOADED_MODELS: 1
    deploy:
      resources:
        limits:
          memory: 4G          # Qwen2.5 3B GGUF Q4 ≈ 2.2GB RAM
    profiles: ["cpu"]         # use "gpu" profile for GPU variant

  # ── Application ───────────────────────────────────────────────────────────

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://ambrane:${POSTGRES_PASSWORD}@postgres/ambrane_support
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
      - OLLAMA_URL=http://ollama:11434
      - STT_PROVIDER=faster_whisper
      - LLM_PROVIDER=ollama
      - TTS_PROVIDER=kokoro
      - MCP_TRANSPORT=stdio
    volumes:
      - ./knowledge:/app/knowledge:ro
      - ./backend:/app:rw
      - model_cache:/root/.cache/huggingface
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_started
    deploy:
      resources:
        limits:
          memory: 2G

  mcp_server:
    build:
      context: ./backend
      dockerfile: Dockerfile.mcp
    command: python -m app.mcp.server
    environment:
      - DATABASE_URL=postgresql+asyncpg://ambrane:${POSTGRES_PASSWORD}@postgres/ambrane_support
      - ZOHO_CLIENT_ID=${ZOHO_CLIENT_ID}
      - ZOHO_CLIENT_SECRET=${ZOHO_CLIENT_SECRET}
      - LYMBUS_API_KEY=${LYMBUS_API_KEY}
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 512M

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  ollama_data:
  model_cache:
```

### 8.2 Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--reload", "--ws-ping-interval", "20", "--ws-ping-timeout", "30"]
```

### 8.3 Estimated RAM Budget (Laptop)

```
Service           RAM Budget
─────────────────────────────
Ollama (Qwen2.5)  2.2 GB   ← Q4_K_M GGUF quantization
PostgreSQL        512 MB
Redis             300 MB
Qdrant            512 MB
Backend (FastAPI) 512 MB
MCP Server        256 MB
Frontend (Next.js)512 MB
Faster-Whisper    ~800 MB  ← tiny.en model for laptop
Kokoro TTS        ~400 MB
─────────────────────────────
TOTAL             ≈ 6.0 GB  ← fits on 8GB RAM laptop
                            ← comfortable on 16GB
```

---

## 9. Deployment Guide

### 9.1 Prerequisites

```bash
# Required on host machine:
- Python 3.11+
- Node.js 20+
- Docker Desktop (or Docker Engine + Compose v2)
- Git
- ffmpeg (for audio processing)
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
```

### 9.2 First-Time Setup

```bash
# 1. Clone repository
git clone <your-repo>
cd ambrane-voice-support

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (Zoho, Lymbus, etc.)

# 3. Download AI models
bash scripts/download_models.sh
# This script does:
#   - ollama pull qwen2.5:3b-instruct-q4_K_M
#   - python -c "from faster_whisper import WhisperModel; WhisperModel('tiny')"
#   - Downloads Kokoro model weights

# 4. Start infrastructure
docker compose up postgres redis qdrant -d

# 5. Run database migrations
docker compose run --rm backend alembic upgrade head

# 6. Seed demo data (optional)
docker compose run --rm backend python scripts/seed_db.py

# 7. Ingest knowledge base
docker compose run --rm backend python scripts/ingest_knowledge.py

# 8. Start all services
docker compose up -d

# 9. Verify
curl http://localhost:8000/health
open http://localhost:3000
```

### 9.3 Development Mode (Without Docker)

```bash
# Terminal 1: Infrastructure only
docker compose up postgres redis qdrant ollama -d

# Terminal 2: Backend
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Terminal 3: MCP Server
cd backend
python -m app.mcp.server

# Terminal 4: Frontend
cd frontend
npm install
npm run dev
```

### 9.4 Makefile Shortcuts

```makefile
# Makefile
.PHONY: setup start stop logs test ingest

setup:
	cp .env.example .env
	docker compose up postgres redis qdrant -d
	docker compose run --rm backend alembic upgrade head
	bash scripts/download_models.sh
	python scripts/ingest_knowledge.py

start:
	docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f backend

test:
	docker compose run --rm backend pytest tests/ -v

ingest:
	docker compose run --rm backend python scripts/ingest_knowledge.py

migrate:
	docker compose run --rm backend alembic upgrade head
```

---

## 10. Step-by-Step Implementation Plan

> Estimated: 1 developer × 12 weeks (part-time / full-time adjustable)

### Phase 1: Foundation (Week 1–2)

```
[ ] 1.1  Set up Git repo with monorepo structure
[ ] 1.2  Write pyproject.toml + requirements.txt
[ ] 1.3  Bootstrap FastAPI app with config, logging, health check
[ ] 1.4  Write SQLAlchemy models + Alembic migration
[ ] 1.5  Set up PostgreSQL + Redis + Qdrant via Docker Compose
[ ] 1.6  Test database connection + Redis connection
[ ] 1.7  Define CallState TypedDict (state.py)
[ ] 1.8  Write abstract base classes for STT, LLM, TTS (provider interfaces)
```

### Phase 2: AI Voice Pipeline (Week 3–4)

```
[ ] 2.1  Implement Faster-Whisper STT (streaming mode)
[ ] 2.2  Integrate Ollama + Qwen2.5 3B via LangChain-Ollama
[ ] 2.3  Implement Kokoro TTS (streaming synthesis)
[ ] 2.4  Build AudioProcessor (VAD + chunking)
[ ] 2.5  WebSocket audio streaming endpoint (/ws/call)
[ ] 2.6  End-to-end audio pipeline test (speak → STT → LLM → TTS → hear)
[ ] 2.7  Implement provider factories (STT/LLM/TTS easily swappable)
```

### Phase 3: RAG Engine (Week 5)

```
[ ] 3.1  BGE embedder setup (bge-small-en-v1.5 via sentence-transformers)
[ ] 3.2  Qdrant collection creation + indexing logic
[ ] 3.3  Document ingestion pipeline (PDF + DOCX + MD → chunks)
[ ] 3.4  Hybrid search (dense + sparse/BM25)
[ ] 3.5  Cross-encoder reranker integration (ms-marco-MiniLM)
[ ] 3.6  RAG retriever with citation metadata
[ ] 3.7  Ingest all knowledge base documents (FAQs, manuals, policies, SOPs)
[ ] 3.8  Test retrieval accuracy
```

### Phase 4: Core Agents (Week 6–7)

```
[ ] 4.1  Build LangGraph supervisor graph (graph.py)
[ ] 4.2  Receptionist Agent (language detection + greeting)
[ ] 4.3  Authentication Agent (mobile + order ID verification)
[ ] 4.4  Context Loader (PostgreSQL customer data fetch)
[ ] 4.5  Intent Detection Agent (multi-label classification)
[ ] 4.6  Background Intelligence (sentiment + confidence + priority)
[ ] 4.7  Decision Engine (pure routing, no LLM)
[ ] 4.8  Test complete core flow with mock customer
```

### Phase 5: Business Agents (Week 8)

```
[ ] 5.1  Product Support Agent + RAG integration
[ ] 5.2  Warranty Agent + warranty_db MCP tools
[ ] 5.3  Registration Agent
[ ] 5.4  Invoice Agent
[ ] 5.5  Order Status Agent + Lymbus + Courier MCP tools
[ ] 5.6  Return & Replacement Agent
[ ] 5.7  Complaint Agent (ticket creation + categorization)
[ ] 5.8  Test all business agents end-to-end
```

### Phase 6: MCP Tool Server (Week 9)

```
[ ] 6.1  FastMCP server setup
[ ] 6.2  Zoho Desk tools (create, update, search tickets)
[ ] 6.3  Lymbus tools (orders, returns, replacements)
[ ] 6.4  Warranty DB tools (validate, register, claim)
[ ] 6.5  Courier API tools (tracking, pickup)
[ ] 6.6  Knowledge Base tools (search, retrieve)
[ ] 6.7  CRM tools (profile read/write)
[ ] 6.8  MCP Resources (policies, FAQs)
[ ] 6.9  Integration tests for all tools
```

### Phase 7: Human Escalation + Agent Assist (Week 10)

```
[ ] 7.1  Human Escalation Agent (context packaging)
[ ] 7.2  Agent Assist Agent (real-time suggestions)
[ ] 7.3  WebSocket /ws/agent endpoint for agent dashboard
[ ] 7.4  Compliance monitoring (keyword detection)
[ ] 7.5  Zoho Desk ticket auto-fill from CallState
[ ] 7.6  Live transcript streaming to agent UI
```

### Phase 8: Post-Call + Analytics (Week 10–11)

```
[ ] 8.1  Call Summary Agent (structured JSON output)
[ ] 8.2  Post-call service (CRM update, Zoho update, notifications)
[ ] 8.3  SMS / WhatsApp trigger (via Twilio or MSG91)
[ ] 8.4  CSAT survey trigger
[ ] 8.5  Analytics event publisher (Redis → PostgreSQL)
[ ] 8.6  Analytics API endpoints
[ ] 8.7  Dashboard KPI calculations
```

### Phase 9: Frontend (Week 11–12)

```
[ ] 9.1  Next.js 14 App Router setup + TypeScript + Tailwind
[ ] 9.2  Analytics Dashboard (KPI cards + charts via Recharts)
[ ] 9.3  Live Call View (transcript + agent assist panel)
[ ] 9.4  Customer Context Panel (auth status, history, orders)
[ ] 9.5  Call Controls (escalate, mute, end)
[ ] 9.6  Knowledge Base UI (search + upload)
[ ] 9.7  WebSocket hooks (useCall, useAgentAssist)
[ ] 9.8  Responsive layout + dark mode
```

### Phase 10: Testing + Hardening (Week 12)

```
[ ] 10.1  Unit tests for all agents (pytest + LangGraph test harness)
[ ] 10.2  Integration tests for MCP tools
[ ] 10.3  Load test WebSocket (locust)
[ ] 10.4  Prompt injection / security testing
[ ] 10.5  RAM profiling + optimization
[ ] 10.6  Latency benchmarking (STT + LLM + TTS pipeline)
[ ] 10.7  Error handling + graceful degradation
[ ] 10.8  Logging + Prometheus metrics
```

---

## 11. Recommended Coding Standards

### 11.1 Python Standards

```python
# ── Type hints everywhere ──────────────────────────────────────────────────
# Good: explicit, IDE-friendly
async def get_customer(customer_id: UUID) -> CustomerContext | None:
    ...

# ── Pydantic for all data contracts ───────────────────────────────────────
class AgentResponse(BaseModel):
    agent_name: str
    text: str
    citations: list[Citation] = []
    confidence: float = Field(ge=0.0, le=1.0)
    tool_calls: list[ToolCall] = []

# ── Async-first (no blocking I/O) ─────────────────────────────────────────
# All DB, Redis, HTTP calls must be async
# Use asyncpg driver, aioredis, httpx

# ── Provider abstraction pattern ──────────────────────────────────────────
class STTProvider(ABC):
    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptChunk]:
        ...

# ── Agent prompt management ───────────────────────────────────────────────
# Keep prompts in separate prompts.py, versioned
# Use f-strings or ChatPromptTemplate (not hardcoded in agent)

# ── Structured logging ────────────────────────────────────────────────────
import structlog
logger = structlog.get_logger(__name__)
logger.info("intent_detected", call_id=call_id, intent=intent, confidence=conf)
```

### 11.2 Project Conventions

```
Naming:
  - Files:     snake_case.py
  - Classes:   PascalCase
  - Functions: snake_case
  - Constants: UPPER_SNAKE_CASE
  - DB tables: snake_case (plural)

Agent Patterns:
  - Every agent returns updated CallState (immutable update)
  - Never call LLM from routing/decision functions
  - All external I/O via MCP tools (no direct HTTP in agents)
  - Prompts always include language instruction (Hindi/English)

Error Handling:
  - Use custom exception hierarchy (AmbraneSupportError)
  - Agents never crash the graph — return error state
  - All external calls wrapped with retry (tenacity)
  - Timeouts on all LLM calls (30s max)

Testing:
  - Agents tested with mock LLM + mock MCP tools
  - RAG tested with known retrieval fixtures
  - WebSocket tests via pytest-asyncio
```

### 11.3 Git Workflow

```
Branch strategy: GitHub Flow
  main          ← always deployable
  feature/xxx   ← feature branches
  fix/xxx       ← bug fixes

Commit format:
  feat(warranty-agent): add warranty claim eligibility check
  fix(stt): handle empty audio chunks in stream
  refactor(graph): extract routing into pure functions
  docs(api): update OpenAPI descriptions

PR checklist:
  [ ] Tests pass
  [ ] Type-checked (mypy --strict)
  [ ] Linted (ruff)
  [ ] Formatted (black)
  [ ] No secrets committed
```

---

## 12. Future Scalability Strategy

### 12.1 Provider Swap Strategy (Cloud Migration)

The provider abstraction layer means you can swap components **with zero business logic changes**:

| Component | Local (Now) | Cloud (Later) |
|---|---|---|
| **STT** | Faster-Whisper | Google Speech-to-Text, AWS Transcribe, Deepgram |
| **LLM** | Qwen2.5 3B via Ollama | GPT-4o, Gemini 1.5 Pro, Claude 3.5 |
| **TTS** | Kokoro | Google TTS, ElevenLabs, AWS Polly |
| **Embeddings** | BGE-small local | OpenAI text-embedding-3-small |
| **Vector DB** | Qdrant (local) | Qdrant Cloud, Pinecone, Weaviate |
| **Database** | PostgreSQL (Docker) | AWS RDS, Cloud SQL, Supabase |
| **Cache** | Redis (Docker) | AWS ElastiCache, Redis Cloud |

```python
# Swapping STT provider = 1-line config change
STT_PROVIDER=faster_whisper  →  STT_PROVIDER=google_stt
```

### 12.2 Horizontal Scaling Path

```
Phase 1: Laptop  
  └─ Docker Compose (single machine)

Phase 2: Small Server (8–32 cores)
  └─ Docker Compose on VPS/bare metal
  └─ Nginx reverse proxy
  └─ Add GPU for faster inference

Phase 3: Multi-Server
  └─ Docker Swarm or bare Kubernetes (k3s)
  └─ Separate STT/TTS/LLM services
  └─ Redis Cluster
  └─ PostgreSQL with read replicas

Phase 4: Cloud-Native
  └─ Kubernetes (EKS/GKE)
  └─ Replace Ollama → OpenAI/Gemini API
  └─ Replace Qdrant local → Qdrant Cloud
  └─ Add Kafka for event streaming
  └─ TimescaleDB for analytics time-series
  └─ Prometheus + Grafana monitoring
```

### 12.3 Adding New Agents

The modular LangGraph design makes adding agents trivial:

```python
# To add a "Loan EMI Agent" (hypothetical future product):
# 1. Create backend/app/agents/loan_emi/agent.py
# 2. Add to graph.py: graph.add_node("loan_emi", loan_emi_agent)
# 3. Add routing rule in route_decision()
# 4. Add MCP tools if needed
# Done — zero changes to existing agents
```

### 12.4 Multi-Language Expansion

```python
# Current: Hindi + English
# Future: Add Tamil, Telugu, Marathi, Bengali

# STT: Faster-Whisper supports 99 languages natively
# LLM: Qwen2.5 has multilingual capability
# TTS: Replace Kokoro → Azure Neural TTS (supports all Indian languages)
# Prompts: Parameterize language in prompt templates
```

### 12.5 Compliance & Security Hardening (Production)

```
PII Handling:
  - Mask mobile/OTP in logs
  - Encrypt transcripts at rest (PostgreSQL column encryption)
  - GDPR/DPDP right-to-erasure support

Security:
  - JWT authentication for agent dashboard
  - API key rotation for external integrations
  - Rate limiting per call session
  - Input sanitization (prompt injection defense)

Observability:
  - OpenTelemetry traces for all agent calls
  - Prometheus metrics: latency, error rate, token usage
  - Grafana dashboards
  - Alerting on: high escalation rate, LLM timeout, STT errors
```

---

## Quick Reference: Key Technology Choices

| Layer | Technology | Why |
|---|---|---|
| **STT** | Faster-Whisper (tiny/base) | Fast, low RAM, streaming support |
| **LLM** | Qwen2.5 3B Q4 via Ollama | Best quality/size ratio, tool calling, multilingual |
| **TTS** | Kokoro TTS | High-quality, fully offline, no API cost |
| **Embeddings** | bge-small-en-v1.5 | 384-dim, fast, strong retrieval quality |
| **Vector DB** | Qdrant | Hybrid search, filtering, low RAM |
| **Agent Framework** | LangGraph | State machines, streaming, multi-agent |
| **Tool Calling** | FastMCP | Standard protocol, easy tool registry |
| **API** | FastAPI | Async, WebSocket, auto OpenAPI |
| **DB** | PostgreSQL | JSONB for flexible fields, reliable |
| **Cache/PubSub** | Redis | Session state, real-time transcript streaming |
| **Frontend** | Next.js 14 App Router | Server components, WebSocket, TypeScript |

---

*Architecture Version: 1.0.0 | Designed for Ambrane Consumer Electronics | June 2026*
