"""Tests for ``rag_core`` embedding helper (mocked SageMaker)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import rag_core as rc


def test_new_vector_id_is_uuid_shape() -> None:
    u = rc.new_vector_id()
    assert len(u) == 36 and u.count("-") == 4


def test_get_embedding_nested_list() -> None:
    body = MagicMock()
    body.read.return_value = json.dumps([[[0.1, 0.2, 0.3]]]).encode()
    mock_sr = MagicMock()
    mock_sr.invoke_endpoint.return_value = {"Body": body}
    with patch.object(rc, "SAGEMAKER_ENDPOINT", "ep-test"):
        with patch.object(rc, "sagemaker_runtime", mock_sr):
            vec = rc.get_embedding("hi")
    assert vec == [0.1, 0.2, 0.3]


def test_get_embedding_missing_endpoint() -> None:
    with patch.object(rc, "SAGEMAKER_ENDPOINT", None):
        with pytest.raises(RuntimeError, match="SAGEMAKER_ENDPOINT"):
            rc.get_embedding("x")
