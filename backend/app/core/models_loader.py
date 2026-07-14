"""
HuggingFace Model Registry — loads all AI models once at startup.
Singleton pattern ensures models stay in RAM across requests.
"""

import asyncio
import structlog
from functools import lru_cache

from app.config import settings

logger = structlog.get_logger(__name__)


class ModelRegistry:
    """
    Singleton registry for all HuggingFace models.
    Models are loaded once at startup and reused for every request.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance.embedder = None
            cls._instance.reranker = None
            cls._instance.sentiment_analyzer = None
            cls._instance.intent_classifier = None
            cls._instance.lang_detector = None
            cls._instance.lang_detector = None
        return cls._instance

    async def initialize(self):
        if self._initialized:
            return

        logger.info("loading_models", note="This takes 1-2 minutes on first run...")

        # Run blocking model loads in thread pool (don't block event loop)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_all_models)

        self._initialized = True
        logger.info("models_ready")

    def _load_all_models(self):
        """Blocking model loading — runs in thread pool."""
        from sentence_transformers import SentenceTransformer, CrossEncoder
        from transformers import pipeline
        cache_dir = settings.MODELS_CACHE_DIR

        # 2. BGE Embedder (for RAG)
        logger.info("loading_embedder", model=settings.EMBED_MODEL)
        self.embedder = SentenceTransformer(
            settings.EMBED_MODEL,
            cache_folder=f"{cache_dir}/embeddings",
            device="cpu",
        )
        logger.info("embedder_loaded")

        # 3. Cross-Encoder Reranker (for RAG quality boost)
        logger.info("loading_reranker", model=settings.RERANK_MODEL)
        self.reranker = CrossEncoder(
            settings.RERANK_MODEL,
            max_length=512,
            device="cpu",
        )
        logger.info("reranker_loaded")

        # 4. Sentiment Analysis
        logger.info("loading_sentiment", model=settings.SENTIMENT_MODEL)
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=settings.SENTIMENT_MODEL,
            device=-1,
            model_kwargs={"cache_dir": f"{cache_dir}/sentiment"},
        )
        logger.info("sentiment_loaded")

        # 5. Intent Classification (Zero-Shot — no training needed)
        logger.info("loading_intent", model=settings.INTENT_MODEL)
        self.intent_classifier = pipeline(
            "zero-shot-classification",
            model=settings.INTENT_MODEL,
            device=-1,
            model_kwargs={"cache_dir": f"{cache_dir}/intent"},
        )
        logger.info("intent_loaded")

        # 6. Language Detection
        logger.info("loading_lang_detector", model=settings.LANG_DETECT_MODEL)
        self.lang_detector = pipeline(
            "text-classification",
            model=settings.LANG_DETECT_MODEL,
            device=-1,
            model_kwargs={"cache_dir": f"{cache_dir}/langdetect"},
        )
        logger.info("lang_detector_loaded")

    # ── Convenience Methods ────────────────────────────────────────────────────

    def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns 384-dim vector."""
        return self.embedder.encode(text, normalize_embeddings=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one batch (faster)."""
        return self.embedder.encode(
            texts, normalize_embeddings=True, batch_size=32
        ).tolist()

    def rerank(self, query: str, candidates: list[str]) -> list[float]:
        """Score query-candidate pairs. Returns list of float scores."""
        pairs = [(query, c) for c in candidates]
        return self.reranker.predict(pairs).tolist()

    def detect_sentiment(self, text: str) -> dict:
        """
        Returns: { sentiment: 'positive'|'neutral'|'angry', score: float }
        """
        result = self.sentiment_analyzer(text[:512])[0]
        label_map = {
            "LABEL_0": "angry",
            "LABEL_1": "neutral",
            "LABEL_2": "positive",
            "negative": "angry",
            "neutral": "neutral",
            "positive": "positive",
        }
        return {
            "sentiment": label_map.get(result["label"], "neutral"),
            "score": float(result["score"]),
        }

    def detect_intent(self, text: str) -> dict:
        """
        Zero-shot intent classification — no training needed!
        Returns: { intent: str, confidence: float, all_scores: dict }
        """
        labels = [
            "product support",
            "warranty claim",
            "invoice request",
            "order status",
            "return request",
            "replacement request",
            "complaint",
            "talk to human",
            "product registration",
        ]
        result = self.intent_classifier(text[:512], labels)
        intent_map = {
            "product support": "product_support",
            "warranty claim": "warranty",
            "invoice request": "invoice",
            "order status": "order_status",
            "return request": "return",
            "replacement request": "replacement",
            "complaint": "complaint",
            "talk to human": "talk_to_human",
            "product registration": "registration",
        }
        top_label = result["labels"][0]
        return {
            "intent": intent_map.get(top_label, "complaint"),
            "confidence": float(result["scores"][0]),
            "all_scores": {
                intent_map.get(l, l): float(s)
                for l, s in zip(result["labels"], result["scores"])
            },
        }

    def detect_language(self, text: str) -> str:
        """Returns: 'en', 'hi', or ISO language code."""
        result = self.lang_detector(text[:256])[0]
        return result["label"].lower()
