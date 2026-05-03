"""Background task worker using arq."""

import asyncio
from arq.connections import RedisSettings
from app.core.config import settings
from app.core.logging import logger
from app.services.database import database_service
from app.services.knowledge.service import knowledge_service


async def process_knowledge_source_task(ctx: dict, source_id: int):
    """Worker task to process a knowledge source."""
    logger.info("worker_task_started", task="process_knowledge_source", source_id=source_id)
    
    async with database_service.async_session_maker() as session:
        await knowledge_service.process_source(session, source_id)


async def startup(ctx):
    """Worker startup hook."""
    logger.info("worker_starting")
    # Add any initialization if needed


async def shutdown(ctx):
    """Worker shutdown hook."""
    logger.info("worker_shutting_down")


class WorkerSettings:
    """Worker configuration for arq."""

    functions = [process_knowledge_source_task]
    redis_settings = RedisSettings(
        host=settings.VALKEY_HOST or "localhost",
        port=settings.VALKEY_PORT or 6379,
        password=settings.VALKEY_PASSWORD or None,
    )
    on_startup = startup
    on_shutdown = shutdown
    # Allow for concurrent jobs
    max_jobs = 10
    # Job timeout (10MB PDFs might take time)
    job_timeout = 300 
