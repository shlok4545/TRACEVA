"""Development-only demo reset command.

Usage:
    python -m app.db.reset_demo

This script resets the SQLite demo database to a clean seeded state. It is intentionally
restricted to local development and should never be exposed in the production user interface.
"""

from __future__ import annotations

from app.db.init_db import init_db

if __name__ == "__main__":
    print("DEVELOPMENT ONLY: resetting TRACEVA demo database...")
    init_db()
    print("TRACEVA demo database ready.")
