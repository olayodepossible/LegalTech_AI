"""Async job queue abstraction. Production: Kafka, SQS, Redis Streams."""

from __future__ import annotations

import logging
import uuid
from typing import Protocol

logger = logging.getLogger(__name__)


class QueueClient(Protocol):
    async def publish_ingestion(self, payload: dict) -> str: ...


class StubQueueClient:
    async def publish_ingestion(self, payload: dict) -> str:
        job_id = str(uuid.uuid4())
        logger.info("queue.ingestion job_id=%s keys=%s", job_id, list(payload.keys()))
        return job_id
