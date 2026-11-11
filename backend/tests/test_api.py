from __future__ import annotations

import time
import re
from datetime import datetime, timedelta, timezone

import pytest

from backend.app import _admin_auth, create_app, enqueue_command
from backend.database import Database, canonical_json, utc_iso


KEY = "local-test-key"
DEVICE = "garden-test"


@pytest.fixture
def db():
    database = Database("sqlite:///:memory:")
    database.ensure_device(DEVICE, KEY, "cal-v1")
    yield database
    database.close()


@pytest.fixture
def client(db):
    return SyncASGIClient(create_app(db=db, bundle=None))


class SyncASGIClient:
    """Call the registered synchronous FastAPI handlers without binding sockets."""
    def __init__(self, app):
        self.routes = []
        for route in app.routes:
            if hasattr(route, "endpoint"):
                pattern = re.sub(r"\{[^}]+\}", r"[^/]+", route.path)
                self.routes.append((re.compile(f"^{pattern}$"), route.endpoint, route.path))

    def _call(self, path, **kwargs):
        endpoint = next(endpoint for pattern, endpoint, _ in self.routes if pattern.match(path))
        try:
            return endpoint(**kwargs)
        except Exception as exc:
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                return DirectResponse(exc)
            raise

    def get(self, url, headers=None, admin=False):
        path, _, query = url.partition("?")
        params = dict(item.split("=", 1) for item in query.split("&") if item) if query else {}
        if "after_seq" in params:
            params["after_seq"] = int(params["after_seq"])
        if path == "/api/v1/web/auth/check" and admin:
            from fastapi.security import HTTPBasicCredentials
            credentials = HTTPBasicCredentials(username="admin", password="smartgreen2026")
            result = self._call(path, username=_admin_auth(credentials))
            return result if isinstance(result, DirectResponse) else DirectResponse(result)
        parts = path.split("/")
        values = {**params}
        if path != "/api/v1/web/devices":
            values["device_id"] = parts[5] if "/web/" in path else parts[4]
        if "/web/" not in path:
            values["x_api_key"] = (headers or {}).get("X-API-Key")
        if admin:
            from fastapi.security import HTTPBasicCredentials
            values["_"] = HTTPBasicCredentials(username="admin", password="smartgreen2026")
        result = self._call(path, **values)
        return result if isinstance(result, DirectResponse) else DirectResponse(result)

    def post(self, url, headers=None, json=None, admin=False):
        path = url.split("?", 1)[0]
        parts = path.split("/")
        values = {"device_id": parts[5] if "/web/" in path else parts[4]}
        if "/web/" not in path:
            values["x_api_key"] = (headers or {}).get("X-API-Key")
        if parts[-1] == "telemetry" or parts[-1] == "events":
            values["body"] = json
        elif len(parts) >= 3 and parts[-1] == "ack":
            values["seq"] = int(parts[-2])
            values["body"] = json
        elif "/web/" in path:
            values["body"] = json
        if admin:
            from fastapi.security import HTTPBasicCredentials
            values["_"] = HTTPBasicCredentials(username="admin", password="smartgreen2026")
        result = self._call(path, **values)
        return result if isinstance(result, DirectResponse) else DirectResponse(result)


class DirectResponse:
    """Normalize handler return values to the small response surface used by tests."""
    def __init__(self, value):
        from fastapi.responses import Response
        from fastapi.encoders import jsonable_encoder
        from fastapi import HTTPException
        self.status_code = value.status_code if isinstance(value, (Response, HTTPException)) else 200
        self._body = (value.body if isinstance(value, Response) else
                      {"detail": jsonable_encoder(value.detail)} if isinstance(value, HTTPException) else
                      jsonable_encoder(value))

    def json(self):
        if isinstance(self._body, bytes):
            return __import__("json").loads(self._body)
        return self._body


def headers(key=KEY):
    return {"X-API-Key": key, "Content-Type": "application/json"}


def telemetry(seq=1):
    return {
        "schema_version": 1, "build_stage": "contract_test", "device_id": DEVICE,
        "boot_id": "boot-1", "sample_seq": seq, "timestamp": "2026-11-08T10:00:00Z",
        "uptime_ms": seq * 60000, "data_origin": "real", "calibration_id": "cal-v1",
        "soil_raw": 2100, "soil_pct": 37.5, "soil_valid": True, "air_valid": True,
        "temperature_c": 27.0, "humidity_pct": 60.0, "light_raw": 900, "light_lux": None,
        "tank_ok": True, "pump_on": False, "mode": "AUTO", "commissioned": False,
        "storage_fault": False, "clock_ready": True, "clock_fault": False,
        "server_available": True, "last_command_seq": 0, "queued_events": 0,
        "telemetry_overwrites": 0,
    }


