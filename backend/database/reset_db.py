#!/usr/bin/env python3
"""
Drop tables, run migrations, seed data, optionally add extra test rows via models.
Aligned with models.py (users, activity_history, jobs).
"""

import argparse
import subprocess
import sys
from pathlib import Path

from src.client import DataAPIClient
from src.models import Database


def drop_all_tables(db: DataAPIClient) -> None:
    print("Dropping existing tables (FK order)...")
    tables_to_drop = [
        "activity_history",
        "jobs",
        "users",
    ]
    for table in tables_to_drop:
        try:
            db.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            print(f"   Dropped {table}")
        except Exception as e:
            print(f"   Warning dropping {table}: {e}")

    try:
        db.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
        print("   Dropped update_updated_at_column (if existed)")
    except Exception as e:
        print(f"   Warning dropping function: {e}")


def create_test_data(db_models: Database) -> None:
    print("\nCreating extra test rows via models API...")
    uid = "test_user_001"
    existing = db_models.users.find_by_clerk_id(uid)
    if not existing:
        db_models.users.create_user(
            clerk_user_id=uid,
            display_name="Test User",
            email="test@example.com",
        )
        print("   Created test user")
    else:
        print("   Test user already exists")

    acts = db_models.activity_history.find_by_user(uid)
    if not acts:
        db_models.activity_history.create_activity_history(
            clerk_user_id=uid,
            account_name="Workspace",
            email="test@example.com",
            details="Seed from reset_db",
            label="signup",
            activity_type="signup",
            activity_date="2026-04-18",
        )
        print("   Created sample activity_history")
    else:
        print("   User already has activity rows")

    jobs = db_models.jobs.find_by_user(uid, limit=5)
    if not jobs:
        db_models.jobs.create_job(
            uid,
            "ingestion",
            request_payload={"source": "reset_db"},
        )
        print("   Created sample job")
    else:
        print("   User already has jobs")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset LegalTech database")
    parser.add_argument(
        "--with-test-data",
        action="store_true",
        help="Create test user / activity / job via Python models",
    )
    parser.add_argument(
        "--skip-drop",
        action="store_true",
        help="Skip drop + migrations (only seed + optional test data)",
    )
    args = parser.parse_args()

    print("Database reset")
    print("=" * 50)

    db = DataAPIClient()
    db_models = Database()

    if not args.skip_drop:
        drop_all_tables(db)
        print("\nRunning migrations...")
        root = Path(__file__).resolve().parent
        result = subprocess.run(
            ["uv", "run", "run_migrations.py"],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Migration failed!")
            print(result.stderr)
            sys.exit(1)
        print("Migrations completed")

    print("\nLoading seed_data.py...")
    root = Path(__file__).resolve().parent
    result = subprocess.run(
        ["uv", "run", "seed_data.py"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Seed failed!")
        print(result.stderr)
        print(result.stdout)
        sys.exit(1)
    print(result.stdout or "Seed completed")

    if args.with_test_data:
        create_test_data(db_models)

    print("\nRow counts:")
    for table in ("users", "activity_history", "jobs"):
        try:
            rows = db.query(f"SELECT COUNT(*) AS count FROM {table}")
            count = rows[0].get("count", 0) if rows else 0
            print(f"   {table}: {count}")
        except Exception as e:
            print(f"   {table}: error {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
