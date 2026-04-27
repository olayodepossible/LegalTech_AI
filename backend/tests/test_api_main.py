"""Tests for API app: health route and small pure helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_health_endpoint() -> None:
    import api.main as main

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"
    assert "timestamp" in data


def test_schema_missing_response_maps_undefined_table() -> None:
    import api.main as main

    exc = Exception('ERROR: relation "users" does not exist (42P01)')
    resp = main._schema_missing_response(exc)
    assert resp is not None
    assert resp.status_code == 503


def test_schema_missing_response_none_for_other_errors() -> None:
    import api.main as main

    assert main._schema_missing_response(Exception("timeout")) is None


def test_trace_id_from_request_header() -> None:
    import api.main as main

    req = MagicMock()
    req.headers.get = lambda k, d=None: "hdr-1" if k.lower() == "x-request-id" else d
    req.scope = {}
    assert main._trace_id_from_request(req) == "hdr-1"


def test_short_chat_title_in_main() -> None:
    import api.main as main

    assert main._short_chat_title("") == "New chat"
    t = main._short_chat_title("hello world")
    assert "hello" in t
