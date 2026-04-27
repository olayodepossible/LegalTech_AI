"""Tests for researcher evaluation models and heuristics."""

from __future__ import annotations

import pytest

pytest.importorskip("agents")

from research_evaluation import (  # noqa: E402
    ResearchEvaluation,
    needs_search_refinement,
)


def test_needs_search_refinement_when_inadequate() -> None:
    ev = ResearchEvaluation(adequate=False, confidence=0.9)
    assert needs_search_refinement(ev) is True


def test_needs_search_refinement_low_confidence() -> None:
    ev = ResearchEvaluation(adequate=True, confidence=0.5)
    assert needs_search_refinement(ev) is True


def test_needs_search_refinement_ok() -> None:
    ev = ResearchEvaluation(adequate=True, confidence=0.9)
    assert needs_search_refinement(ev) is False


def test_research_evaluation_coerce_queries() -> None:
    ev = ResearchEvaluation(
        adequate=True,
        suggested_search_queries=["a", "", "b"],
    )
    assert ev.suggested_search_queries == ["a", "b"]
