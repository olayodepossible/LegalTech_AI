from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    storage_uri: str | None
    presigned_url: str | None = None