def test_auth_rejects_wrong_device_key(client):
    response = client.post(f"/api/v1/devices/{DEVICE}/telemetry", headers=headers("wrong"), json=telemetry())
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_telemetry_idempotency_and_conflict(client, db):
    url = f"/api/v1/devices/{DEVICE}/telemetry"
    item = telemetry()
    assert client.post(url, headers=headers(), json=item).json() == {"stored": True}
    reordered = dict(reversed(list(item.items())))
    assert client.post(url, headers=headers(), json=reordered).status_code == 200
    changed = dict(item, soil_pct=38.0)
    assert client.post(url, headers=headers(), json=changed).status_code == 409
    assert db.one("SELECT count(*) AS n FROM telemetry")["n"] == 1


def test_command_queue_after_seq_ttl_and_expiry(client, db):
    now = int(time.time())
    with pytest.raises(ValueError, match="TTL"):
        enqueue_command(db, DEVICE, 1, "WATER", now, now + 61, source="MANUAL", duration_ms=1000)
    enqueue_command(db, DEVICE, 1, "WATER", now, now + 50, source="MANUAL", duration_ms=1000)
    enqueue_command(db, DEVICE, 2, "SET_MODE", now, now + 60, mode="AUTO")
    response = client.get(f"/api/v1/devices/{DEVICE}/commands/next?after_seq=0", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"schema_version": 1, "device_id": DEVICE, "command_seq": 1,
                               "kind": "WATER", "issued_at": now, "expires_at": now + 50,
                               "source": "MANUAL", "duration_ms": 1000}
    response = client.get(f"/api/v1/devices/{DEVICE}/commands/next?after_seq=1", headers=headers())
    assert response.status_code == 200 and response.json()["command_seq"] == 2
    assert client.get(f"/api/v1/devices/{DEVICE}/commands/next?after_seq=2", headers=headers()).status_code == 204
    assert db.one("SELECT max(expires_at-issued_at) AS ttl FROM commands")["ttl"] <= 60


def test_dashboard_marks_stale_pending_commands_expired(client, db):
    now = int(time.time())
    enqueue_command(db, DEVICE, 12, "STOP", now - 61, now - 1)
    response = client.get(f"/api/v1/web/devices/{DEVICE}/dashboard")
    assert response.status_code == 200
    command = next(row for row in response.json()["commands"] if row["command_seq"] == 12)
    assert command["status"] == "EXPIRED"
    assert db.one("SELECT status FROM commands WHERE device_id=? AND command_seq=?", (DEVICE, 12))["status"] == "EXPIRED"


def test_ack_is_idempotent(client, db):
    now = int(time.time())
    enqueue_command(db, DEVICE, 7, "STOP", now, now + 30)
    url = f"/api/v1/devices/{DEVICE}/commands/7/ack"
    ack = {"schema_version": 1, "device_id": DEVICE, "command_seq": 7, "result": "stopped"}
    assert client.post(url, headers=headers(), json=ack).status_code == 204
    assert client.post(url, headers=headers(), json=ack).status_code == 204
    row = db.one("SELECT status,ack_result FROM commands WHERE device_id=? AND command_seq=?", (DEVICE, 7))
    assert row == {"status": "ACKED", "ack_result": "stopped"}


def test_ai_water_command_requires_opt_in_and_positive_advice(db, monkeypatch):
    now = int(time.time())
    monkeypatch.delenv("SG_AI_COMMANDS_ENABLED", raising=False)
    with pytest.raises(ValueError, match="disabled"):
        enqueue_command(db, DEVICE, 1, "WATER", now, now + 30, source="AI", duration_ms=1000,
                        ai_advice={"can_trigger_pump": True})
    monkeypatch.setenv("SG_AI_COMMANDS_ENABLED", "true")
    with pytest.raises(ValueError, match="does not authorize"):
        enqueue_command(db, DEVICE, 1, "WATER", now, now + 30, source="AI", duration_ms=1000,
                        ai_advice={"can_trigger_pump": False})
    assert db.one("SELECT count(*) AS n FROM commands")["n"] == 0


