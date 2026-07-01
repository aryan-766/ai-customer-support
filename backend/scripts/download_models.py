"""Download HuggingFace models at setup time."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def download_all():
    print("📥 Downloading HuggingFace models...")
    print(f"Cache directory: {settings.MODELS_CACHE_DIR}")

    from sentence_transformers import SentenceTransformer, CrossEncoder
    from transformers import pipeline

    print(f"  Downloading embedder: {settings.EMBED_MODEL}")
    SentenceTransformer(settings.EMBED_MODEL, cache_folder=f"{settings.MODELS_CACHE_DIR}/embeddings")

    print(f"  Downloading reranker: {settings.RERANK_MODEL}")
    CrossEncoder(settings.RERANK_MODEL)

    print(f"  Downloading sentiment: {settings.SENTIMENT_MODEL}")
    pipeline("sentiment-analysis", model=settings.SENTIMENT_MODEL,
             model_kwargs={"cache_dir": f"{settings.MODELS_CACHE_DIR}/sentiment"})

    print(f"  Downloading intent classifier: {settings.INTENT_MODEL}")
    pipeline("zero-shot-classification", model=settings.INTENT_MODEL,
             model_kwargs={"cache_dir": f"{settings.MODELS_CACHE_DIR}/intent"})

    print(f"  Downloading language detector: {settings.LANG_DETECT_MODEL}")
    pipeline("text-classification", model=settings.LANG_DETECT_MODEL,
             model_kwargs={"cache_dir": f"{settings.MODELS_CACHE_DIR}/langdetect"})

    print("✅ All HuggingFace models downloaded!")


if __name__ == "__main__":
    download_all()
