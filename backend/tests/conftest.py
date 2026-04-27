"""
Shared pytest configuration: PYTHONPATH, minimal env vars, ``flow_log`` alias for ingest worker.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Required before importing api.main or src.Database
os.environ.setdefault(
    "AURORA_CLUSTER_ARN",
    "arn:aws:rds:eu-west-2:123456789012:cluster:pytest-dummy",
)
os.environ.setdefault(
    "AURORA_SECRET_ARN",
    "arn:aws:secretsmanager:eu-west-2:123456789012:secret:pytest-dummy",
)
os.environ.setdefault("AURORA_DATABASE", "legalcompanion")
os.environ.setdefault("DEFAULT_AWS_REGION", "eu-west-2")
os.environ.setdefault("CLERK_JWKS_URL", "https://clerk.pytest.invalid/.well-known/jwks.json")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

for _p in (
    BACKEND_ROOT / "database",
    BACKEND_ROOT / "ingest",
    BACKEND_ROOT / "researcher",
    BACKEND_ROOT,
):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

import src.flow_log as _flow_log_mod

sys.modules.setdefault("flow_log", _flow_log_mod)
