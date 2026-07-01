"""Knowledge Base API — search and ingest."""
from fastapi import APIRouter, UploadFile, File, Form
from app.core.rag.retriever import rag

router = APIRouter(prefix="/knowledge")


@router.get("/search")
async def search_kb(q: str, category: str | None = None, top_k: int = 3):
    """Semantic search across the knowledge base."""
    citations = await rag.search(query=q, category=category, rerank_top_n=top_k)
    return {"query": q, "results": citations}


@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(default="general"),
):
    """Upload and ingest a single document into the knowledge base."""
    # TODO: implement single-file upload ingestion
    return {"message": "Ingestion queued", "filename": file.filename, "category": category}
