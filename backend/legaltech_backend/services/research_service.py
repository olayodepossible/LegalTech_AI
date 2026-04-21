"""Research Service — legal research flow via RAG (README: cases + laws)."""

from __future__ import annotations

import logging
from typing import Any

from legaltech_backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self, rag: RAGService) -> None:
        self._rag = rag

    async def research(
        self,
        query: str,
        *,
        jurisdiction: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        filters = {}
        if jurisdiction:
            filters["jurisdiction"] = jurisdiction
        system = (
            "You are a legal research assistant. Summarize relevant principles, "
            "cite sources mentioned in context, and list caveats. If context is thin, say so."
        )
        answer, citations = await self._rag.answer_with_context(
            query=query, system_prompt=system, language=language, filters=filters or None
        )
        logger.info("research.done query_chars=%s citations=%s", len(query), len(citations))
        return {
            "answer": answer,
            "citations": citations,
            "jurisdiction": jurisdiction,
            "insights": [
                "Cross-check citations against primary sources before filing.",
                "Date-filter sources in production for current law.",
            ],
        }
