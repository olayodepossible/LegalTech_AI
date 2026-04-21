from pydantic import BaseModel, Field


class ContractAnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_id: str | None = None
    language: str | None = Field(default=None, description="ISO-ish language hint for LLM")


class ContractAnalyzeResponse(BaseModel):
    summary: str
    document_id: str | None
    retrieved_clauses: list[dict]
    risks: list[str]
    suggestions: list[str]
