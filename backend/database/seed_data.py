#!/usr/bin/env python3
"""
Seed data using the same column sets as models.py (Users, ActivityHistory, Jobs).
Requires AURORA_CLUSTER_ARN, AURORA_SECRET_ARN, and RDS Data API.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.schemas import ActivityHistoryCreate, JobCreate, UserCreate

load_dotenv(override=True)

cluster_arn = os.environ.get("AURORA_CLUSTER_ARN")
secret_arn = os.environ.get("AURORA_SECRET_ARN")
database = os.environ.get("AURORA_DATABASE", "legalcompanion")
region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not cluster_arn or not secret_arn:
    print("Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN in environment")
    sys.exit(1)

client = boto3.client("rds-data", region_name=region)


def _exec(sql: str, parameters: list | None = None) -> dict:
    kwargs: dict = {
        "resourceArn": cluster_arn,
        "secretArn": secret_arn,
        "database": database,
        "sql": sql,
    }
    if parameters:
        kwargs["parameters"] = parameters
    return client.execute_statement(**kwargs)


def _string_param(name: str, value: str | None) -> dict:
    if value is None:
        return {"name": name, "value": {"isNull": True}}
    return {"name": name, "value": {"stringValue": value}}


def upsert_user(row: dict) -> bool:
    try:
        u = UserCreate(**row)
    except ValidationError as e:
        print(f"  User validation error: {e}")
        return False
    v = u.model_dump(exclude_none=True)
    sql = """
        INSERT INTO users (clerk_user_id, display_name, email)
        VALUES (:clerk_user_id, :display_name, :email)
        ON CONFLICT (clerk_user_id) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            email = EXCLUDED.email,
            updated_at = NOW()
    """
    params = [
        {"name": "clerk_user_id", "value": {"stringValue": v["clerk_user_id"]}},
        _string_param("display_name", v.get("display_name")),
        _string_param("email", v.get("email")),
    ]
    try:
        _exec(sql, params)
        return True
    except ClientError as e:
        print(f"  User insert error: {e.response['Error']['Message'][:120]}")
        return False


def insert_activity(row: dict) -> bool:
    try:
        a = ActivityHistoryCreate(**row)
    except ValidationError as e:
        print(f"  Activity validation error: {e}")
        return False
    v = a.model_dump(exclude_none=True)
    cols = list(v.keys())
    ph = ", ".join(f":{c}" for c in cols)
    sql = f"INSERT INTO activity_history ({', '.join(cols)}) VALUES ({ph})"
    params: list[dict] = []
    for c in cols:
        val = v[c]
        if val is None:
            params.append({"name": c, "value": {"isNull": True}})
        else:
            params.append({"name": c, "value": {"stringValue": str(val)}})
    try:
        _exec(sql, params)
        return True
    except ClientError as e:
        print(f"  Activity insert error: {e.response['Error']['Message'][:120]}")
        return False


def insert_job(row: dict) -> bool:
    try:
        j = JobCreate(**row)
    except ValidationError as e:
        print(f"  Job validation error: {e}")
        return False
    v = j.model_dump(exclude_none=True)
    clerk_user_id = v["clerk_user_id"]
    job_type = v["job_type"]
    payload = v.get("request_payload")

    if payload is None:
        sql = """
            INSERT INTO jobs (clerk_user_id, job_type, status, request_payload)
            VALUES (:clerk_user_id, :job_type, 'pending', CAST(:request_payload AS jsonb))
        """
        params = [
            {"name": "clerk_user_id", "value": {"stringValue": clerk_user_id}},
            {"name": "job_type", "value": {"stringValue": job_type}},
            {"name": "request_payload", "value": {"isNull": True}},
        ]
    else:
        sql = """
            INSERT INTO jobs (clerk_user_id, job_type, status, request_payload)
            VALUES (:clerk_user_id, :job_type, 'pending', CAST(:request_payload AS jsonb))
        """
        params = [
            {"name": "clerk_user_id", "value": {"stringValue": clerk_user_id}},
            {"name": "job_type", "value": {"stringValue": job_type}},
            {"name": "request_payload", "value": {"stringValue": json.dumps(payload)}},
        ]
    try:
        _exec(sql, params)
        return True
    except ClientError as e:
        print(f"  Job insert error: {e.response['Error']['Message'][:120]}")
        return False


def main() -> None:
    print("Seeding users, activity_history, jobs")
    print("=" * 50)

    users = [
        {
            "clerk_user_id": "user_seed_demo_001",
            "display_name": "Demo Lawyer",
            "email": "demo@example.com",
        },
        {
            "clerk_user_id": "user_seed_demo_002",
            "display_name": "Second User",
            "email": "second@example.com",
        },
    ]

    ok = 0
    for u in users:
        if upsert_user(u):
            ok += 1
            print(f"  user ok: {u['clerk_user_id']}")
    print(f"Users: {ok}/{len(users)}")

    activities = [
        {
            "clerk_user_id": "user_seed_demo_001",
            "account_name": "Primary",
            "email": "demo@example.com",
            "details": "Opened dashboard",
            "label": "visit_dashboard",
            "activity_type": "visit_dashboard",
            "activity_date": "2026-04-18",
        },
        {
            "clerk_user_id": "user_seed_demo_001",
            "account_name": "Primary",
            "email": "demo@example.com",
            "details": "Legal research query",
            "label": "chat_message",
            "activity_type": "chat_message",
            "activity_date": "2026-04-18",
        },
    ]
    a_ok = 0
    for a in activities:
        if insert_activity(a):
            a_ok += 1
    print(f"Activity rows: {a_ok}/{len(activities)}")

    jobs = [
        {
            "clerk_user_id": "user_seed_demo_001",
            "job_type": "legal_research",
            "request_payload": {"query": "duty of care", "jurisdiction": "US"},
        },
        {
            "clerk_user_id": "user_seed_demo_001",
            "job_type": "contract_analysis",
            "request_payload": {"document_id": "doc-123"},
        },
        {
            "clerk_user_id": "user_seed_demo_002",
            "job_type": "ingestion",
        },
    ]
    j_ok = 0
    for j in jobs:
        if insert_job(j):
            j_ok += 1
    print(f"Jobs: {j_ok}/{len(jobs)}")

    try:
        r = _exec("SELECT COUNT(*) AS c FROM users")
        n = r["records"][0][0].get("longValue", 0)
        print(f"\nusers row count: {n}")
    except ClientError as e:
        print(f"verify error: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
