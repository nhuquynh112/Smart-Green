from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
SQLITE_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS devices(device_id TEXT PRIMARY KEY, api_key_hash TEXT NOT NULL,
 display_name TEXT,is_demo INTEGER NOT NULL DEFAULT 0,connected INTEGER NOT NULL DEFAULT 0,last_seen_at TEXT,
 calibration_id TEXT,dry_raw INTEGER,wet_raw INTEGER,last_command_seq INTEGER NOT NULL DEFAULT 0,
 watering_history_complete INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS telemetry(device_id TEXT NOT NULL REFERENCES devices(device_id),boot_id TEXT NOT NULL,
 sample_seq INTEGER NOT NULL,schema_version INTEGER NOT NULL DEFAULT 1,build_stage TEXT,measured_at TEXT,
 received_at TEXT NOT NULL,uptime_ms INTEGER,data_origin TEXT,calibration_id TEXT,soil_raw INTEGER,soil_pct REAL,
 soil_valid INTEGER,temperature_c REAL,humidity_pct REAL,air_valid INTEGER,light_raw INTEGER,light_lux REAL,
 water_ok INTEGER,tank_ok INTEGER,mode TEXT,pump_running INTEGER,commissioned INTEGER,storage_fault INTEGER,
 clock_ready INTEGER,clock_fault INTEGER,server_available INTEGER,last_command_seq INTEGER,queued_events INTEGER,
 telemetry_overwrites INTEGER,payload TEXT NOT NULL,PRIMARY KEY(device_id,boot_id,sample_seq));
CREATE INDEX IF NOT EXISTS telemetry_device_measured_idx ON telemetry(device_id,measured_at DESC);
CREATE INDEX IF NOT EXISTS telemetry_device_received_idx ON telemetry(device_id,received_at DESC);
CREATE TABLE IF NOT EXISTS commands(device_id TEXT NOT NULL REFERENCES devices(device_id),command_seq INTEGER NOT NULL,
 schema_version INTEGER NOT NULL DEFAULT 1,kind TEXT NOT NULL,source TEXT,duration_ms INTEGER,mode TEXT,
 issued_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'PENDING',ack_result TEXT,
 acked_at TEXT,created_at TEXT NOT NULL,PRIMARY KEY(device_id,command_seq),
 CHECK(expires_at>issued_at AND expires_at-issued_at<=60),
 CHECK((kind='WATER' AND source IS NOT NULL AND duration_ms IS NOT NULL AND mode IS NULL) OR
 (kind='SET_MODE' AND mode IS NOT NULL AND source IS NULL AND duration_ms IS NULL) OR
 (kind='STOP' AND source IS NULL AND duration_ms IS NULL AND mode IS NULL)));
CREATE INDEX IF NOT EXISTS commands_pending_idx ON commands(device_id,status,command_seq);
CREATE TABLE IF NOT EXISTS watering_events(device_id TEXT NOT NULL REFERENCES devices(device_id),event_id INTEGER NOT NULL,
 schema_version INTEGER NOT NULL DEFAULT 1,command_seq INTEGER NOT NULL DEFAULT 0,started_at INTEGER NOT NULL,
 planned_ms INTEGER,actual_ms INTEGER,ended_at INTEGER,source TEXT NOT NULL,reason TEXT NOT NULL,received_at TEXT NOT NULL,
 payload TEXT NOT NULL,PRIMARY KEY(device_id,event_id),
 CHECK((reason='ManualHandWatering' AND source IN ('MANUAL_CARE','MANUAL') AND planned_ms IS NULL AND actual_ms IS NULL)
    OR (reason IN ('Reboot','Manual') AND actual_ms IS NULL)
    OR (reason NOT IN ('Reboot','Manual','ManualHandWatering') AND planned_ms IS NOT NULL AND actual_ms IS NOT NULL)),
 CHECK(reason<>'Manual' OR ended_at IS NOT NULL));
CREATE INDEX IF NOT EXISTS watering_events_device_started_idx ON watering_events(device_id,started_at DESC);
CREATE TABLE IF NOT EXISTS ai_predictions(prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,device_id TEXT NOT NULL
 REFERENCES devices(device_id),as_of TEXT,available_at TEXT,horizon_minutes INTEGER,predicted_soil_pct REAL,
 model_name TEXT,data_origin TEXT,can_trigger_pump INTEGER NOT NULL DEFAULT 0 CHECK(can_trigger_pump=0),
 status TEXT NOT NULL,raw_output TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ai_predictions_device_created_idx ON ai_predictions(device_id,created_at DESC);
"""


def utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class Database:
    """Small DB-API adapter. SQLite is used by default; PostgreSQL uses psycopg2."""

    def __init__(self, url: str | None = None):
        self._lock = threading.RLock()
        self.url = url or os.getenv("DATABASE_URL", "sqlite:///./smart_green.sqlite3")
        self.sqlite = self.url.startswith("sqlite:")
        self._memory = self.url in {"sqlite://", "sqlite:///:memory:"}
        self._conn: sqlite3.Connection | None = None
        if self.sqlite:
            if self._memory:
                self._conn = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
            else:
                path = self.url.removeprefix("sqlite:///").replace("/", os.sep)
                self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(SQLITE_SCHEMA)
            self._migrate_sqlite()
        else:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
            except ImportError as exc:
                raise RuntimeError("PostgreSQL DATABASE_URL requires psycopg2-binary") from exc
            self._psycopg2 = psycopg2
            self._dict_cursor = RealDictCursor
            with self.connection() as conn:
                schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
                with conn.cursor() as cur:
                    cur.execute(schema)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        if self.sqlite:
            assert self._conn is not None
            with self._lock:
                yield self._conn
        else:
            conn = self._psycopg2.connect(self.url)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self.connection() as conn:
            if self.sqlite:
                conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                if self.sqlite:
                    conn.commit()
            except Exception:
                if self.sqlite:
                    conn.rollback()
                raise

    def execute_on(self, conn: Any, sql: str, params: tuple = ()) -> int:
        if self.sqlite:
            return conn.execute(sql, params).rowcount
        with conn.cursor() as cur:
            cur.execute(sql.replace("?", "%s"), params)
            return cur.rowcount

    def executemany_on(self, conn: Any, sql: str, rows: list[tuple]) -> int:
        if self.sqlite:
            return conn.executemany(sql, rows).rowcount
        with conn.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)
            return cur.rowcount

    def one_on(self, conn: Any, sql: str, params: tuple = ()) -> dict | None:
        if self.sqlite:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None
        with conn.cursor(cursor_factory=self._dict_cursor) as cur:
            cur.execute(sql.replace("?", "%s"), params)
            row = cur.fetchone()
            return dict(row) if row else None

    def all_on(self, conn: Any, sql: str, params: tuple = ()) -> list[dict]:
        if self.sqlite:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]
        with conn.cursor(cursor_factory=self._dict_cursor) as cur:
            cur.execute(sql.replace("?", "%s"), params)
            return [dict(row) for row in cur.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.connection() as conn:
            if self.sqlite:
                cur = conn.execute(sql, params)
                return cur.rowcount
            with conn.cursor() as cur:
                cur.execute(sql.replace("?", "%s"), params)
                return cur.rowcount

    def one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.connection() as conn:
            if self.sqlite:
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None
            with conn.cursor(cursor_factory=self._dict_cursor) as cur:
                cur.execute(sql.replace("?", "%s"), params)
                row = cur.fetchone()
                return dict(row) if row else None

    def all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.connection() as conn:
            if self.sqlite:
                return [dict(row) for row in conn.execute(sql, params).fetchall()]
            with conn.cursor(cursor_factory=self._dict_cursor) as cur:
                cur.execute(sql.replace("?", "%s"), params)
                return [dict(row) for row in cur.fetchall()]

    def ensure_device(self, device_id: str, key: str, calibration_id: str | None = None) -> None:
        key_hash = hash_key(key)
        now = utc_iso()
        if self.sqlite:
            self.execute("INSERT INTO devices(device_id,api_key_hash,calibration_id,created_at) VALUES(?,?,?,?) "
                         "ON CONFLICT(device_id) DO UPDATE SET api_key_hash=excluded.api_key_hash, "
                         "calibration_id=COALESCE(excluded.calibration_id,devices.calibration_id)",
                         (device_id, key_hash, calibration_id, now))
        else:
            self.execute("INSERT INTO devices(device_id,api_key_hash,calibration_id) VALUES(?,?,?) "
                         "ON CONFLICT(device_id) DO UPDATE SET api_key_hash=EXCLUDED.api_key_hash, "
                         "calibration_id=COALESCE(EXCLUDED.calibration_id,devices.calibration_id)",
                         (device_id, key_hash, calibration_id))

    def _migrate_sqlite(self) -> None:
        """Add columns introduced after the first local SQLite prototype."""
        assert self._conn is not None
        migrations = {
            "devices": {"display_name": "TEXT", "is_demo": "INTEGER NOT NULL DEFAULT 0",
                        "dry_raw": "INTEGER", "wet_raw": "INTEGER",
                        "last_command_seq": "INTEGER NOT NULL DEFAULT 0",
                        "watering_history_complete": "INTEGER NOT NULL DEFAULT 0"},
            "watering_events": {"ended_at": "INTEGER"},
            "commands": {"request_id": "TEXT", "request_fingerprint": "TEXT"},
        }
        for table, columns in migrations.items():
            existing = {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}
            for name, declaration in columns.items():
                if name not in existing:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
        self._conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS commands_request_id_idx ON commands(device_id,request_id) WHERE request_id IS NOT NULL")
        table_sql = self._conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='watering_events'").fetchone()["sql"] or ""
        if "'Scheduled'" not in table_sql or "'ManualCheck'" not in table_sql or "'ManualHandWatering'" not in table_sql:
            self._conn.executescript("""
            DROP INDEX IF EXISTS watering_events_device_started_idx;
            CREATE TABLE watering_events_new(
              device_id TEXT NOT NULL REFERENCES devices(device_id),event_id INTEGER NOT NULL,
              schema_version INTEGER NOT NULL DEFAULT 1,command_seq INTEGER NOT NULL DEFAULT 0,
              started_at INTEGER NOT NULL,planned_ms INTEGER,actual_ms INTEGER,ended_at INTEGER,
              source TEXT NOT NULL,reason TEXT NOT NULL,received_at TEXT NOT NULL,payload TEXT NOT NULL,
              PRIMARY KEY(device_id,event_id),
              CHECK((reason='ManualHandWatering' AND source IN ('MANUAL_CARE','MANUAL') AND planned_ms IS NULL AND actual_ms IS NULL)
                OR (reason IN ('Reboot','Manual') AND actual_ms IS NULL)
                OR (reason NOT IN ('Reboot','Manual','ManualHandWatering') AND planned_ms IS NOT NULL AND actual_ms IS NOT NULL)),
              CHECK(reason<>'Manual' OR ended_at IS NOT NULL));
            INSERT INTO watering_events_new(device_id,event_id,schema_version,command_seq,started_at,planned_ms,
              actual_ms,ended_at,source,reason,received_at,payload)
              SELECT device_id,event_id,schema_version,command_seq,started_at,planned_ms,actual_ms,ended_at,
              source,reason,received_at,payload FROM watering_events;
            DROP TABLE watering_events;
            ALTER TABLE watering_events_new RENAME TO watering_events;
            CREATE INDEX watering_events_device_started_idx ON watering_events(device_id,started_at DESC);
            """)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
