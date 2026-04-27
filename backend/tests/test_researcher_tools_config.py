"""Researcher tools environment checks."""

from __future__ import annotations

from unittest.mock import patch

import tools as researcher_tools


def test_serper_search_configured_false_without_key() -> None:
    with patch.dict("os.environ", {"SERPER_API_KEY": ""}, clear=False):
        assert researcher_tools.serper_search_configured() is False
