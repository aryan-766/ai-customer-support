"""Stub API routers — to be implemented."""
from fastapi import APIRouter
router = APIRouter(prefix="/agents")

@router.get("/status")
async def agents_status():
    return {"status": "operational", "agents": [
        "receptionist", "authentication", "intent", "background_intel",
        "product_support", "warranty", "registration", "invoice",
        "order_status", "return_replacement", "complaint",
        "human_escalation", "agent_assist", "call_summary"
    ]}