def test_reboot_event_null_duration_and_idempotency(client, db):
    event = {"schema_version": 1, "device_id": DEVICE, "event_id": 4, "command_seq": 0,
             "started_at": int(time.time()), "planned_ms": 1000, "actual_ms": None,
             "source": "RULE", "reason": "Reboot"}
    url = f"/api/v1/devices/{DEVICE}/events"
    assert client.post(url, headers=headers(), json=event).json() == {"event_id": 4}
    assert client.post(url, headers=headers(), json=event).json() == {"event_id": 4}
    changed = dict(event, planned_ms=2000)
    assert client.post(url, headers=headers(), json=changed).status_code == 409
    row = db.one("SELECT actual_ms,reason FROM watering_events WHERE device_id=? AND event_id=?", (DEVICE, 4))
    assert row == {"actual_ms": None, "reason": "Reboot"}


def test_ai_inference_service_builds_v2_and_never_authorizes_pump(db):
    from backend.ai_service import AI_COLUMNS, make_recent_minute_dataframe, run_prediction

    start = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=16)
    rows = []
    for minute in range(16):
        at = start + timedelta(minutes=minute)
        rows.append({"measured_at": at, "data_origin": "real", "calibration_id": "cal-v1",
                     "soil_valid": True, "air_valid": True, "soil_pct": 40-minute*.1,
                     "temperature_c": 26.0, "humidity_pct": 60.0})
    event = {"started_at": int((start - timedelta(minutes=30)).timestamp()),
             "actual_ms": 1000, "reason": "Duration"}
    recent = make_recent_minute_dataframe(DEVICE, rows, [event])
    assert list(recent.columns) == AI_COLUMNS
    assert len(recent) == 16 and recent.water_event_count.nunique() == 1

    def fake_predict(bundle, frame, now):
        assert len(frame) == 16
        return {"predicted_soil_pct": 36.0, "horizon_minutes": 30, "as_of": frame.timestamp.iloc[-1].isoformat(),
                "available_at": now, "model": "test", "can_trigger_pump": True}

    result = run_prediction({}, recent, predictor=fake_predict)
    assert result["status"] == "available" and result["can_trigger_pump"] is False
    unavailable = run_prediction({}, recent, predictor=lambda *_: (_ for _ in ()).throw(ValueError("stale data")))
    assert unavailable == {"status": "unavailable", "reason": "stale data", "can_trigger_pump": False}


