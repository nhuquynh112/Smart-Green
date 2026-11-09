"""Create a portable JSON backup of all Smart-Green production tables."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from backend.database import Database

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "devices": "device_id",
    "telemetry": "device_id,boot_id,sample_seq",
    "commands": "device_id,command_seq",
    "watering_events": "device_id,event_id",
    "ai_predictions": "prediction_id",
}


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")


def create_backup(db: Database, output_dir: str | Path | None = None,
                  timestamp: datetime | None = None) -> Path:
    """Write a consistent portable JSON snapshot and return its path."""
    output = Path(output_dir) if output_dir is not None else ROOT / "backups"
    output.mkdir(parents=True, exist_ok=True)
    stamp = (timestamp or datetime.now(timezone.utc)).astimezone(timezone.utc)
    name = stamp.strftime("backup_%Y%m%d_%H%M%S.json")
    backup = {
        "format_version": 1,
        "created_at": stamp.isoformat(),
        "tables": {},
    }
    with db.transaction() as conn:
        for table, ordering in TABLES.items():
            backup["tables"][table] = db.all_on(conn, f"SELECT * FROM {table} ORDER BY {ordering}")
    target = output / name
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(backup, ensure_ascii=False, indent=2, default=_json_default) + "\n",
                         encoding="utf-8")
    os.replace(temporary, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "backups"), help="Backup directory (default: ./backups)")
    parser.add_argument("--database-url", help="Overrides DATABASE_URL")
    args = parser.parse_args()
    database = Database(args.database_url)
    try:
        path = create_backup(database, args.output_dir)
        print(path)
    finally:
        database.close()


if __name__ == "__main__":
    main()
