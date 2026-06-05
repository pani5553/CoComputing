"""
Idempotent seed script for Co-Computing tasks.

Usage (from the backend/ directory with the virtual environment activated):
    python app/seed/seed.py

Or from the project root:
    python backend/app/seed/seed.py

Reads SUPABASE_DB_URL from the .env file in the backend/ directory
(or from environment variables directly).
"""
import os
import sys
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Allow running from any directory by adding backend/ to sys.path
# ──────────────────────────────────────────────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env before importing settings
from dotenv import load_dotenv  # noqa: E402 — must come after sys.path manipulation

env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"[WARN] .env not found at {env_path}. Relying on environment variables.")

import psycopg2  # noqa: E402

SQL_FILE = Path(__file__).parent / "tasks_seed.sql"


def main() -> None:
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("[ERROR] SUPABASE_DB_URL is not set. Check your .env file.")
        sys.exit(1)

    if not SQL_FILE.exists():
        print(f"[ERROR] Seed SQL file not found: {SQL_FILE}")
        sys.exit(1)

    sql = SQL_FILE.read_text(encoding="utf-8")

    print(f"[INFO] Connecting to database...")
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                print(f"[INFO] Executing seed from {SQL_FILE.name} ...")
                cur.execute(sql)
                conn.commit()
                print("[OK] Seed executed successfully. Existing rows were not modified.")
    except psycopg2.Error as exc:
        print(f"[ERROR] Database error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
