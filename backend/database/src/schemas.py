"""
Pydantic DTOs aligned with database/src/models.py insert/update shapes.
Tables: users, activity_history, jobs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Status values used by Jobs.update_status
JobStatus = Literal["pending", "running", "completed", "failed"]

# Suggested job_type values (models accept any str up to VARCHAR(50))
JobType = Literal[
    "portfolio_analysis",
    "rebalance",
    "projection",
    "legal_research",
    "contract_analysis",
    "ingestion",
    "document_processing",
]


class UserCreate(BaseModel):
    """Matches Users.create_user(...)."""

    clerk_user_id: str = Field(description="Primary key; Clerk user id")
    display_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)


class ActivityHistoryCreate(BaseModel):
    """Matches ActivityHistory.create_activity_history(...)."""

    clerk_user_id: str
    account_name: str = Field(..., max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    details: Optional[str] = None
    label: Optional[str] = Field(None, max_length=255)
    activity_type: Optional[str] = Field(None, max_length=100)
    activity_date: Optional[str] = Field(None, max_length=64)


class JobCreate(BaseModel):
    """Matches Jobs.create_job(clerk_user_id, job_type, request_payload=None)."""

    clerk_user_id: str
    job_type: str = Field(..., min_length=1, max_length=50)
    request_payload: Optional[Dict[str, Any]] = None


class JobUpdate(BaseModel):
    """Partial job row; maps to Jobs.update_status / update_report / etc."""

    status: Optional[JobStatus] = None
    error_message: Optional[str] = None
    report_payload: Optional[Dict[str, Any]] = None
    charts_payload: Optional[Dict[str, Any]] = None
    retirement_payload: Optional[Dict[str, Any]] = None
    summary_payload: Optional[Dict[str, Any]] = None


class RebalanceRecommendation(BaseModel):
    """Structured LLM output only; not a models.py table."""

    current_allocation: Dict[str, float] = Field(
        description="Current allocation by symbol or bucket",
    )
    target_allocation: Dict[str, float] = Field(
        description="Target allocation",
    )
    trades: List[Dict[str, Any]] = Field(
        description="Trades to reach target",
    )
    rationale: str = Field(description="Explanation")
