"""Tests for ``search_s3vectors`` Lambda handler (mocked AWS)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import search_s3vectors as ss


def test_lambda_handler_missing_query() -> None:
    r = ss.lambda_handler({"body": json.dumps({})}, None)
    assert r["statusCode"] == 400
    body = json.loads(r["body"])
    assert "error" in body


def test_lambda_handler_success() -> None:
    with patch.object(ss, "get_embedding", return_value=[0.1, 0.2]):
        mock_s3v = MagicMock()
        mock_s3v.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "k1",
                    "distance": 0.5,
                    "metadata": {"text": "hello"},
                }
            ]
        }
        with patch.object(ss, "s3_vectors", mock_s3v):
            r = ss.lambda_handler(
                {"body": json.dumps({"query": "test", "k": 3})},
                None,
            )
    assert r["statusCode"] == 200
    payload = json.loads(r["body"])
    assert payload["count"] == 1
    assert payload["results"][0]["id"] == "k1"
