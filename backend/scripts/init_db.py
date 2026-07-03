import asyncio
import structlog
from app.core.database import engine, Base
# Import all models to ensure they are registered with Base.metadata
from app.models import Customer, Order, Call, Ticket, Transcript, Message, AgentLog, ToolLog

logger = structlog.get_logger(__name__)

async def init_db():
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
