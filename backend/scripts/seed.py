"""
Convenience wrapper: runs the seed from backend/scripts/ directory.
Delegates to app/seed/seed.py.

Usage (from backend/ directory):
    python scripts/seed.py
"""
import sys
from pathlib import Path

# Add backend/ root to sys.path so app.seed.seed can be imported
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.seed.seed import main  # noqa: E402

if __name__ == "__main__":
    main()
