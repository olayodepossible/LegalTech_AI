"""Tests for ``src.client.DataAPIClient`` helpers and execute path (mocked RDS Data API)."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.client import DataAPIClient


@pytest.fixture
def mock_boto_client() -> MagicMock:
    with patch("src.client.boto3.client") as mock_boto:
        rds = MagicMock()
        mock_boto.return_value = rds
        yield rds


def test_build_parameters_types(mock_boto_client: MagicMock) -> None:
    c = DataAPIClient(
        cluster_arn="arn:aws:rds:x:1:cluster:c",
        secret_arn="arn:aws:secretsmanager:x:1:secret:s",
        database="db",
        region="eu-west-2",
    )
    params = c._build_parameters(
        {
            "n": None,
            "b": True,
            "i": 7,
            "f": 1.25,
            "d": Decimal("3.5"),
            "dt": date(2026, 1, 15),
            "ts": datetime(2026, 1, 15, 12, 0, 0),
            "j": {"a": 1},
            "arr": [1, 2],
            "s": "hello",
        }
    )
    by_name = {p["name"]: p for p in params}
    assert by_name["n"]["value"] == {"isNull": True}
    assert by_name["b"]["value"] == {"booleanValue": True}
    assert by_name["i"]["value"] == {"longValue": 7}
    assert by_name["f"]["value"] == {"doubleValue": 1.25}
    assert by_name["d"]["value"] == {"stringValue": "3.5"}
    assert by_name["j"]["value"]["stringValue"] == '{"a": 1}'
    assert by_name["arr"]["value"]["stringValue"] == "[1, 2]"


def test_extract_value_json_string(mock_boto_client: MagicMock) -> None:
    c = DataAPIClient(
        cluster_arn="arn:aws:rds:x:1:cluster:c",
        secret_arn="arn:aws:secretsmanager:x:1:secret:s",
        database="db",
        region="eu-west-2",
    )
    assert c._extract_value({"stringValue": '{"x": true}'}) == {"x": True}
    assert c._extract_value({"stringValue": "plain"}) == "plain"
    assert c._extract_value({"isNull": True}) is None
    assert c._extract_value({"longValue": 42}) == 42


def test_execute_success(mock_boto_client: MagicMock) -> None:
    mock_boto_client.execute_statement.return_value = {
        "records": [],
        "columnMetadata": [],
    }
    c = DataAPIClient(
        cluster_arn="arn:aws:rds:x:1:cluster:c",
        secret_arn="arn:aws:secretsmanager:x:1:secret:s",
        database="db",
        region="eu-west-2",
    )
    out = c.execute("SELECT 1", [])
    assert out["records"] == []
    mock_boto_client.execute_statement.assert_called_once()


def test_execute_client_error(mock_boto_client: MagicMock) -> None:
    mock_boto_client.execute_statement.side_effect = ClientError(
        {"Error": {"Code": "DatabaseErrorException", "Message": "relation \"users\" does not exist"}},
        "ExecuteStatement",
    )
    c = DataAPIClient(
        cluster_arn="arn:aws:rds:x:1:cluster:c",
        secret_arn="arn:aws:secretsmanager:x:1:secret:s",
        database="db",
        region="eu-west-2",
    )
    with pytest.raises(ClientError):
        c.execute("SELECT * FROM users")


def test_query_maps_records(mock_boto_client: MagicMock) -> None:
    mock_boto_client.execute_statement.return_value = {
        "columnMetadata": [{"name": "id"}, {"name": "title"}],
        "records": [
            [{"longValue": 1}, {"stringValue": "a"}],
        ],
    }
    c = DataAPIClient(
        cluster_arn="arn:aws:rds:x:1:cluster:c",
        secret_arn="arn:aws:secretsmanager:x:1:secret:s",
        database="db",
        region="eu-west-2",
    )
    rows = c.query("SELECT id, title FROM t", [])
    assert rows == [{"id": 1, "title": "a"}]
