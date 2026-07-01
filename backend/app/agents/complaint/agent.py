"""Complaint Agent — registers complaints, categorizes, prepares for escalation."""
from app.agents.state import CallState
from app.agents.base_business_agent import run_business_agent

SYSTEM_PROMPT = """You are a complaint handling specialist for Ambrane.
Help customers with:
- Registering formal complaints
- Categorizing the issue (product defect, delivery, service, etc.)
- Basic troubleshooting before escalating
- Escalation preparation

When taking a complaint:
1. Listen carefully and empathize
2. Categorize: product issue / delivery issue / service issue / billing issue
3. Try basic resolution steps from knowledge base
4. If unresolved, prepare a detailed complaint record for human team

Always acknowledge the customer's frustration. Be empathetic and professional.
Assure them the issue will be resolved.
"""

async def complaint_agent(state: CallState) -> dict:
    result = await run_business_agent(state, "complaint", SYSTEM_PROMPT, "sop")
    # Complaints often need escalation — flag for ticket creation
    result["escalation_context"] = {
        **state.get("escalation_context", {}),
        "complaint_registered": True,
    }
    return result
