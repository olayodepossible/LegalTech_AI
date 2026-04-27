"""Lambda entrypoint is a callable ASGI adapter."""

from __future__ import annotations

from api.lambda_handler import handler


def test_handler_is_callable() -> None:
    assert callable(handler)
