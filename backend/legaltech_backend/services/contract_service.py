"""Contract Service — analysis flow using Document + RAG (README: Contract Analysis)."""

from __future__ import annotations

import logging
from typing import Any

from legaltech_backend.services.document_service import DocumentService
from legaltech_backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class ContractService:
    def __init__(self, documents: DocumentService, rag: RAGService) -> None:
        self._documents = documents
        self._rag = rag

    async def analyze(
        self,
        *,
        query: str,
        doc_id: str | None,
        language: str | None = None,
    ) -> dict[str, Any]:
        doc_hint = ""
        if doc_id:
            rec = self._documents.get_document(doc_id)
            if rec:
                doc_hint = f" Focus on document {doc_id} ({rec.filename}), storage={rec.storage_uri}."
        system = (
            "You are a contracts analyst. Identify risks, ambiguous clauses, and suggestions. "
            "Structure: Risks, Key clauses, Recommendations."
        )
        full_query = query + doc_hint
        answer, contexts = await self._rag.answer_with_context(
            query=full_query,
            system_prompt=system,
            language=language,
            filters={"doc_id": doc_id} if doc_id else None,
        )
        logger.info("contract.analyze doc_id=%s contexts=%s", doc_id, len(contexts))
        return {
            "summary": answer,
            "retrieved_clauses": contexts,
            "document_id": doc_id,
            "risks": [],  # populate via structured LLM JSON in production
            "suggestions": [],
        }
