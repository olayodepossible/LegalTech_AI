from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    jurisdiction: str | None = None
    language: str | None = None


class ResearchResponse(BaseModel):
    answer: str
    citations: list[dict]
    jurisdiction: str | None
    insights: list[str]
