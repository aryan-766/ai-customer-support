"""
RAG Retriever — searches Qdrant for relevant knowledge base chunks.
Uses BAAI/bge-small-en-v1.5 for embedding + cross-encoder reranker.
"""

import asyncio
from typing import Optional
import structlog

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)

from app.config import settings
from app.core.models_loader import ModelRegistry
from typing import TypedDict

class Citation(TypedDict):
    citation_id: str
    title: str
    source: str
    snippet: str
    relevance_score: float

logger = structlog.get_logger(__name__)

VECTOR_SIZE = 384   # BAAI/bge-small-en-v1.5 output dimensions


class RAGRetriever:
    """
    Knowledge base retriever using:
    - BAAI/bge-small-en-v1.5 for dense embedding
    - Qdrant for vector storage + search
    - Cross-encoder reranker for quality improvement
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance

    def get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=settings.QDRANT_URL, timeout=10)
        return self._client

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = settings.KB_TOP_K,
        rerank_top_n: int = settings.KB_RERANK_TOP_N,
    ) -> list[Citation]:
        """
        Main search method:
        1. Embed query with BGE
        2. Vector search in Qdrant
        3. Rerank with cross-encoder
        4. Return top-N as Citation objects
        """
        models = ModelRegistry()
        loop = asyncio.get_event_loop()

        # Step 1: Embed query (thread pool — blocking)
        query_vector = await loop.run_in_executor(None, models.embed, query)

        # Step 2: Build optional category filter
        search_filter = None
        if category:
            search_filter = Filter(
                must=[FieldCondition(key="category", match=MatchValue(value=category))]
            )

        # Step 3: Vector search
        client = self.get_client()
        results = await loop.run_in_executor(
            None,
            lambda: client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
                query_filter=search_filter,
            ),
        )

        if not results:
            return []

        # Step 4: Rerank
        candidates = [r.payload.get("chunk_text", "") for r in results]
        scores = await loop.run_in_executor(None, models.rerank, query, candidates)

        # Sort by reranker scores
        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
        top = ranked[:rerank_top_n]

        citations: list[Citation] = [
            Citation(
                citation_id=r.payload.get("citation_id", str(r.id)),
                title=r.payload.get("title", "Knowledge Base"),
                source=r.payload.get("source_file", ""),
                snippet=r.payload.get("chunk_text", "")[:300],
                relevance_score=float(score),
            )
            for r, score in top
        ]

        logger.info("rag_search_done", query=query[:50], results=len(citations))
        return citations

    def build_context_prompt(self, citations: list[Citation]) -> str:
        """Format citations into a prompt context block."""
        if not citations:
            return ""
        parts = ["Use the following knowledge base information to answer:"]
        for i, c in enumerate(citations, 1):
            parts.append(f"\n[{c['citation_id']}] {c['title']}\n{c['snippet']}")
        return "\n".join(parts)


async def setup_qdrant_collection():
    """Create collection if it doesn't exist (runs at startup)."""
    loop = asyncio.get_event_loop()
    client = QdrantClient(url=settings.QDRANT_URL, timeout=10)

    existing = await loop.run_in_executor(None, client.get_collections)
    names = [c.name for c in existing.collections]

    if settings.QDRANT_COLLECTION not in names:
        await loop.run_in_executor(
            None,
            lambda: client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            ),
        )
        logger.info("qdrant_collection_created", name=settings.QDRANT_COLLECTION)
    else:
        logger.info("qdrant_collection_exists", name=settings.QDRANT_COLLECTION)


# Singleton
rag = RAGRetriever()
