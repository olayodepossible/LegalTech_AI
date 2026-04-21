"""Vector database abstraction. Production: pgvector, Pinecone, Qdrant, etc."""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class VectorRecord:
    def __init__(self, doc_id: str, chunk_id: str, text: str, score: float) -> None:
        self.doc_id = doc_id
        self.chunk_id = chunk_id
        self.text = text
        self.score = score


class VectorStoreClient(Protocol):
    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        top_k: int,
        collection: str,
        filters: dict | None,
    ) -> list[VectorRecord]: ...

    async def upsert_chunks(
        self,
        doc_id: str,
        chunks: list[tuple[str, list[float]]],
        collection: str,
    ) -> None: ...


class StubVectorStoreClient:
    """Deterministic stub retrievals for local dev."""

    def __init__(self, default_collection: str) -> None:
        self.default_collection = default_collection
        self._chunks: dict[str, list[tuple[str, str, list[float]]]] = {}

    async def similarity_search(
        self,
        query_embedding: list[float],
        *,
        top_k: int,
        collection: str,
        filters: dict | None,
    ) -> list[VectorRecord]:
        _ = query_embedding, filters
        stored = self._chunks.get(collection, [])
        out: list[VectorRecord] = []
        for i, (doc_id, text, _) in enumerate(stored[:top_k]):
            out.append(VectorRecord(doc_id=doc_id, chunk_id=f"c{i}", text=text, score=0.9 - i * 0.05))
        if not out:
            out.append(
                VectorRecord(
                    doc_id="demo-doc",
                    chunk_id="c0",
                    text="[stub] Relevant clause would appear here after real embeddings are indexed.",
                    score=0.85,
                )
            )
        logger.info("vector.search collection=%s hits=%s", collection, len(out))
        return out

    async def upsert_chunks(
        self,
        doc_id: str,
        chunks: list[tuple[str, list[float]]],
        collection: str,
    ) -> None:
        lst = self._chunks.setdefault(collection, [])
        for text, emb in chunks:
            lst.append((doc_id, text, emb))
        logger.info("vector.upsert doc_id=%s chunks=%s", doc_id, len(chunks))
