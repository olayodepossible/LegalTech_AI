"""Pydantic models for contract analysis responses."""

from pydantic import BaseModel, Field


class ConcernItem(BaseModel):
    """A single identified issue in the contract."""

    title: str = Field(..., description="Short label for the issue")
    detail: str = Field(..., description="Why it matters and what to watch for")


class ContractAnalysisResult(BaseModel):
    """Structured output from the contract analysis model."""

    executive_summary: str = Field(
        ...,
        description="Brief overview of the document and overall posture for the user",
    )
    pain_points: list[ConcernItem] = Field(
        default_factory=list,
        description="Ambiguities, one-sided terms, or operational friction for the user",
    )
    red_flags: list[ConcernItem] = Field(
        default_factory=list,
        description="Clauses that are unusually risky, unconscionable, or may be void",
    )
    potential_risks: list[ConcernItem] = Field(
        default_factory=list,
        description="Legal, financial, or enforcement risks if the contract is signed as-is",
    )
