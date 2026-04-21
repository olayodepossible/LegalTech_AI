from fastapi import APIRouter, Depends, HTTPException, Query

from legaltech_backend.api.deps import get_document_service, get_ingestion_service
from legaltech_backend.schemas.ingestion import IngestionEnqueueResponse, IngestionSimulateRequest
from legaltech_backend.services.document_service import DocumentService
from legaltech_backend.services.ingestion_service import IngestionService

router = APIRouter()


@router.post("/enqueue", response_model=IngestionEnqueueResponse)
async def enqueue_ingestion(
    document_id: str = Query(..., min_length=1),
    svc: IngestionService = Depends(get_ingestion_service),
    documents: DocumentService = Depends(get_document_service),
) -> IngestionEnqueueResponse:
    if documents.get_document(document_id) is None:
        raise HTTPException(status_code=404, detail="document not found")
    job_id = await svc.enqueue_for_processing(document_id)
    return IngestionEnqueueResponse(job_id=job_id, document_id=document_id)


@router.post("/simulate")
async def simulate_worker(
    body: IngestionSimulateRequest,
    svc: IngestionService = Depends(get_ingestion_service),
    documents: DocumentService = Depends(get_document_service),
) -> dict:
    """
    Development helper: chunk + embed without a real queue worker.
    Guard or remove in hardened production.
    """
    if documents.get_document(body.document_id) is None:
        raise HTTPException(status_code=404, detail="document not found")
    await svc.process_document_inline(body.document_id, body.text)
    return {"status": "indexed", "document_id": body.document_id}
