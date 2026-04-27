#!/usr/bin/env python3
"""
Run DDL against Aurora via RDS Data API.
Statements must match migrations/001_schema.sql (executed one-by-one).

``AURORA_DATABASE`` must be the PostgreSQL database name on the cluster
(``database_name`` in terraform/5_database — default ``legalcompanion``), not the
cluster identifier (e.g. ``legal-companion-aurora-cluster``). A wrong name yields
``database \"...\" does not exist``.
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(override=True)

cluster_arn = os.environ.get("AURORA_CLUSTER_ARN")
secret_arn = os.environ.get("AURORA_SECRET_ARN")
database = os.environ.get("AURORA_DATABASE", "legalcompanion")
region = os.environ.get("DEFAULT_AWS_REGION", "us-east-1")

if not cluster_arn or not secret_arn:
    print("Missing AURORA_CLUSTER_ARN or AURORA_SECRET_ARN")
    sys.exit(1)

client = boto3.client("rds-data", region_name=region)

# Keep in sync with migrations/001_schema.sql
statements = [
    'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
    """CREATE TABLE IF NOT EXISTS users (
    clerk_user_id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
)""",
    """CREATE TABLE IF NOT EXISTS activity_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    details TEXT,
    label VARCHAR(255),
    activity_type VARCHAR(100),
    activity_date VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
)""",
    """CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    request_payload JSONB,
    report_payload JSONB,
    charts_payload JSONB,
    retirement_payload JSONB,
    summary_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITHOUT TIME ZONE,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
)""",
    "CREATE INDEX IF NOT EXISTS idx_activity_history_user ON activity_history(clerk_user_id)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(clerk_user_id)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
    """CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql""",
    """CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column()""",
    """CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column()""",
    # migrations/002_legal_chats.sql — POST /api/chat persistence
    """CREATE TABLE IF NOT EXISTS legal_chats (
    id UUID PRIMARY KEY,
    clerk_user_id VARCHAR(255) NOT NULL REFERENCES users(clerk_user_id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL DEFAULT 'New chat',
    language VARCHAR(16) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
)""",
    """CREATE TABLE IF NOT EXISTS legal_chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES legal_chats(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    language_code VARCHAR(16) NOT NULL DEFAULT 'en',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT legal_chat_messages_role_check CHECK (role IN ('user', 'assistant'))
)""",
    "CREATE INDEX IF NOT EXISTS idx_legal_chats_user_updated ON legal_chats(clerk_user_id, updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_legal_chat_messages_chat_created ON legal_chat_messages(chat_id, created_at)",
]


def _hint_if_db_missing(msg: str) -> None:
    if "does not exist" not in msg.lower() or "database" not in msg.lower():
        return
    print()
    print(
        "  Hint: The database name in AURORA_DATABASE must exist on the Aurora cluster."
    )
    print(f"  You are using AURORA_DATABASE={database!r}")
    print(
        "  For Terraform Part 5 in this repo, set AURORA_DATABASE=legalcompanion "
        "(see aws_rds_cluster.aurora.database_name)."
    )
    print(
        "  Do not use the cluster id (e.g. legal-companion-aurora-cluster) or "
        "legal-companion as the database name unless you created that database."
    )


def main() -> None:
    print("Running migrations...")
    print(f"  database={database!r}  region={region!r}")
    ok = 0
    err = 0
    for i, stmt in enumerate(statements, 1):
        first = next((ln for ln in stmt.split("\n") if ln.strip()), stmt)[:70]
        print(f"\n[{i}/{len(statements)}] {first}...")
        try:
            client.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database,
                sql=stmt,
            )
            print("   ok")
            ok += 1
        except ClientError as e:
            msg = e.response["Error"]["Message"]
            if "already exists" in msg.lower():
                print("   exists (skip)")
                ok += 1
            else:
                print(f"   error: {msg[:200]}")
                _hint_if_db_missing(msg)
                err += 1

    print(f"\nDone: {ok} ok, {err} errors")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
