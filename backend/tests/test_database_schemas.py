"""Pydantic schema validation for database DTOs."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas import ActivityHistoryCreate, JobCreate, UserCreate


def test_user_create_minimal() -> None:
    u = UserCreate(clerk_user_id="user_abc")
    assert u.clerk_user_id == "user_abc"


def test_activity_history_requires_account_name() -> None:
    with pytest.raises(ValidationError):
        ActivityHistoryCreate()
    assert ActivityHistoryCreate(account_name="Alice").account_name == "Alice"


def test_job_create_job_type_length() -> None:
    with pytest.raises(ValidationError):
        JobCreate(clerk_user_id="x", job_type="")
