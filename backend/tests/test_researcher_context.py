"""Tests for researcher ``context`` helpers."""

from __future__ import annotations

import pytest

pytest.importorskip("agents")

from context import (  # noqa: E402
    build_response_language_block,
    companion_message_for_code,
    should_give_companion_guidance,
)


def test_should_give_companion_guidance_greeting() -> None:
    assert should_give_companion_guidance("Hi") is True
    assert should_give_companion_guidance("thanks!") is True


def test_should_give_companion_guidance_legal_topic() -> None:
    assert should_give_companion_guidance("What is breach of contract?") is False


def test_companion_message_for_code_es() -> None:
    msg = companion_message_for_code("es")
    assert "Acompañante" in msg or "legal" in msg.lower()


def test_build_response_language_block() -> None:
    b = build_response_language_block("fr")
    assert "French" in b or "français" in b
    assert "fr" in b
