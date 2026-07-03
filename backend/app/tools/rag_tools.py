"""
FastMCP server for Knowledge Search tools (RAG).
"""

from fastmcp import FastMCP
from typing import List, Dict, Any
from app.config import settings

rag_mcp = FastMCP("Ambrane-KnowledgeBase")

@rag_mcp.tool()
async def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search the Ambrane Knowledge Base for policies, FAQs, manuals, etc.
    """
    # Note: A real implementation would call Qdrant here.
    # For now we'll stub this out to be integrated with Qdrant later.
    from qdrant_client import AsyncQdrantClient
    
    try:
        client = AsyncQdrantClient(url=settings.QDRANT_URL)
        # Assuming fastembed is set up on the collection
        results = await client.query(
            collection_name=settings.QDRANT_COLLECTION,
            query_text=query,
            limit=top_k
        )
        
        formatted_results = []
        for point in results:
            formatted_results.append({
                "score": point.score,
                "text": point.metadata.get("text", ""),
                "source": point.metadata.get("source", "unknown")
            })
        return formatted_results
    except Exception as e:
        return [{"error": f"Failed to search knowledge base: {str(e)}"}]
