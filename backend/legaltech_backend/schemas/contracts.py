from pydantic import BaseModel, Field


class ConcernItem(BaseModel):
    """A single identified issue in the contract (aligned with `contract_analyst` package)."""

    title: str = Field(..., description="Short label for the issue")
    detail: str = Field(..., description="Why it matters and what to watch for")


class ContractAnalysisResult(BaseModel):
    """Structured contract analysis — same shape as POST /api/contracts/analyze (contract_analyst package, in-process)."""

    executive_summary: str = Field(
        ...,
        description="Brief overview of the document and overall posture for the user",
    )
    pain_points: list[ConcernItem] = Field(default_factory=list)
    red_flags: list[ConcernItem] = Field(default_factory=list)
    potential_risks: list[ConcernItem] = Field(default_factory=list)


class ContractAnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_id: str | None = None
    language: str | None = Field(default=None, description="ISO-ish language hint for LLM")


class ContractAnalyzeResponse(BaseModel):
    """Legacy RAG-shaped response; prefer ContractAnalysisResult for OpenAI analysis."""

    summary: str
    document_id: str | None
    retrieved_clauses: list[dict]
    risks: list[str]
    suggestions: list[str]
