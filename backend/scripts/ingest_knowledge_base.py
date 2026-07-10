"""
Knowledge Base Ingestion Script
================================
Reads all markdown files from the knowledge/ directory,
chunks them, embeds with BAAI/bge-small-en-v1.5, and stores in Qdrant.

Usage (from backend/ directory with venv activated):
    python scripts/ingest_knowledge_base.py

Categories are auto-detected from folder names:
    knowledge/faqs/     → category: "faq"
    knowledge/manuals/  → category: "manual"
    knowledge/policies/ → category: "policy"
    knowledge/sops/     → category: "sop"
"""

import os
import sys
import uuid
import hashlib

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)

from app.config import settings

# ── Configuration ──────────────────────────────────────────────────────────────
KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "knowledge")
VECTOR_SIZE = 384       # BAAI/bge-small-en-v1.5 output dimensions
CHUNK_SIZE = 500        # characters per chunk
CHUNK_OVERLAP = 50      # overlap between chunks

# Map folder names → RAG categories
CATEGORY_MAP = {
    "faqs": "faq",
    "manuals": "manual",
    "policies": "policy",
    "sops": "sop",
}


def load_embedder():
    """Load the BGE embedding model."""
    print("📦 Loading BAAI/bge-small-en-v1.5 embedding model...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(
        settings.EMBED_MODEL,
        cache_folder=f"{settings.MODELS_CACHE_DIR}/embeddings",
        device="cpu",
    )
    print("✅ Embedding model loaded.")
    return model


def read_markdown_files(knowledge_dir: str) -> list[dict]:
    """
    Walk the knowledge directory and read all .md files.
    Returns list of: { path, filename, category, content }
    """
    documents = []
    knowledge_dir = os.path.abspath(knowledge_dir)

    if not os.path.exists(knowledge_dir):
        print(f"❌ Knowledge directory not found: {knowledge_dir}")
        return documents

    for root, dirs, files in os.walk(knowledge_dir):
        for filename in files:
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            # Detect category from parent folder name
            parent_folder = os.path.basename(root).lower()
            category = CATEGORY_MAP.get(parent_folder, "general")

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            documents.append({
                "path": filepath,
                "filename": filename,
                "category": category,
                "content": content,
            })
            print(f"  📄 {filename} (category: {category}, {len(content)} chars)")

    return documents


def chunk_document(doc: dict) -> list[dict]:
    """
    Split a document into overlapping chunks.
    Each chunk gets a unique citation_id and preserves the section heading.
    """
    content = doc["content"]
    chunks = []

    # Split by sections (## headings) first for better context
    sections = _split_by_sections(content)

    for section_title, section_text in sections:
        # Further chunk large sections
        text_chunks = _split_text(section_text, CHUNK_SIZE, CHUNK_OVERLAP)

        for i, chunk_text in enumerate(text_chunks):
            if not chunk_text.strip():
                continue

            # Create a deterministic citation_id from content hash
            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:8]
            citation_id = f"{doc['category']}_{content_hash}"

            title = section_title or doc["filename"].replace(".md", "").replace("_", " ").title()

            chunks.append({
                "citation_id": citation_id,
                "title": title,
                "source_file": doc["filename"],
                "category": doc["category"],
                "chunk_text": chunk_text.strip(),
            })

    return chunks


