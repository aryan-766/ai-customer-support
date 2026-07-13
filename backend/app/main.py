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
        title="Ambrane AI Voice Support API (ElevenLabs Tool Server)",
        description=(
            "Backend Tool Server for ElevenLabs Conversational AI Agents "
            "handling Zoho, Shopify, and Qdrant Integrations."
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
    from app.api.v1 import calls, analytics, tickets, knowledge, eleven_webhook
    
    app.include_router(calls.router,     prefix=prefix, tags=["Calls"])
    app.include_router(analytics.router, prefix=prefix, tags=["Analytics"])
    app.include_router(tickets.router,   prefix=prefix, tags=["Tickets"])
    app.include_router(knowledge.router, prefix=prefix, tags=["Knowledge Base"])
    app.include_router(eleven_webhook.router, prefix=prefix, tags=["ElevenLabs Webhook"])

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
        from fastapi import Request, WebSocket
        logger.error("global_exception", error=str(exc), exc_info=True)
        print("GLOBAL EXCEPTION:", exc, flush=True)
        traceback.print_exc()
        
        if isinstance(request, WebSocket):
            try:
                await request.close(code=1011)
            except:
                pass
            return
            
        return __import__("fastapi").responses.JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__)}
        )

    return app


app = create_app()
