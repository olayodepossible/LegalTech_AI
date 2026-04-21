"""Document Service — uploads, storage URIs, ties to ingestion (README: Document Svc → S3)."""

from __future__ import annotations

import logging

from legaltech_backend.integrations.storage import StorageClient
from legaltech_backend.repositories.document_repository import DocumentRepository

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, repo: DocumentRepository, storage: StorageClient) -> None:
        self._repo = repo
        self._storage = storage

    async def register_upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        body: bytes,
    ) -> tuple[str, str | None]:
        rec = self._repo.create(filename, storage_uri=None, content_type=content_type)
        key = f"documents/{rec.id}/{filename}"
        uri = await self._storage.put_document(key, body, content_type or "application/octet-stream")
        rec.storage_uri = uri
        return rec.id, uri

    async def presign_upload(self, filename: str) -> tuple[str, str | None]:
        rec = self._repo.create(filename, storage_uri=None, content_type=None)
        key = f"documents/{rec.id}/{filename}"
        url = await self._storage.get_presigned_put_url(key)
        return rec.id, url

    def get_document(self, doc_id: str):
        return self._repo.get(doc_id)
