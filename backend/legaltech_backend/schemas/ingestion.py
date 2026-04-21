from pydantic import BaseModel, Field


class IngestionEnqueueResponse(BaseModel):
    job_id: str
    document_id: str


class IngestionSimulateRequest(BaseModel):
    """Dev-only: push text through chunk+embed without a real worker."""

    document_id: str
    text: str = Field(..., min_length=1)
