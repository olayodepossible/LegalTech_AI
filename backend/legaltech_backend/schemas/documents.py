from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    storage_uri: str | None
    presigned_url: str | None = None
