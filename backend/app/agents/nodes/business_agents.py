"""
Business Agents for LangGraph.
Each agent handles a specific domain and has access to specific FastMCP tools.
"""

from langchain_core.messages import AIMessage, HumanMessage
import structlog
from app.agents.state import CallState
from app.core.llm.factory import LLMFactory
from app.tools import crm_mcp, rag_mcp, utility_mcp

logger = structlog.get_logger(__name__)

async def _generic_agent(state: CallState, role_prompt: str, tools_list: list) -> dict:
    """Helper to run a generic agent with specific prompt and tools."""
    llm = LLMFactory.get_provider()
    
    # In a real implementation, we would bind tools to the LLM here.
    # Ollama integration needs to support tool calling, or we manually parse.
    # For this demo, we'll construct a prompt that asks the LLM to respond.
    
    transcript = state.get("transcript", [])
    recent_text = "\n".join([f"{t['speaker']}: {t['text']}" for t in transcript[-5:]])
    
    system_prompt = f"{role_prompt}\n\nRecent conversation:\n{recent_text}\n\nRespond conversationally as an AI voice assistant. Keep it concise."
    
    try:
        response = await llm.generate(
            prompt="Respond to the user.",
            system=system_prompt
        )
        
        return {
            "messages": [AIMessage(content=response.text)],
            "active_agent": "completed"
        }
    except Exception as e:
        logger.error("agent_execution_failed", error=str(e))
        return {
            "messages": [AIMessage(content="I'm having trouble connecting right now. Please hold.")],
            "escalate": True
        }


async def faq_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane FAQ Agent. Answer general questions using the knowledge base."
    return await _generic_agent(state, prompt, [])

async def order_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Order Support Agent. Help the user check their order status."
    return await _generic_agent(state, prompt, [])

async def complaint_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Complaint Resolution Agent. Be empathetic and register their complaint."
    return await _generic_agent(state, prompt, [])

async def tech_support_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Technical Support Agent. Help troubleshoot device issues."
    return await _generic_agent(state, prompt, [])

async def registration_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Registration Agent. Help the user register their product or account."
    return await _generic_agent(state, prompt, [])

async def sales_agent(state: CallState) -> dict:
    prompt = "You are an Ambrane Sales Agent. Help the user choose a product to buy."
    return await _generic_agent(state, prompt, [])
