"""Ingestion / worker orchestration — OCR, chunk, embed (README: queue → worker → vector DB)."""

from __future__ import annotations

import logging

from legaltech_backend.integrations.queue import QueueClient
from legaltech_backend.repositories.document_repository import DocumentRepository
from legaltech_backend.repositories.metadata_repository import MetadataRepository
from legaltech_backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        documents: DocumentRepository,
        metadata: MetadataRepository,
        queue: QueueClient,
        rag: RAGService,
    ) -> None:
        self._documents = documents
        self._metadata = metadata
        self._queue = queue
        self._rag = rag

    async def enqueue_for_processing(self, doc_id: str) -> str:
        """Publish job; a real worker would consume and call `process_document_inline` or similar."""
        job = self._metadata.create_ingestion_job(doc_id)
        await self._queue.publish_ingestion({"job_id": job.id, "doc_id": doc_id})
        self._documents.update_status(doc_id, "queued")
        return job.id

    async def process_document_inline(self, doc_id: str, text: str) -> None:
        """
        Simulate worker: chunk naïvely, embed, upsert to vector store.
        Production: OCR/Tika, semantic chunking, idempotent hashes (README continuous RAG).
        """
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not chunks:
            chunks = [text[:2000]]
        await self._rag.index_document_chunks(doc_id, chunks[:50])
        self._documents.update_status(doc_id, "indexed")
        logger.info("ingestion.done doc_id=%s chunks=%s", doc_id, len(chunks))
