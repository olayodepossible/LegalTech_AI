"""Tests for RAG ingest worker helpers."""

from __future__ import annotations

import pytest

import rag_ingest_worker as w


def test_chunks_splits_with_overlap() -> None:
    text = " ".join(str(i) for i in range(50))
    parts = w._chunks(text, size=20, overlap=5)
    assert len(parts) >= 2
    assert all(len(p) <= 20 for p in parts)


def test_chunks_empty() -> None:
    assert w._chunks("", 100, 10) == []
    assert w._chunks("   \n  ", 100, 10) == []


def test_extract_text_plain() -> None:
    assert w._extract_text(b"hello", "text/plain", "f.txt") == "hello"


def test_extract_text_unsupported() -> None:
    with pytest.raises(RuntimeError, match="Unsupported type"):
        w._extract_text(b"x", "application/zip", "f.bin")
