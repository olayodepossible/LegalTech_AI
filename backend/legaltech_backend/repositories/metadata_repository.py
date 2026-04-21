"""Application metadata, ingestion jobs, audit (PostgreSQL in production)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class IngestionJobRecord:
    id: str
    doc_id: str
    stage: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MetadataRepository:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJobRecord] = {}

    def create_ingestion_job(self, doc_id: str) -> IngestionJobRecord:
        job_id = str(uuid.uuid4())
        rec = IngestionJobRecord(id=job_id, doc_id=doc_id, stage="queued")
        self._jobs[job_id] = rec
        logger.info("metadata.ingestion_job id=%s doc_id=%s", job_id, doc_id)
        return rec

    def get_job(self, job_id: str) -> IngestionJobRecord | None:
        return self._jobs.get(job_id)
