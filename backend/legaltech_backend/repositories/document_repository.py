"""Document metadata store."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class DocumentRecord:
    id: str
    filename: str
    storage_uri: str | None
    content_type: str | None
    status: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DocumentRepository:
    """In-memory registry; replace with SQLAlchemy + PostgreSQL."""

    def __init__(self) -> None:
        self._by_id: dict[str, DocumentRecord] = {}

    def create(self, filename: str, storage_uri: str | None, content_type: str | None) -> DocumentRecord:
        doc_id = str(uuid.uuid4())
        rec = DocumentRecord(
            id=doc_id,
            filename=filename,
            storage_uri=storage_uri,
            content_type=content_type,
            status="pending",
        )
        self._by_id[doc_id] = rec
        logger.info("doc.create id=%s filename=%s", doc_id, filename)
        return rec

    def get(self, doc_id: str) -> DocumentRecord | None:
        return self._by_id.get(doc_id)

    def update_status(self, doc_id: str, status: str) -> DocumentRecord | None:
        rec = self._by_id.get(doc_id)
        if rec:
            rec.status = status
        return rec
