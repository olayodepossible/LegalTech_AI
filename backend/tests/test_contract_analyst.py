"""Tests for contract analyst schemas and text extraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from contract_analyst.schemas import ConcernItem, ContractAnalysisResult
from contract_analyst.text_extract import extract_text_from_bytes


def test_extract_text_plain_utf8() -> None:
    raw = "Hello 世界\nline2".encode("utf-8")
    assert extract_text_from_bytes(raw, "notes.txt") == "Hello 世界\nline2"


def test_contract_analysis_result_model() -> None:
    r = ContractAnalysisResult(
        executive_summary="Summary",
        pain_points=[ConcernItem(title="p", detail="d")],
        red_flags=[],
        potential_risks=[],
    )
    assert r.executive_summary == "Summary"
    assert len(r.pain_points) == 1


def test_extract_pdf_uses_pypdf() -> None:
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page one"
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]
    with patch("contract_analyst.text_extract.PdfReader", return_value=mock_reader):
        out = extract_text_from_bytes(b"%PDF-1.4 dummy", "doc.pdf")
    assert "Page one" in out
