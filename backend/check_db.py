"""Check the configured database connection and report production tables."""
from __future__ import annotations

import json

from backend.database import Database


EXPECTED_TABLES = {"devices", "telemetry", "commands", "watering_events", "ai_predictions"}


def check_database(db: Database) -> dict:
    ping = db.one("SELECT 1 AS connected")
    if not ping or int(ping["connected"]) != 1:
        raise RuntimeError("Database connectivity probe failed")
    if db.sqlite:
        rows = db.all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    else:
        rows = db.all("SELECT table_name AS name FROM information_schema.tables WHERE table_schema=current_schema() ORDER BY table_name")
    tables = [row["name"] for row in rows]
    missing = sorted(EXPECTED_TABLES - set(tables))
    if missing:
        raise RuntimeError(f"Production schema is incomplete; missing tables: {missing}")
    return {"status": "ok", "database": "sqlite" if db.sqlite else "postgresql",
            "tables": [name for name in tables if name in EXPECTED_TABLES]}


def main() -> None:
    db = Database()
    try:
        print(json.dumps(check_database(db), ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
