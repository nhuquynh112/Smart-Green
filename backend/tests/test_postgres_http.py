"""HTTP integration tests isolated in a temporary PostgreSQL schema.

Set DATABASE_URL to enable this suite. Tests never use or truncate public tables.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app, enqueue_command
from backend.database import Database


@pytest.fixture(scope="module")
def pg_http():
    url = os.getenv("DATABASE_URL")
    if not url or not url.startswith(("postgres://", "postgresql://")):
        pytest.skip("Set DATABASE_URL to a PostgreSQL server to run HTTP integration tests")
    import psycopg2
    from psycopg2 import sql

    schema = "sg_http_test_" + uuid.uuid4().hex[:20]
    admin = psycopg2.connect(url)
    admin.autocommit = True
    database = None
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        parsed = urlsplit(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        prior_options = params.get("options", "").strip()
        params["options"] = f"{prior_options} -c search_path={schema}".strip()
        isolated_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path,
                                   urlencode(params, quote_via=quote), parsed.fragment))
        database = Database(isolated_url)
        app = create_app(db=database, bundle={})
        with TestClient(app) as client:
            yield database, client
    finally:
        if database is not None:
            database.close()
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
        admin.close()


def new_device(pg_http, label: str):
    database, client = pg_http
    device_id = f"pg-http-{label}-{uuid.uuid4().hex[:8]}"
    api_key = "test-key-" + uuid.uuid4().hex
    database.ensure_device(device_id, api_key, "pg-calibration-v1")
    return database, client, device_id, api_key


def telemetry(device_id: str, *, telemetry_only: bool = False) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 1, "build_stage": "bringup" if telemetry_only else "production",
        "device_id": device_id, "boot_id": "pg-test-boot", "sample_seq": 1,
        "timestamp": now, "uptime_ms": 60000, "data_origin": "real",
        "calibration_id": "pg-calibration-v1", "soil_raw": 1800, "soil_pct": 45.0,
        "soil_valid": True, "air_valid": True, "temperature_c": 25.0,
        "humidity_pct": 60.0, "light_raw": 800, "light_lux": None,
        "tank_ok": True, "pump_on": False, "mode": "MANUAL", "commissioned": True,
        "storage_fault": False, "clock_ready": True, "clock_fault": False,
        "server_available": True, "last_command_seq": 0, "queued_events": 0,
        "telemetry_overwrites": 0, "telemetry_only": telemetry_only,
    }


def admin_auth():
    return (os.getenv("SG_WEB_USER", "admin"), os.getenv("SG_WEB_PASSWORD", "smartgreen2026"))


def test_postgres_http_telemetry_identity_idempotent_and_conflict(pg_http):
    _, client, device_id, key = new_device(pg_http, "telemetry")
    payload = telemetry(device_id)
    url = f"/api/v1/devices/{device_id}/telemetry"
    headers = {"X-API-Key": key}
    assert client.post(url, headers=headers, json=payload).status_code == 200
    reordered = dict(reversed(list(payload.items())))
    assert client.post(url, headers=headers, json=reordered).status_code == 200
    assert client.post(url, headers=headers, json={**payload, "soil_pct": 46.0}).status_code == 409


def test_postgres_http_rejects_bad_device_key(pg_http):
    _, client, device_id, _ = new_device(pg_http, "wrong-key")
    response = client.post(f"/api/v1/devices/{device_id}/telemetry",
                          headers={"X-API-Key": "incorrect"}, json=telemetry(device_id))
    assert response.status_code == 401


def test_postgres_http_expired_command_is_not_delivered(pg_http):
    database, client, device_id, key = new_device(pg_http, "expiry")
    now = int(datetime.now(timezone.utc).timestamp())
    enqueue_command(database, device_id, 1, "STOP", now - 30, now - 1)
    response = client.get(f"/api/v1/devices/{device_id}/commands/next?after_seq=0",
                          headers={"X-API-Key": key})
    assert response.status_code == 204
    assert database.one("SELECT status FROM commands WHERE device_id=? AND command_seq=1",
                        (device_id,))["status"] == "EXPIRED"


def test_postgres_http_ack_is_repeatable_and_persistent(pg_http):
    database, client, device_id, key = new_device(pg_http, "ack")
    now = int(datetime.now(timezone.utc).timestamp())
    enqueue_command(database, device_id, 1, "STOP", now, now + 30)
    payload = {"schema_version": 1, "device_id": device_id, "command_seq": 1, "result": "stopped"}
    url = f"/api/v1/devices/{device_id}/commands/1/ack"
    assert client.post(url, headers={"X-API-Key": key}, json=payload).status_code == 204
    assert client.post(url, headers={"X-API-Key": key}, json=payload).status_code == 204
    row = database.one("SELECT status,ack_result FROM commands WHERE device_id=? AND command_seq=1", (device_id,))
    assert row == {"status": "ACKED", "ack_result": "stopped"}


def test_postgres_http_event_replay_and_manual_watering_null_pump_duration(pg_http):
    database, client, device_id, key = new_device(pg_http, "events")
    event = {"schema_version": 1, "device_id": device_id, "event_id": 12, "command_seq": 0,
             "started_at": int(datetime.now(timezone.utc).timestamp()), "planned_ms": 1000,
             "actual_ms": 1000, "source": "MANUAL", "reason": "Duration"}
    url = f"/api/v1/devices/{device_id}/events"
    assert client.post(url, headers={"X-API-Key": key}, json=event).json() == {"event_id": 12}
    assert client.post(url, headers={"X-API-Key": key}, json=event).json() == {"event_id": 12}
    hand = client.post(f"/api/v1/web/devices/{device_id}/manual-watering", auth=admin_auth(), json={
        "started_at": datetime.now(timezone.utc).isoformat(), "water_ml": 50.0,
        "note": "Tưới tay thử PostgreSQL",
    })
    assert hand.status_code == 201 and hand.json()["actual_ms"] is None
    row = database.one("SELECT planned_ms,actual_ms,source,reason,payload FROM watering_events WHERE device_id=? AND event_id=?",
                       (device_id, hand.json()["event_id"]))
    assert row["planned_ms"] is None and row["actual_ms"] is None
    assert row["source"] == "MANUAL_CARE" and row["reason"] == "ManualHandWatering"


def test_postgres_http_telemetry_only_interlocks_every_command(pg_http):
    _, client, device_id, key = new_device(pg_http, "telemetry-only")
    response = client.post(f"/api/v1/devices/{device_id}/telemetry",
                           headers={"X-API-Key": key}, json=telemetry(device_id, telemetry_only=True))
    assert response.status_code == 200
    blocked = client.post(f"/api/v1/web/devices/{device_id}/commands", auth=admin_auth(),
                          json={"kind": "STOP"})
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Thiết bị đang ở chế độ chỉ thu dữ liệu (telemetry_only=true), không nhận lệnh điều khiển bơm"