def _split_by_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown text by ## headings. Returns [(heading, text), ...]"""
    import re
    sections = []
    parts = re.split(r"(^#{1,3}\s+.+$)", text, flags=re.MULTILINE)

    current_heading = ""
    current_text = ""

    for part in parts:
        if re.match(r"^#{1,3}\s+", part):
            # Save previous section
            if current_text.strip():
                sections.append((current_heading, current_text.strip()))
            current_heading = part.strip().lstrip("#").strip()
            current_text = ""
        else:
            current_text += part

    # Last section
    if current_text.strip():
        sections.append((current_heading, current_text.strip()))

    return sections if sections else [("", text)]


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks, breaking at paragraph/sentence boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size

        # Try to break at paragraph boundary
        if end < len(text):
            # Look for newline near the end
            newline_pos = text.rfind("\n\n", start + chunk_size // 2, end + 100)
            if newline_pos > start:
                end = newline_pos
            else:
                # Try sentence boundary
                period_pos = text.rfind(". ", start + chunk_size // 2, end + 50)
                if period_pos > start:
                    end = period_pos + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, end - overlap)

    return chunks


def setup_qdrant(client: QdrantClient):
    """Create or recreate the Qdrant collection."""
    collection_name = settings.QDRANT_COLLECTION

    # Check if collection exists
    existing = client.get_collections()
    existing_names = [c.name for c in existing.collections]

    if collection_name in existing_names:
        print(f"⚠️  Collection '{collection_name}' already exists. Recreating...")
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"✅ Qdrant collection '{collection_name}' created.")


def ingest_chunks(client: QdrantClient, embedder, chunks: list[dict]):
    """Embed all chunks and upsert into Qdrant."""
    collection_name = settings.QDRANT_COLLECTION

    print(f"\n🔄 Embedding {len(chunks)} chunks...")

    # Batch embed all chunk texts
    texts = [c["chunk_text"] for c in chunks]
    embeddings = embedder.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=True)

    # Build Qdrant points
    points = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["citation_id"]))
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "citation_id": chunk["citation_id"],
                    "title": chunk["title"],
                    "source_file": chunk["source_file"],
                    "category": chunk["category"],
                    "chunk_text": chunk["chunk_text"],
                },
            )
        )

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        print(f"  ✅ Upserted batch {i // batch_size + 1} ({len(batch)} points)")

    print(f"\n🎉 Successfully ingested {len(points)} chunks into Qdrant!")


def verify_ingestion(client: QdrantClient, embedder):
    """Run a test query to verify the ingestion worked."""
    collection_name = settings.QDRANT_COLLECTION

    # Get collection info
    info = client.get_collection(collection_name)
    print(f"\n📊 Collection Stats:")
    print(f"   Points: {info.points_count}")
    print(f"   Vectors: {info.vectors_count}")

    # Test search
    test_queries = [
        "How do I reset my power bank?",
        "What is the return policy?",
        "My smartwatch is not pairing",
    ]

    print(f"\n🔍 Test Searches:")
    for query in test_queries:
        query_vector = embedder.encode(query, normalize_embeddings=True).tolist()
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=2,
            with_payload=True,
        )
        print(f"\n  Q: \"{query}\"")
        for r in results:
            print(f"    → [{r.payload['category']}] {r.payload['title']} (score: {r.score:.3f})")
            print(f"      {r.payload['chunk_text'][:100]}...")


def main():
    print("=" * 60)
    print("📚 AMBRANE KNOWLEDGE BASE INGESTION")
    print("=" * 60)

    # 1. Load embedder
    embedder = load_embedder()

    # 2. Read markdown files
    print(f"\n📂 Reading knowledge base from: {os.path.abspath(KNOWLEDGE_DIR)}")
    documents = read_markdown_files(KNOWLEDGE_DIR)
    if not documents:
        print("❌ No documents found! Check the knowledge/ directory path.")
        sys.exit(1)
    print(f"\n📄 Found {len(documents)} documents.")

    # 3. Chunk documents
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
        print(f"  📝 {doc['filename']} → {len(chunks)} chunks")
    print(f"\n📝 Total chunks: {len(all_chunks)}")

    # 4. Setup Qdrant
    print(f"\n🔌 Connecting to Qdrant at {settings.QDRANT_URL}...")
    client = QdrantClient(url=settings.QDRANT_URL, timeout=30)
    setup_qdrant(client)

    # 5. Ingest
    ingest_chunks(client, embedder, all_chunks)

    # 6. Verify
    verify_ingestion(client, embedder)

    print("\n" + "=" * 60)
    print("✅ KNOWLEDGE BASE INGESTION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
