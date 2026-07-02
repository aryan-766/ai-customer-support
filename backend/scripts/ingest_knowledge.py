"""
Knowledge base ingestion script.
Reads documents from /knowledge directory → chunks → embeds → stores in Qdrant.
Run once: python scripts/ingest_knowledge.py
"""

import asyncio
import sys
import os
from pathlib import Path
import uuid
import structlog

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.core.models_loader import ModelRegistry
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

logger = structlog.get_logger(__name__)

KNOWLEDGE_DIR = Path("/app/knowledge")
if not KNOWLEDGE_DIR.exists():
    KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"
VECTOR_SIZE = 384   # bge-small-en-v1.5

# Category mapping: folder name → Qdrant category tag
FOLDER_CATEGORIES = {
    "faqs": "faq",
    "manuals": "manual",
    "policies": "policy",
    "sops": "sop",
}


async def main():
    print("🚀 Starting knowledge base ingestion...")
    print(f"📁 Knowledge dir: {KNOWLEDGE_DIR}")

    # Initialize models
    registry = ModelRegistry()
    await registry.initialize()

    # Connect to Qdrant
    client = QdrantClient(url=settings.QDRANT_URL, timeout=30)

    # Ensure collection exists
    existing = client.get_collections()
    if settings.QDRANT_COLLECTION not in [c.name for c in existing.collections]:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"✅ Created Qdrant collection: {settings.QDRANT_COLLECTION}")

    total_chunks = 0

    # Walk all knowledge subdirectories
    for folder, category in FOLDER_CATEGORIES.items():
        folder_path = KNOWLEDGE_DIR / folder
        if not folder_path.exists():
            print(f"⚠️  Folder not found: {folder_path}")
            continue

        print(f"\n📂 Processing {folder}/ (category: {category})")

        for file_path in folder_path.rglob("*"):
            if file_path.suffix.lower() not in {".md", ".txt", ".pdf", ".docx"}:
                continue

            print(f"   📄 {file_path.name}")
            text = extract_text(file_path)

            if not text.strip():
                print(f"   ⚠️  Empty file, skipping")
                continue

            chunks = split_text(text, chunk_size=500, overlap=50)
            print(f"   → {len(chunks)} chunks")

            # Embed and store in batches
            points = []
            for i, chunk in enumerate(chunks):
                vector = registry.embed(chunk)
                citation_id = f"{file_path.stem}-{i}"

                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "chunk_text": chunk,
                        "chunk_index": i,
                        "source_file": file_path.name,
                        "title": file_path.stem.replace("_", " ").title(),
                        "category": category,
                        "citation_id": citation_id,
                        "language": "en",
                    }
                ))

            # Upload batch
            if points:
                client.upsert(
                    collection_name=settings.QDRANT_COLLECTION,
                    points=points,
                )
                total_chunks += len(points)

    print(f"\n✅ Ingestion complete! Total chunks stored: {total_chunks}")
    print(f"   Collection: {settings.QDRANT_COLLECTION}")
    print(f"   Qdrant: {settings.QDRANT_URL}")


def extract_text(file_path: Path) -> str:
    """Extract raw text from supported file types."""
    suffix = file_path.suffix.lower()

    if suffix in {".md", ".txt"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            print(f"   ⚠️  PDF error: {e}")
            return ""

    elif suffix == ".docx":
        try:
            from docx import Document
            doc = Document(str(file_path))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            print(f"   ⚠️  DOCX error: {e}")
            return ""

    return ""


def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping word chunks."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    asyncio.run(main())
