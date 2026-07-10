"""
Ambrane AI Voice Customer Support — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from app.config import settings
from app.core.database import engine, Base
from app.core.cache import redis_manager
from app.core.models_loader import ModelRegistry
from app.api.v1 import calls, agents, analytics, tickets, knowledge, websocket, san_software
from app.utils.logger import setup_logging
from prometheus_fastapi_instrumentator import Instrumentator

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # ── Startup ────────────────────────────────────────────────────────────────
    setup_logging()
    logger.info("starting_up", app=settings.APP_NAME, env=settings.APP_ENV)

    # Connect Redis
    await redis_manager.connect()
    logger.info("redis_connected", url=settings.REDIS_URL)

    # Load HuggingFace models (blocking — must finish before serving)
    registry = ModelRegistry()
    await registry.initialize()
    logger.info("models_loaded")

    # Pre-load TTS Provider
    try:
        from app.core.tts.factory import TTSFactory
        tts = TTSFactory.get_provider()
        logger.info("preloading_tts_model")
        # Initialize early to trigger model download/loading
        tts._load_model()
    except Exception as e:
        logger.error("tts_preload_failed", error=str(e))

    # Pre-load LLM (Ollama)
    try:
        from app.core.llm.factory import LLMFactory
        llm = LLMFactory.get_provider()
        logger.info("preloading_llm_model")
        await llm.generate(prompt="hi")
    except Exception as e:
        logger.error("llm_preload_failed", error=str(e))

    # Setup Qdrant collection if missing
    from app.core.rag.retriever import setup_qdrant_collection
    await setup_qdrant_collection()
    logger.info("qdrant_ready", collection=settings.QDRANT_COLLECTION)

    # Initialize SQL database tables
    from app.core.database import create_all_tables
    await create_all_tables()
    logger.info("database_tables_initialized")

    logger.info("startup_complete", 
                docs=f"http://localhost:{settings.PORT}/docs")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("shutting_down")
    await redis_manager.disconnect()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ambrane AI Voice Support API",
        description=(
            "Multi-agent AI Voice Customer Support Platform "
            "for Ambrane Consumer Electronics"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Prometheus Metrics ─────────────────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routes ────────────────────────────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(calls.router,     prefix=prefix, tags=["Calls"])
    app.include_router(agents.router,    prefix=prefix, tags=["Agents"])
    app.include_router(analytics.router, prefix=prefix, tags=["Analytics"])
    app.include_router(tickets.router,   prefix=prefix, tags=["Tickets"])
    app.include_router(knowledge.router, prefix=prefix, tags=["Knowledge Base"])
    app.include_router(san_software.router, prefix=prefix, tags=["San Software SIP"])
    app.include_router(websocket.router, tags=["WebSocket"])

    # ── Health Check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "env": settings.APP_ENV,
        }
        
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        import traceback
        return __import__("fastapi").responses.JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__)}
        )

    return app


app = create_app()
