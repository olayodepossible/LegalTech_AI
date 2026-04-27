"""Tests for API RAG retrieval configuration gate."""

from __future__ import annotations

import pytest


def test_configured_requires_all_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_BUCKET", "b")
    monkeypatch.setenv("INDEX_NAME", "i")
    monkeypatch.setenv("SAGEMAKER_ENDPOINT", "e")
    import api.rag_retrieval as rr

    assert rr._configured() is True


def test_configured_false_if_any_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTOR_BUCKET", "")
    monkeypatch.setenv("INDEX_NAME", "i")
    monkeypatch.setenv("SAGEMAKER_ENDPOINT", "e")
    import api.rag_retrieval as rr

    assert rr._configured() is False
