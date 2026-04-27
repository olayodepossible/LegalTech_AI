"""RAG retrieval short-circuit behaviour."""

from __future__ import annotations

import pytest


def test_retrieve_returns_empty_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_BUCKET", "")
    monkeypatch.setenv("INDEX_NAME", "idx")
    monkeypatch.setenv("SAGEMAKER_ENDPOINT", "ep")
    import api.rag_retrieval as rr

    assert rr.retrieve_user_rag_context("user_1", "hello world") == ""


def test_retrieve_returns_empty_for_blank_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_BUCKET", "b")
    monkeypatch.setenv("INDEX_NAME", "i")
    monkeypatch.setenv("SAGEMAKER_ENDPOINT", "e")
    import api.rag_retrieval as rr

    assert rr.retrieve_user_rag_context("user_1", "   ") == ""
