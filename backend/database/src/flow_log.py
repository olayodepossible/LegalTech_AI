"""
Structured JSON logs for CloudWatch: correlate requests across services via trace_id.

Log lines are single JSON objects (filter in Insights with e.g. channel = "service_flow").
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Iterator

_trace_id: ContextVar[str | None] = ContextVar("flow_trace_id", default=None)
_service: ContextVar[str] = ContextVar("flow_service", default="unknown")

_flow_logger = logging.getLogger("legaltech.flow")


def get_trace_id() -> str | None:
    return _trace_id.get()


def get_service() -> str:
    return _service.get()


def set_trace_context(trace_id: str, service: str | None = None) -> list[Token[Any]]:
    tokens: list[Token[Any]] = [_trace_id.set(trace_id)]
    if service is not None:
        tokens.append(_service.set(service))
    return tokens


def reset_trace_context(tokens: list[Token[Any]]) -> None:
    for t in reversed(tokens):
        t.var.reset(t)


@contextmanager
def trace_context(trace_id: str, service: str | None = None) -> Iterator[None]:
    tokens = set_trace_context(trace_id, service)
    try:
        yield
    finally:
        reset_trace_context(tokens)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def log_flow(
    event: str,
    *,
    step: str,
    target: str | None = None,
    duration_ms: float | None = None,
    level: int = logging.INFO,
    exc: BaseException | None = None,
    **fields: Any,
) -> None:
    """Emit one JSON log line for cross-service tracing."""
    payload: dict[str, Any] = {
        "channel": "service_flow",
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_trace_id(),
        "service": get_service(),
        "event": event,
        "step": step,
    }
    if target is not None:
        payload["target"] = target
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 3)
    for k, v in fields.items():
        if v is not None:
            payload[k] = v
    if exc is not None:
        payload["error"] = str(exc)
        payload["error_type"] = type(exc).__name__
    line = json.dumps(payload, default=str)
    _flow_logger.log(level, line)


@contextmanager
def flow_span(
    event_start: str,
    event_end: str,
    *,
    step: str,
    target: str | None = None,
    **fields: Any,
) -> Iterator[None]:
    log_flow(event_start, step=step, target=target, **fields)
    t0 = time.perf_counter()
    try:
        yield
    except BaseException as exc:
        log_flow(
            event_end + ".error",
            step=step,
            target=target,
            duration_ms=(time.perf_counter() - t0) * 1000,
            exc=exc,
            **fields,
        )
        raise
    log_flow(
        event_end,
        step=step,
        target=target,
        duration_ms=(time.perf_counter() - t0) * 1000,
        **fields,
    )
