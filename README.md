# 📞 Ambrane AI Customer Support Workflow

An intelligent, production-ready AI Customer Support System featuring an automated inbound voice call lifecycle, routing logic, database checks, and external integrations (Zoho Desk CRM, NimbusPost Aggregator).

The project is structured as a monorepo containing a **FastAPI backend** and a **Next.js frontend**.

---

## 🏗️ Architecture & Call Flow

The lifecycle of an inbound voice call includes:
1. **WebSocket Call Initiation**: Connects to the server and creates session cache.
2. **Pre-Call Zoho Ticket Integration**: Automatic creation of a temporary ticket in Zoho Desk.
3. **AI Receptionist**: Language detection (Hindi/English) and greeting.
4. **Authentication (Single-ID Input)**: Prompting the caller for Customer ID, Order ID, or Invoice ID and searching Zoho CRM Contacts.
5. **Context Loader**: Loading historical call logs and tickets from PostgreSQL.
6. **Intent Detection**: Deciding if the customer's intent is clear or requires human escalation.
7. **Business Agent (RAG)**: Querying Qdrant Vector DB for manuals and policy checks, and retrieving order details from NimbusPost API.
8. **Resolution & Loop Check**: Checking if the customer issue is resolved or needs escalation.
9. **Post-Call Automations**: Synchronizing transcripts and updating ticket status in Zoho and PostgreSQL.

> [!NOTE]
> For a detailed walkthrough of the call flow and architecture, please see:
> * [CALL_FLOW.md](CALL_FLOW.md) - Explains the step-by-step logic and routing nodes.
> * [ambrane_ai_voice_platform_architecture.md](ambrane_ai_voice_platform_architecture.md) - Provides deep dive information on the components.

---

## 📂 Project Structure

```
AI Customer Support Workflow/
├── backend/                  # FastAPI Application
│   ├── app/                  # Main backend codebase (APIs, services, routes)
│   ├── tests/                # Automated backend tests
│   ├── Dockerfile            # Backend Docker instructions
│   └── requirements.txt      # Python dependencies
├── frontend/                 # Next.js Application
│   ├── src/                  # React components and pages
│   ├── public/               # Static assets
│   ├── package.json          # Node dependencies
│   └── next.config.ts        # Next.js configuration
├── docker-compose.yml        # Docker compose file for PostgreSQL, Redis, Qdrant
├── .env.example              # Template environment variables file
└── Makefile                  # Command shortcuts
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Docker & Docker Compose
- Node.js (v18+)
- Python (v3.10+)

### 2. Environment Variables
Clone/copy the `.env.example` file to `.env` in the root directory:
```bash
cp .env.example .env
```
Fill in the credentials for Zoho Desk, NimbusPost, Qdrant, PostgreSQL, and Redis.

### 3. Running Services with Docker Compose
Start PostgreSQL, Redis, and Qdrant in the background:
```bash
docker-compose up -d
```

### 4. Running Backend (FastAPI)
Navigate to the `backend/` directory:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Running Frontend (Next.js)
Navigate to the `frontend/` directory:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the client-side interface.
