"""Tests for ``src.flow_log`` (structured tracing)."""

from __future__ import annotations

import json
import logging

import pytest

from src.flow_log import (
    flow_span,
    get_service,
    get_trace_id,
    log_flow,
    new_trace_id,
    reset_trace_context,
    set_trace_context,
    trace_context,
)


def test_trace_context_sets_and_clears_trace_id() -> None:
    tid = new_trace_id()
    assert get_trace_id() is None
    with trace_context(tid, "svc-a"):
        assert get_trace_id() == tid
        assert get_service() == "svc-a"
    assert get_trace_id() is None


def test_set_reset_tokens() -> None:
    tokens = set_trace_context("t-1", "api")
    try:
        assert get_trace_id() == "t-1"
        assert get_service() == "api"
    finally:
        reset_trace_context(tokens)
    assert get_trace_id() is None


def test_log_flow_emits_json_with_channel(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="legaltech.flow")
    with trace_context("trace-xyz", "test"):
        log_flow("evt1", step="s1", target="t1", extra_field=42)
    assert any("service_flow" in r.message for r in caplog.records)
    line = next(r.message for r in caplog.records if "service_flow" in r.message)
    data = json.loads(line)
    assert data["channel"] == "service_flow"
    assert data["trace_id"] == "trace-xyz"
    assert data["service"] == "test"
    assert data["event"] == "evt1"
    assert data["step"] == "s1"
    assert data["target"] == "t1"
    assert data["extra_field"] == 42


def test_flow_span_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="legaltech.flow")
    with trace_context("t2", "test"):
        with flow_span("a", "b", step="st", target="tg", k=1):
            pass
    msgs = [json.loads(r.message) for r in caplog.records if r.message.startswith("{")]
    events = [m["event"] for m in msgs]
    assert "a" in events and "b" in events


def test_flow_span_records_error(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="legaltech.flow")
    with trace_context("t3", "test"):
        with pytest.raises(ValueError, match="boom"):
            with flow_span("a", "b", step="st"):
                raise ValueError("boom")
    msgs = [json.loads(r.message) for r in caplog.records if r.message.startswith("{")]
    assert any(m.get("event") == "b.error" for m in msgs)
    assert any(m.get("error_type") == "ValueError" for m in msgs)
