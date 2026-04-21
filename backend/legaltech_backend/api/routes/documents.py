from fastapi import APIRouter, Depends, File, Query, UploadFile

from legaltech_backend.api.deps import get_document_service
from legaltech_backend.schemas.documents import DocumentUploadResponse
from legaltech_backend.services.document_service import DocumentService

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    svc: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    body = await file.read()
    doc_id, uri = await svc.register_upload(
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        body=body,
    )
    return DocumentUploadResponse(document_id=doc_id, storage_uri=uri)


@router.post("/presign", response_model=DocumentUploadResponse)
async def presign_upload(
    filename: str = Query(..., min_length=1),
    svc: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    doc_id, url = await svc.presign_upload(filename)
    return DocumentUploadResponse(document_id=doc_id, storage_uri=None, presigned_url=url)
