"""RAG Service — low-level retrieve (optional; higher-level flows use contract/research)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from legaltech_backend.api.deps import get_rag_service
from legaltech_backend.services.rag_service import RAGService

router = APIRouter()


class RAGRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=8, ge=1, le=50)
    jurisdiction: str | None = None


@router.post("/retrieve")
async def rag_retrieve(
    body: RAGRetrieveRequest,
    svc: RAGService = Depends(get_rag_service),
) -> dict:
    filters = {"jurisdiction": body.jurisdiction} if body.jurisdiction else None
    hits = await svc.retrieve(body.query, top_k=body.top_k, filters=filters)
    return {"chunks": hits}
