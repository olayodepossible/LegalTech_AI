"""Object storage abstraction (S3-compatible). Production: boto3 / aioboto3."""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class StorageClient(Protocol):
    async def put_document(self, key: str, body: bytes, content_type: str) -> str: ...
    async def get_presigned_put_url(self, key: str) -> str | None: ...


class StubStorageClient:
    """In-memory stub; swap for S3 in production."""

    def __init__(self, bucket: str | None) -> None:
        self.bucket = bucket or "stub-bucket"
        self._objects: dict[str, bytes] = {}

    async def put_document(self, key: str, body: bytes, content_type: str) -> str:
        self._objects[key] = body
        logger.info("storage.put bucket=%s key=%s bytes=%s", self.bucket, key, len(body))
        return f"s3://{self.bucket}/{key}"

    async def get_presigned_put_url(self, key: str) -> str | None:
        logger.debug("storage.presign key=%s", key)
        return f"https://example.invalid/{self.bucket}/{key}"