def test_ai_route_stores_unavailable_without_confirmed_watering_history(db):
    client = SyncASGIClient(create_app(db=db, bundle={"metadata": {"quality": {"data_origin": "synthetic"}}}))
    response = client.get(f"/api/v1/devices/{DEVICE}/ai/prediction", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    row = db.one("SELECT status,can_trigger_pump FROM ai_predictions ORDER BY prediction_id DESC LIMIT 1")
    assert row == {"status": "unavailable", "can_trigger_pump": 0}


def test_web_basic_auth_and_admin_device_dashboard(db, monkeypatch):
    from fastapi import HTTPException
    from fastapi.security import HTTPBasicCredentials

    monkeypatch.setenv("SG_WEB_USER", "admin")
    monkeypatch.setenv("SG_WEB_PASSWORD", "smartgreen2026")
    with pytest.raises(HTTPException) as error:
        _admin_auth(HTTPBasicCredentials(username="admin", password="wrong"))
    assert error.value.status_code == 401
    assert "WWW-Authenticate" not in (error.value.headers or {})

    from backend.seed_demo import seed_demo
    seeded = seed_demo(db)
    client = SyncASGIClient(create_app(db=db, bundle=__import__("backend.app", fromlist=["_load_bundle"])._load_bundle(None)))
    devices = client.get("/api/v1/web/devices").json()
    assert {seeded["bench_device_id"], seeded["demo_device_id"]}.issubset({row["device_id"] for row in devices})
    dashboard = client.get(f"/api/v1/web/devices/{seeded['demo_device_id']}/dashboard").json()
    assert dashboard["device"]["display_name"] == "Mô phỏng AI v2 (SIM-ONLY · 14.400 mẫu)"
    assert dashboard["model_evaluation"]["selected_model"] == "linear_regression"
    assert set(dashboard["model_evaluation"]["test_mae"]) == {
        "persistence", "linear_extrapolation", "linear_regression", "random_forest"}
    assert dashboard["latest_ai"]["status"] == "available"
    assert dashboard["latest_ai"]["can_trigger_pump"] is False
    assert client.get("/api/v1/web/auth/check", admin=True).json()["authenticated"] is True
    # Inspect the generated API contract: reads are public, mutations require Basic Auth.
    app = create_app(db=db, bundle={"metadata": {"quality": {}}})
    schema = app.openapi()
    assert "security" not in schema["paths"]["/api/v1/web/devices"]["get"]
    assert "security" not in schema["paths"]["/api/v1/web/devices/{device_id}/dashboard"]["get"]
    assert schema["paths"]["/api/v1/web/devices/{device_id}/commands"]["post"]["security"]
    assert schema["paths"]["/api/v1/web/devices/{device_id}/predict"]["post"]["security"]


def test_web_command_water_interlocks_and_sequence(db, client, monkeypatch):
    from fastapi import HTTPException

    url = f"/api/v1/devices/{DEVICE}/telemetry"
    low_tank = telemetry()
    low_tank.update(tank_ok=False)
    client.post(url, headers=headers(), json=low_tank)
    web_url = f"/api/v1/web/devices/{DEVICE}/commands"
    request = {"kind": "WATER", "duration_ms": 500, "ttl_sec": 30}
    response = client.post(web_url, admin=True, json=request)
    assert response.status_code == 400 and "Phao" in response.json()["detail"]

    bad_soil = telemetry(2)
    bad_soil.update(soil_valid=False, soil_pct=None, tank_ok=True)
    client.post(url, headers=headers(), json=bad_soil)
    response = client.post(web_url, admin=True, json=request)
    assert response.status_code == 400 and "Cảm biến" in response.json()["detail"]

    good = telemetry(3)
    good.update(mode="MANUAL", commissioned=True, timestamp=utc_iso())
    client.post(url, headers=headers(), json=good)
    response = client.post(web_url, admin=True, json={"kind": "WATER", "duration_ms": 1001, "ttl_sec": 30})
    assert response.status_code == 400 and "giới hạn an toàn" in response.json()["detail"]
    response = client.post(web_url, admin=True, json=request)
    assert response.status_code == 201 and response.json()["command_seq"] == 1
    assert response.json()["source"] == "MANUAL"
    duplicate = client.post(web_url, admin=True, json=request)
    assert duplicate.status_code == 409
    client.post(f"/api/v1/devices/{DEVICE}/commands/1/ack", headers=headers(), json={"schema_version":1,"device_id":DEVICE,"command_seq":1,"result":"started"})
    mode = client.post(web_url, admin=True, json={"kind": "SET_MODE", "mode": "AUTO"})
    stop = client.post(web_url, admin=True, json={"kind": "STOP"})
    assert mode.json()["command_seq"] == 2 and stop.json()["command_seq"] == 3
    assert db.one("SELECT last_command_seq FROM devices WHERE device_id=?", (DEVICE,))["last_command_seq"] == 3


def test_web_predict_runs_seeded_demo_and_saves_prediction(db):
    from backend.seed_demo import seed_demo

    seeded = seed_demo(db)
    client = SyncASGIClient(create_app(db=db, bundle=__import__("backend.app", fromlist=["_load_bundle"])._load_bundle(None)))
    response = client.post(f"/api/v1/web/devices/{seeded['demo_device_id']}/predict", admin=True,
                           json={"watering_history_complete": True})
    result = response.json()
    assert result["status"] == "available"
    assert result["model"] == "linear_regression"
    assert result["horizon_minutes"] == 30
    assert result["predicted_soil_pct"] is not None
    assert result["can_trigger_pump"] is False
    assert db.one("SELECT count(*) AS n FROM ai_predictions WHERE device_id=? AND status='available'",
                  (seeded["demo_device_id"],))["n"] == 2


def test_demo_prediction_rebases_seed_history_even_after_live_simulator_boot(db):
    from backend.seed_demo import seed_demo

    seeded = seed_demo(db)
    client = SyncASGIClient(create_app(db=db, bundle=__import__("backend.app", fromlist=["_load_bundle"])._load_bundle(None)))
    live = telemetry(1)
    live.update(device_id=seeded["demo_device_id"], boot_id="simulator-fresh-boot",
                calibration_id="SIM-v1", data_origin="synthetic", soil_pct=42.0,
                timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                tank_ok=True)
    response = client.post(f"/api/v1/devices/{seeded['demo_device_id']}/telemetry",
                           headers={"X-API-Key": "local-demo-sim-only-key"}, json=live)
    assert response.status_code == 200
    predicted = client.post(f"/api/v1/web/devices/{seeded['demo_device_id']}/predict", admin=True,
                            json={"watering_history_complete": True}).json()
    assert predicted["status"] == "available"
    assert predicted["predicted_soil_pct"] is not None
    assert predicted["can_trigger_pump"] is False


def test_seed_demo_loads_bench_and_full_v2_prediction(db):
    from backend.seed_demo import seed_demo

    seeded = seed_demo(db)
    assert seeded["bench_samples"] == 60
    assert seeded["demo_samples"] == 14400
    assert seeded["demo_events"] == 10
    assert seeded["bench_events"] == 2
    assert seeded["prediction"]["status"] == "available"
    assert seeded["prediction"]["can_trigger_pump"] is False
    last_telemetry = db.one("SELECT received_at FROM telemetry WHERE device_id=? AND boot_id='seed-synthetic-v2' ORDER BY measured_at DESC LIMIT 1",
                            (seeded["demo_device_id"],))
    received_at = datetime.fromisoformat(last_telemetry["received_at"].replace("Z", "+00:00"))
    ready_at = datetime.fromisoformat(seeded["prediction"]["available_at"].replace("Z", "+00:00"))
    assert received_at == ready_at
    assert db.one("SELECT count(*) AS n FROM watering_events WHERE device_id=?", (seeded["demo_device_id"],))["n"] == 10
    last_sim = db.all("SELECT measured_at FROM telemetry WHERE device_id=? AND boot_id='seed-synthetic-v2' ORDER BY measured_at DESC LIMIT 20",
                      (seeded["demo_device_id"],))
    assert len(last_sim) == 20
    stamps = [datetime.fromisoformat(row["measured_at"].replace("Z", "+00:00")) for row in reversed(last_sim)]
    assert all((b-a).total_seconds() == 60 for a, b in zip(stamps, stamps[1:]))
    latest = stamps[-1]
    sim_events = db.all("SELECT ended_at,planned_ms,actual_ms,reason FROM watering_events WHERE device_id=?",
                        (seeded["demo_device_id"],))
    assert len(sim_events) == 10
    assert all(latest.timestamp() - event["ended_at"] > 20 * 60 for event in sim_events)
    assert all(event["planned_ms"] == 1000 and event["actual_ms"] == 1000 and event["reason"] == "Scheduled"
               for event in sim_events)

    last_bench = db.all("SELECT measured_at FROM telemetry WHERE device_id=? ORDER BY measured_at DESC LIMIT 20",
                        (seeded["bench_device_id"],))
    bench_stamps = [datetime.fromisoformat(row["measured_at"].replace("Z", "+00:00")) for row in reversed(last_bench)]
    bench_events = db.all("SELECT ended_at,planned_ms,actual_ms,reason FROM watering_events WHERE device_id=?", (seeded["bench_device_id"],))
    assert len(bench_events) == 2 and all(bench_stamps[-1].timestamp() - e["ended_at"] > 20 * 60 for e in bench_events)
    assert all(e["planned_ms"] == 1000 and e["actual_ms"] == 1000 and e["reason"] == "ManualCheck" for e in bench_events)


def test_device_simulator_polls_acknowledges_and_emits_event():
    from backend.simulate_device import DeviceSimulator

    now = int(time.time())
    command = {"schema_version": 1, "device_id": DEVICE, "command_seq": 9, "kind": "WATER",
               "source": "MANUAL", "duration_ms": 500, "issued_at": now - 1, "expires_at": now + 30}

    class FakeClient:
        device_id = DEVICE
        root = f"/api/v1/devices/{DEVICE}"

        def __init__(self):
            self.requests = []
            self.sent_event = None

        def request(self, method, path, payload=None):
            self.requests.append((method, path, payload))
            if method == "GET":
                return 200, command
            if path.endswith("/events"):
                self.sent_event = payload
                return 200, {"event_id": payload["event_id"]}
            if path.endswith("/commands/next?after_seq=0"):
                return 204, None
            return 204, None

    api = FakeClient()
    DeviceSimulator(api).step()
    assert [path for method, path, _ in api.requests] == [
        f"{api.root}/telemetry", f"{api.root}/commands/next?after_seq=0",
        f"{api.root}/commands/9/ack", f"{api.root}/events"]
    ack = next(body for method, path, body in api.requests if path.endswith("/ack"))
    assert ack["result"] == "started" and ack["command_seq"] == 9
    assert api.sent_event["command_seq"] == 9 and api.sent_event["actual_ms"] == 500


def test_database_connection_check_lists_production_tables(db):
    from backend.check_db import check_database

    result = check_database(db)
    assert result["status"] == "ok" and result["database"] == "sqlite"
    assert set(result["tables"]) == {"devices", "telemetry", "commands", "watering_events", "ai_predictions"}


def test_dashboard_watering_stats_separates_sources_and_estimates_water(client, db, monkeypatch):
    now = int(time.time())
    monkeypatch.setenv("SG_PUMP_FLOW_ML_PER_SEC", "12")
    fixtures = [
        (1, now - 300, 1000, "MANUAL", "Duration"),
        (2, now - 200, 2000, "RULE", "Duration"),
        (3, now - 90000, 500, "AI", "Duration"),
        (4, now - 100, None, "RULE", "Reboot"),
    ]
    for event_id, started_at, actual_ms, source, reason in fixtures:
        body = {"schema_version": 1, "device_id": DEVICE, "event_id": event_id,
                "command_seq": event_id, "started_at": started_at, "planned_ms": 2000,
                "actual_ms": actual_ms, "source": source, "reason": reason}
        response = client.post(f"/api/v1/devices/{DEVICE}/events", headers=headers(), json=body)
        assert response.status_code == 200
    stats = client.get(f"/api/v1/web/devices/{DEVICE}/dashboard").json()["watering_stats"]
    assert stats["total_events"] == 3
    assert stats["events_last_24h"] == 2 and stats["max_daily_events"] == 6
    assert stats["manual_count"] == 1 and stats["auto_count"] == 2
    assert stats["total_actual_ms"] == 3500 and stats["estimated_water_ml"] == 42
    assert stats["flow_is_configured"] is True


def test_telemetry_csv_export_returns_header_and_device_rows(client):
    payload = telemetry()
    assert client.post(f"/api/v1/devices/{DEVICE}/telemetry", headers=headers(), json=payload).status_code == 200
    path = f"/api/v1/web/devices/{DEVICE}/export-csv"
    response = client._call(path, device_id=DEVICE)
    assert response.status_code == 200
    text = response.body.decode("utf-8-sig")
    assert "device_id,boot_id,sample_seq" in text
    assert f"{DEVICE},boot-1,1" in text and "soil_pct" in text
    assert "text/csv" in response.headers["content-type"]


def test_json_database_backup_contains_all_five_tables(db, tmp_path):
    import json
    from backend.backup_db import TABLES, create_backup

    path = create_backup(db, tmp_path, datetime(2026, 11, 9, 12, 34, 56, tzinfo=timezone.utc))
    assert path.name == "backup_20261109_123456.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload["tables"]) == set(TABLES)
    assert payload["tables"]["devices"][0]["device_id"] == DEVICE
    assert all(isinstance(payload["tables"][table], list) for table in TABLES)

@pytest.mark.parametrize('changes', [
    {'quota_limit_starts':4,'quota_starts':4},
    {'quota_limit_ms':4000,'quota_reserved_ms':3800},
    {'clock_ready':False}, {'storage_fault':True}, {'commissioned':False},
    {'mode':'OFF'}, {'pump_on':True}, {'cooldown_remaining_ms':600000},
    {'timestamp':'2020-01-01T00:00:00Z'},
])
def test_water_rejects_unready_device(client, changes):
    row=telemetry();row.update(mode='MANUAL',commissioned=True,timestamp=utc_iso());row.update(changes)
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==200
    result=client.post(f'/api/v1/web/devices/{DEVICE}/commands',admin=True,json={'kind':'WATER','duration_ms':500})
    assert result.status_code==409


def test_stop_supersedes_waiting_mode(client, db):
    url=f'/api/v1/web/devices/{DEVICE}/commands'
    assert client.post(url,admin=True,json={'kind':'SET_MODE','mode':'AUTO'}).status_code==201
    assert client.post(url,admin=True,json={'kind':'STOP'}).status_code==201
    command=client.get(f'/api/v1/devices/{DEVICE}/commands/next?after_seq=0',headers=headers()).json()
    assert command['kind']=='STOP'
    assert db.one('SELECT status FROM commands WHERE device_id=? AND command_seq=1',(DEVICE,))['status']=='EXPIRED'


def test_rejects_invalid_control_limits(client):
    row=telemetry();row['quota_limit_ms']='unlimited'
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==422


def test_http_route_auth_and_quota_end_to_end(db):
    import asyncio
    import json

    async def scenario():
        app=create_app(db=db,bundle=None)
        async def post(path, body, request_headers=None):
            encoded=json.dumps(body).encode();messages=[];delivered=False
            async def receive():
                nonlocal delivered
                if not delivered:
                    delivered=True
                    return {"type":"http.request","body":encoded,"more_body":False}
                await asyncio.Event().wait()
            async def send(message): messages.append(message)
            scope={"type":"http","asgi":{"version":"3.0"},"http_version":"1.1","method":"POST",
                   "scheme":"http","path":path,"raw_path":path.encode(),"query_string":b"",
                   "root_path":"","server":("test",80),"client":("test",1),
                   "headers":[(b"content-type",b"application/json")]+[(k.lower().encode(),v.encode()) for k,v in (request_headers or {}).items()]}
            await app(scope,receive,send)
            status=next(m["status"] for m in messages if m["type"]=="http.response.start")
            content=b"".join(m.get("body",b"") for m in messages if m["type"]=="http.response.body")
            return status,json.loads(content) if content else None
        path=f'/api/v1/web/devices/{DEVICE}/commands'
        status,_=await post(path,{'kind':'WATER','duration_ms':500})
        assert status==401
        row=telemetry();row.update(mode='MANUAL',commissioned=True,timestamp=utc_iso(),quota_limit_starts=4,quota_starts=4)
        status,_=await post(f'/api/v1/devices/{DEVICE}/telemetry',row,headers())
        assert status==200
        app.dependency_overrides[_admin_auth]=lambda:'test-admin'
        status,body=await post(path,{'kind':'WATER','duration_ms':500})
        assert status==409 and 'hạn mức' in body['detail']
        status,_=await post(path,{'kind':'STOP'})
        assert status==201
    asyncio.run(scenario())


def test_postgres_backup_selects_snapshot_before_reading_tables(tmp_path):
    from contextlib import contextmanager
    from backend.backup_db import TABLES, create_backup

    class SnapshotDatabase:
        sqlite = False
        calls = []

        @contextmanager
        def transaction(self):
            yield self

        def execute_on(self, conn, sql):
            self.calls.append(sql)

        def all_on(self, conn, sql):
            assert self.calls[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            self.calls.append(sql)
            return []

    db = SnapshotDatabase()
    create_backup(db, tmp_path)
    assert len(db.calls) == 1 + len(TABLES)


@pytest.mark.parametrize("flow", [None, "invalid", "nan", "0", "-1"])
def test_dashboard_does_not_invent_uncalibrated_volume(client, monkeypatch, flow):
    if flow is None:
        monkeypatch.delenv("SG_PUMP_FLOW_ML_PER_SEC", raising=False)
    else:
        monkeypatch.setenv("SG_PUMP_FLOW_ML_PER_SEC", flow)
    stats = client.get(f"/api/v1/web/devices/{DEVICE}/dashboard").json()["watering_stats"]
    assert stats["flow_is_configured"] is False
    assert stats["estimated_water_ml"] is None
    assert stats["pump_flow_ml_per_sec"] is None

@pytest.mark.parametrize('reserved,expected', [(4000,201),(20000,409)])
def test_unlimited_count_still_checks_time_budget(client, reserved, expected):
    row=telemetry();row.update(mode='MANUAL',commissioned=True,timestamp=utc_iso(),quota_limit_starts=0,quota_starts=20,quota_limit_ms=20000,quota_reserved_ms=reserved)
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==200
    result=client.post(f'/api/v1/web/devices/{DEVICE}/commands',admin=True,json={'kind':'WATER','duration_ms':500})
    assert result.status_code==expected


@pytest.mark.parametrize('body', [
    {'kind':'SET_MODE','mode':'OFF','duration_ms':500},
    {'kind':'STOP','mode':'AUTO'},
    {'kind':'WATER','duration_ms':500,'mode':'AUTO'},
])
def test_command_rejects_fields_for_another_kind(client, db, body):
    response=client.post(f'/api/v1/web/devices/{DEVICE}/commands',admin=True,json=body)
    assert response.status_code==400
    assert db.one('SELECT COUNT(*) AS n FROM commands')['n']==0
