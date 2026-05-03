"""Service for enqueuing background tasks."""

from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings
from app.core.logging import logger


class TaskQueueService:
    """Service for managing the arq task queue."""

    _pool = None

    async def get_pool(self):
        """Get or create the arq pool."""
        if self._pool is None:
            self._pool = await create_pool(
                RedisSettings(
                    host=settings.VALKEY_HOST or "localhost",
                    port=settings.VALKEY_PORT or 6379,
                    password=settings.VALKEY_PASSWORD or None,
                )
            )
        return self._pool

    async def enqueue_knowledge_processing(self, source_id: int):
        """Enqueue a job to process a knowledge source."""
        pool = await self.get_pool()
        job = await pool.enqueue_job("process_knowledge_source_task", source_id)
        logger.info("job_enqueued", source_id=source_id, job_id=job.job_id)
        return job.job_id

    async def close(self):
        """Close the pool."""
        if self._pool:
            await self._pool.close()


task_queue_service = TaskQueueService()
