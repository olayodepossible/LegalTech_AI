"""RAG Service — embed, retrieve, augment (README: Vector DB + LLM context)."""

from __future__ import annotations

import logging

from legaltech_backend.integrations.llm import LLMClient
from legaltech_backend.integrations.vector_store import VectorStoreClient
from legaltech_backend.services.embeddings import stub_embedding

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(
        self,
        vector: VectorStoreClient,
        llm: LLMClient,
        collection: str,
    ) -> None:
        self._vector = vector
        self._llm = llm
        self._collection = collection

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> list[dict]:
        emb = stub_embedding(query)
        hits = await self._vector.similarity_search(
            emb, top_k=top_k, collection=self._collection, filters=filters
        )
        return [
            {"doc_id": h.doc_id, "chunk_id": h.chunk_id, "text": h.text, "score": h.score}
            for h in hits
        ]

    async def answer_with_context(
        self,
        *,
        query: str,
        system_prompt: str,
        language: str | None = None,
        filters: dict | None = None,
    ) -> tuple[str, list[dict]]:
        contexts = await self.retrieve(query, filters=filters)
        context_block = "\n\n".join(c["text"] for c in contexts)
        user = f"Context:\n{context_block}\n\nQuestion:\n{query}"
        answer = await self._llm.complete(system_prompt, user, language=language)
        logger.info("rag.answer contexts=%s answer_chars=%s", len(contexts), len(answer))
        return answer, contexts

    async def index_document_chunks(self, doc_id: str, chunks: list[str]) -> None:
        payload = [(text, stub_embedding(text)) for text in chunks]
        await self._vector.upsert_chunks(doc_id, payload, self._collection)
