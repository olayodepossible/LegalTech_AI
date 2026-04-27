"""Tests for legacy ``ingest_s3vectors`` Lambda handler."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import ingest_s3vectors as ing


def test_lambda_missing_text() -> None:
    r = ing.lambda_handler({"body": json.dumps({"metadata": {}})}, None)
    assert r["statusCode"] == 400


def test_lambda_success() -> None:
    with patch.object(ing, "get_embedding", return_value=[0.1, 0.2]):
        mock_s3v = MagicMock()
        with patch.object(ing, "s3_vectors", mock_s3v):
            r = ing.lambda_handler(
                {"body": json.dumps({"text": "hello", "metadata": {"src": "t"}})},
                None,
            )
    assert r["statusCode"] == 200
    payload = json.loads(r["body"])
    assert "document_id" in payload
    mock_s3v.put_vectors.assert_called_once()
