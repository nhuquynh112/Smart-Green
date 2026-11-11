from __future__ import annotations

import hmac
import csv
import io
import json
import math
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Path as PathParam, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
AI_PACKAGE = ROOT / "ai"
if str(AI_PACKAGE) not in sys.path:
    sys.path.insert(0, str(AI_PACKAGE))

from backend.ai_service import make_recent_minute_dataframe, rebase_demo_window, run_prediction, STATIC_DEMO_BOOT_ID
from backend.database import Database, canonical_json, hash_key, utc_iso


TELEMETRY_REQUIRED = {"schema_version", "device_id", "boot_id", "sample_seq", "timestamp", "uptime_ms",
                      "soil_raw", "light_raw",
                      "soil_pct", "soil_valid", "temperature_c", "humidity_pct", "air_valid",
                      "light_raw", "light_lux", "tank_ok", "pump_on", "mode", "calibration_id",
                      "data_origin"}
EVENT_REQUIRED = {"schema_version", "device_id", "event_id", "command_seq", "started_at",
                  "planned_ms", "actual_ms", "source", "reason"}
MODES = {"OFF", "MANUAL", "AUTO"}
SOURCES = {"AI", "MANUAL", "RULE"}
REASONS = {"Running", "Duration", "Wet", "Sensor", "Tank", "Stop", "Reboot", "Guard"}
WEB_SECURITY = HTTPBasic(auto_error=False)


def _json_for_db(db: Database) -> str:
    return "?" if db.sqlite else "?::jsonb"


def _parse_time(value: Any, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise HTTPException(422, detail=f"{field} must be ISO-8601 string or null")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(422, detail=f"Invalid {field}") from exc
    if result.tzinfo is None:
        raise HTTPException(422, detail=f"{field} must include timezone")
    return result.astimezone(timezone.utc)


def _device_key(db: Database, device_id: str, supplied: str | None) -> None:
    row = db.one("SELECT api_key_hash FROM devices WHERE device_id=?", (device_id,))
    if not supplied or not row or not hmac.compare_digest(hash_key(supplied), row["api_key_hash"].strip()):
        raise HTTPException(401, detail="unauthorized")


def _touch_device(db: Database, device_id: str, calibration_id: str | None = None) -> None:
    now = utc_iso()
    if db.sqlite:
        db.execute("UPDATE devices SET connected=1,last_seen_at=?,calibration_id=COALESCE(?,calibration_id) WHERE device_id=?",
                   (now, calibration_id, device_id))
    else:
        db.execute("UPDATE devices SET connected=true,last_seen_at=?,calibration_id=COALESCE(?,calibration_id) WHERE device_id=?",
                   (now, calibration_id, device_id))


def _validate_telemetry(body: dict, path_device: str) -> tuple[str, int, datetime | None]:
    missing = sorted(TELEMETRY_REQUIRED - body.keys())
    if missing:
        raise HTTPException(422, detail={"missing": missing})
    if type(body.get("schema_version")) is not int or body.get("schema_version") != 1 or body.get("device_id") != path_device:
        raise HTTPException(422, detail="schema_version or device_id mismatch")
    if not isinstance(body.get("boot_id"), str) or not body["boot_id"]:
        raise HTTPException(422, detail="boot_id required")
    if type(body.get("sample_seq")) is not int or body["sample_seq"] <= 0:
        raise HTTPException(422, detail="sample_seq must be a positive integer")
    for name, maximum in (("uptime_ms", None), ("soil_raw", 4095), ("light_raw", 4095)):
        value = body.get(name)
        if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
            raise HTTPException(422, detail=f"invalid {name}")
    for name in ("cooldown_remaining_ms", "max_pulse_ms", "quota_limit_ms", "quota_limit_starts", "quota_reserved_ms", "quota_starts", "quota_window_ends_at"):
        if name in body and (type(body[name]) is not int or not 0 <= body[name] <= 2**53-1):
            raise HTTPException(422, detail=f"invalid {name}")
    if body.get("mode") not in MODES:
        raise HTTPException(422, detail="invalid mode")
    for name in ("soil_valid", "air_valid", "tank_ok", "pump_on"):
        if type(body.get(name)) is not bool:
            raise HTTPException(422, detail=f"{name} must be boolean")
    if body["soil_valid"] != (body.get("soil_pct") is not None):
        raise HTTPException(422, detail="soil validity mismatch")
    if body["air_valid"] != (body.get("temperature_c") is not None and body.get("humidity_pct") is not None):
        raise HTTPException(422, detail="air validity mismatch")
    for name, low, high in (("soil_pct", 0, 100), ("humidity_pct", 0, 100), ("light_lux", 0, None)):
        value = body.get(name)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                                  or value < low or (high is not None and value > high)):
            raise HTTPException(422, detail=f"invalid {name}")
    value = body.get("temperature_c")
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not -40 <= value <= 85):
        raise HTTPException(422, detail="invalid temperature_c")
    return body["boot_id"], body["sample_seq"], _parse_time(body.get("timestamp"), "timestamp")


def enqueue_command(db: Database, device_id: str, command_seq: int, kind: str,
                    issued_at: int, expires_at: int, source: str | None = None,
                    duration_ms: int | None = None, mode: str | None = None,
                    ai_advice: dict | None = None) -> None:
    """Insert a validated command for the trusted operator/dashboard service."""
    if type(command_seq) is not int or command_seq <= 0:
        raise ValueError("command_seq must be positive")
    if type(issued_at) is not int or type(expires_at) is not int or not 0 < expires_at-issued_at <= 60:
        raise ValueError("command TTL must be between 1 and 60 seconds")
    if kind == "WATER":
        if source not in {"AI", "MANUAL"} or type(duration_ms) is not int or duration_ms <= 0 or mode is not None:
            raise ValueError("invalid WATER command")
        if source == "AI" and (os.getenv("SG_AI_COMMANDS_ENABLED", "false").lower() != "true"
                                or not isinstance(ai_advice, dict) or ai_advice.get("can_trigger_pump") is not True):
            raise ValueError("AI command is disabled or advice does not authorize pump control")
    elif kind == "SET_MODE":
        if mode not in MODES or source is not None or duration_ms is not None:
            raise ValueError("invalid SET_MODE command")
    elif kind == "STOP":
        if source is not None or duration_ms is not None or mode is not None:
            raise ValueError("invalid STOP command")
    else:
        raise ValueError("invalid command kind")
    if db.sqlite:
        db.execute("INSERT INTO commands(device_id,command_seq,schema_version,kind,source,duration_ms,mode,issued_at,expires_at,created_at) VALUES(?,?,1,?,?,?,?,?,?,?)",
                   (device_id, command_seq, kind, source, duration_ms, mode, issued_at, expires_at, utc_iso()))
    else:
        db.execute("INSERT INTO commands(device_id,command_seq,schema_version,kind,source,duration_ms,mode,issued_at,expires_at) VALUES(?,?,1,?,?,?,?,?,?)",
                   (device_id, command_seq, kind, source, duration_ms, mode, issued_at, expires_at))


def _load_bundle(path: str | None) -> dict | None:
    if not path:
        path = os.getenv("SG_AI_MODEL_PATH", str(ROOT / "artifacts/offline-demo-v2/model/candidate.joblib"))
    model_path = Path(path)
    if not model_path.is_file():
        return None
    import joblib
    return joblib.load(model_path)


def _configured_keys() -> dict[str, str]:
    configured = os.getenv("SG_DEVICE_KEYS", "")
    if configured:
        value = json.loads(configured)
        if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
            raise RuntimeError("SG_DEVICE_KEYS must be a JSON object mapping device IDs to API keys")
        return value
    device, key = os.getenv("SG_DEVICE_ID"), os.getenv("SG_API_KEY")
    return {device: key} if device and key else {}


def _admin_auth(credentials: HTTPBasicCredentials | None = Depends(WEB_SECURITY)) -> str:
    expected_user = os.getenv("SG_WEB_USER", "admin")
    expected_password = os.getenv("SG_WEB_PASSWORD", "smartgreen2026")
    if (credentials is None or not secrets.compare_digest(credentials.username, expected_user)
            or not secrets.compare_digest(credentials.password, expected_password)):
        from fastapi import status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tài khoản quản trị viên")
    return credentials.username


def _unpack_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _model_evaluation(bundle: dict | None) -> dict | None:
    if not bundle:
        return None
    metadata = bundle.get("metadata", {})
    return {
        "selected_model": metadata.get("selected_by_validation"),
        "horizon_minutes": metadata.get("horizon_minutes"),
        "data_origin": metadata.get("quality", {}).get("data_origin"),
        "calibration_id": metadata.get("quality", {}).get("calibration_id"),
        "device_id": metadata.get("quality", {}).get("device_id"),
        "can_trigger_pump": bool(metadata.get("automatic_irrigation_approved", False)) and False,
        "test_mae": metadata.get("test_mae_percentage_points", {}),
        "validation_mae": metadata.get("validation_mae_percentage_points", {}),
    }


def create_app(db: Database | None = None, bundle: dict | None = None,
               model_path: str | None = None, ai_predictor=None) -> FastAPI:
    database = db or Database()
    for device_id, key in _configured_keys().items():
        database.ensure_device(device_id, key)
    model_bundle = bundle if bundle is not None else _load_bundle(model_path)
    app = FastAPI(title="Smart-Green API", version="1.0", redirect_slashes=False)
    app.state.db = database
    app.state.ai_bundle = model_bundle
    app.state.ai_predictor = ai_predictor
    app.mount("/static", StaticFiles(directory=ROOT / "backend" / "static"), name="static")

    def make_prediction(device_id: str, history_complete: bool | None = None) -> dict:
        bundle = app.state.ai_bundle
        latest_row = database.one("SELECT data_origin,calibration_id FROM telemetry WHERE device_id=? ORDER BY received_at DESC LIMIT 1", (device_id,))
        latest_origin = latest_row.get("data_origin") if latest_row else None
        if bundle is None:
            result = {"status": "unavailable", "reason": "AI model is not configured", "can_trigger_pump": False}
        else:
            if history_complete is not None:
                if database.sqlite:
                    database.execute("UPDATE devices SET watering_history_complete=? WHERE device_id=?",
                                     (history_complete, device_id))
                else:
                    database.execute("UPDATE devices SET watering_history_complete=? WHERE device_id=?",
                                     (history_complete, device_id))
            device = database.one("SELECT watering_history_complete FROM devices WHERE device_id=?", (device_id,))
            if not device or not device["watering_history_complete"]:
                result = {"status": "unavailable", "reason": "watering history is not confirmed complete", "can_trigger_pump": False}
            else:
                quality = bundle.get("metadata", {}).get("quality", {})
                is_static_model_demo = (device_id == quality.get("device_id")
                                        and latest_origin == quality.get("data_origin") == "synthetic"
                                        and latest_row and latest_row.get("calibration_id") == quality.get("calibration_id"))
                if is_static_model_demo:
                    # The SIM-ONLY dashboard may also receive 5-second simulator telemetry.
                    # AI continues to use its immutable seeded v2 series, never a short live tail.
                    rows = database.all("SELECT * FROM telemetry WHERE device_id=? AND boot_id=? AND measured_at IS NOT NULL ORDER BY measured_at DESC LIMIT 240",
                                        (device_id, STATIC_DEMO_BOOT_ID))
                else:
                    rows = database.all("SELECT * FROM telemetry WHERE device_id=? AND measured_at IS NOT NULL ORDER BY measured_at DESC LIMIT 240", (device_id,))
                rows.reverse()
                if is_static_model_demo:
                    events = database.all("SELECT * FROM watering_events WHERE device_id=? AND reason IN ('Manual','Scheduled') ORDER BY started_at", (device_id,))
                else:
                    events = database.all("SELECT * FROM watering_events WHERE device_id=? ORDER BY started_at", (device_id,))
                recent = make_recent_minute_dataframe(device_id, rows, events)
                if recent.empty:
                    result = {"status": "unavailable", "reason": "no valid measured telemetry history", "can_trigger_pump": False}
                else:
                    prediction_now = datetime.now(timezone.utc)
                    if is_static_model_demo:
                        recent = rebase_demo_window(recent, prediction_now)
                    args = (bundle, recent)
                    kwargs = {"now": prediction_now.isoformat()}
                    result = (run_prediction(*args, predictor=app.state.ai_predictor, **kwargs)
                              if app.state.ai_predictor else run_prediction(*args, **kwargs))
        raw = canonical_json(result)
        quality = bundle.get("metadata", {}).get("quality", {}) if bundle else {}
        values = (device_id, result.get("as_of"), result.get("available_at"), result.get("horizon_minutes"),
                  result.get("predicted_soil_pct"), result.get("model"), latest_origin or quality.get("data_origin"),
                  False, result["status"], raw)
        if database.sqlite:
            database.execute("INSERT INTO ai_predictions(device_id,as_of,available_at,horizon_minutes,predicted_soil_pct,model_name,data_origin,can_trigger_pump,status,raw_output,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                             values + (utc_iso(),))
        else:
            database.execute("INSERT INTO ai_predictions(device_id,as_of,available_at,horizon_minutes,predicted_soil_pct,model_name,data_origin,can_trigger_pump,status,raw_output) VALUES(?,?,?,?,?,?,?,?,?,?::jsonb)", values)
        return result

    @app.get("/", include_in_schema=False)
    def dashboard_page():
        return FileResponse(ROOT / "backend" / "static" / "index.html", media_type="text/html; charset=utf-8")

    @app.post("/api/v1/devices/{device_id}/telemetry")
    def post_telemetry(device_id: str, body: dict, x_api_key: str | None = Header(default=None)):
        _device_key(database, device_id, x_api_key)
        boot_id, sample_seq, measured_at = _validate_telemetry(body, device_id)
        canonical = canonical_json(body)
        identity = (device_id, boot_id, sample_seq)
        payload_sql = _json_for_db(database)
        with database.transaction() as conn:
            prior = database.one_on(conn, "SELECT payload FROM telemetry WHERE device_id=? AND boot_id=? AND sample_seq=?", identity)
            if prior:
                existing = prior["payload"]
                if not isinstance(existing, str):
                    existing = canonical_json(existing)
                if canonical_json(json.loads(existing)) != canonical:
                    raise HTTPException(409, detail="telemetry identity conflict")
            else:
                values = (device_id, boot_id, sample_seq, body.get("schema_version"), body.get("build_stage"),
                          measured_at.isoformat().replace("+00:00", "Z") if measured_at else None,
                          utc_iso(), body.get("uptime_ms"), body.get("data_origin"), body.get("calibration_id"),
                          body.get("soil_raw"), body.get("soil_pct"), body.get("soil_valid"),
                          body.get("temperature_c"), body.get("humidity_pct"), body.get("air_valid"),
                          body.get("light_raw"), body.get("light_lux"), body.get("tank_ok"), body.get("tank_ok"),
                          body.get("mode"), body.get("pump_on"), body.get("commissioned"),
                          body.get("storage_fault"), body.get("clock_ready"), body.get("clock_fault"),
                          body.get("server_available"), body.get("last_command_seq"), body.get("queued_events"),
                          body.get("telemetry_overwrites"), canonical)
                columns = "device_id,boot_id,sample_seq,schema_version,build_stage,measured_at,received_at,uptime_ms,data_origin,calibration_id,soil_raw,soil_pct,soil_valid,temperature_c,humidity_pct,air_valid,light_raw,light_lux,water_ok,tank_ok,mode,pump_running,commissioned,storage_fault,clock_ready,clock_fault,server_available,last_command_seq,queued_events,telemetry_overwrites,payload"
                marks = ",".join(["?"]*30 + [payload_sql])
                database.execute_on(conn, f"INSERT INTO telemetry({columns}) VALUES({marks})", values)
            if database.sqlite:
                database.execute_on(conn, "UPDATE devices SET connected=1,last_seen_at=?,calibration_id=COALESCE(?,calibration_id) WHERE device_id=?",
                                    (utc_iso(), body.get("calibration_id"), device_id))
            else:
                database.execute_on(conn, "UPDATE devices SET connected=true,last_seen_at=?,calibration_id=COALESCE(?,calibration_id) WHERE device_id=?",
                                    (utc_iso(), body.get("calibration_id"), device_id))
        return {"stored": True}

    @app.get("/api/v1/devices/{device_id}/commands/next")
    def get_next_command(device_id: str, after_seq: int = Query(0, ge=0), x_api_key: str | None = Header(default=None)):
        _device_key(database, device_id, x_api_key)
        now = int(datetime.now(timezone.utc).timestamp())
        with database.transaction() as conn:
            database.execute_on(conn, "UPDATE commands SET status='EXPIRED' WHERE device_id=? AND status='PENDING' AND expires_at<=?", (device_id, now))
            row = database.one_on(conn, "SELECT * FROM commands WHERE device_id=? AND command_seq>? AND status='PENDING' AND expires_at>? ORDER BY command_seq LIMIT 1",
                                  (device_id, after_seq, now))
        if not row:
            return Response(status_code=204)
        response = {"schema_version": row["schema_version"], "device_id": device_id,
                    "command_seq": row["command_seq"], "kind": row["kind"],
                    "issued_at": row["issued_at"], "expires_at": row["expires_at"]}
        if row["kind"] == "WATER":
            response.update(source=row["source"], duration_ms=row["duration_ms"])
        elif row["kind"] == "SET_MODE":
            response["mode"] = row["mode"]
        return JSONResponse(response)

    @app.post("/api/v1/devices/{device_id}/commands/{seq}/ack")
    def post_ack(device_id: str, seq: int = PathParam(gt=0), body: dict = None,
                 x_api_key: str | None = Header(default=None)):
        _device_key(database, device_id, x_api_key)
        body = body or {}
        if type(body.get("schema_version")) is not int or body.get("schema_version") != 1 or body.get("device_id") != device_id or type(body.get("command_seq")) is not int or body.get("command_seq") != seq or not isinstance(body.get("result"), str):
            raise HTTPException(422, detail="invalid ACK payload")
        now = utc_iso()
        with database.transaction() as conn:
            row = database.one_on(conn, "SELECT status FROM commands WHERE device_id=? AND command_seq=?", (device_id, seq))
            if not row:
                raise HTTPException(404, detail="unknown command")
            database.execute_on(conn, "UPDATE commands SET status=CASE WHEN status='PENDING' THEN 'ACKED' ELSE status END,ack_result=COALESCE(ack_result,?),acked_at=COALESCE(acked_at,?) WHERE device_id=? AND command_seq=?",
                                (body["result"], now, device_id, seq))
        return Response(status_code=204)

    @app.post("/api/v1/devices/{device_id}/events")
    def post_event(device_id: str, body: dict, x_api_key: str | None = Header(default=None)):
        _device_key(database, device_id, x_api_key)
        missing = sorted(EVENT_REQUIRED - body.keys())
        if missing:
            raise HTTPException(422, detail={"missing": missing})
        if type(body.get("schema_version")) is not int or body.get("schema_version") != 1 or body.get("device_id") != device_id:
            raise HTTPException(422, detail="schema_version or device_id mismatch")
        if type(body.get("event_id")) is not int or body["event_id"] <= 0 or type(body.get("command_seq")) is not int or body["command_seq"] < 0:
            raise HTTPException(422, detail="invalid event identity")
        if type(body.get("started_at")) is not int or body["started_at"] < 0 or type(body.get("planned_ms")) is not int or body["planned_ms"] <= 0:
            raise HTTPException(422, detail="invalid event time/duration")
        actual = body.get("actual_ms")
        if (actual is not None and (type(actual) is not int or actual < 0)) or (body.get("reason") == "Reboot" and actual is not None):
            raise HTTPException(422, detail="actual_ms must be null for Reboot")
        if body.get("reason") != "Reboot" and actual is None:
            raise HTTPException(422, detail="actual_ms is required except for Reboot")
        if body.get("source") not in SOURCES or body.get("reason") not in REASONS:
            raise HTTPException(422, detail="invalid event source/reason")
        canonical = canonical_json(body)
        payload_sql = _json_for_db(database)
        with database.transaction() as conn:
            prior = database.one_on(conn, "SELECT payload FROM watering_events WHERE device_id=? AND event_id=?",
                                    (device_id, body["event_id"]))
            if prior:
                existing = prior["payload"]
                if not isinstance(existing, str):
                    existing = canonical_json(existing)
                if canonical_json(json.loads(existing)) != canonical:
                    raise HTTPException(409, detail="event identity conflict")
            else:
                database.execute_on(conn, f"INSERT INTO watering_events(device_id,event_id,schema_version,command_seq,started_at,planned_ms,actual_ms,source,reason,received_at,payload) VALUES(?,?,1,?,?,?,?,?,?,?,{payload_sql})",
                                    (device_id, body["event_id"], body["command_seq"], body["started_at"], body["planned_ms"], actual,
                                     body["source"], body["reason"], utc_iso(), canonical))
        return {"event_id": body["event_id"]}

    @app.get("/api/v1/devices/{device_id}/ai/prediction")
    def ai_prediction(device_id: str, x_api_key: str | None = Header(default=None)):
        _device_key(database, device_id, x_api_key)
        return make_prediction(device_id)

    @app.get("/api/v1/web/devices")
    def web_devices():
        devices = database.all("SELECT device_id,display_name,is_demo,connected,last_seen_at,calibration_id,dry_raw,wet_raw,watering_history_complete FROM devices ORDER BY device_id")
        result = []
        for device in devices:
            latest = database.one("SELECT measured_at,received_at,soil_pct,soil_valid,tank_ok,mode FROM telemetry WHERE device_id=? ORDER BY received_at DESC LIMIT 1", (device["device_id"],))
            received = latest.get("received_at") if latest else device.get("last_seen_at")
            if isinstance(received, str):
                received_dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
            else:
                received_dt = received
            online = bool(device.get("connected")) and bool(received_dt and (datetime.now(timezone.utc)-received_dt.astimezone(timezone.utc)).total_seconds() <= 120)
            result.append({**device, "connected": bool(device.get("connected")), "online": online, "latest": latest})
        return result

    @app.get("/api/v1/web/devices/{device_id}/dashboard")
    def web_dashboard(device_id: str):
        device = database.one("SELECT device_id,display_name,is_demo,connected,last_seen_at,calibration_id,dry_raw,wet_raw,watering_history_complete FROM devices WHERE device_id=?", (device_id,))
        if not device:
            raise HTTPException(404, detail="Không tìm thấy thiết bị")
        rows = database.all("SELECT * FROM telemetry WHERE device_id=? ORDER BY received_at DESC LIMIT 180", (device_id,))
        rows.reverse()
        latest = rows[-1] if rows else None
        now_unix = int(datetime.now(timezone.utc).timestamp())
        with database.transaction() as conn:
            database.execute_on(conn, "UPDATE commands SET status='EXPIRED' WHERE device_id=? AND status='PENDING' AND expires_at<=?",
                                (device_id, now_unix))
        commands = database.all("SELECT command_seq,schema_version,kind,source,duration_ms,mode,issued_at,expires_at,status,ack_result,acked_at FROM commands WHERE device_id=? ORDER BY command_seq DESC LIMIT 30", (device_id,))
        events = database.all("SELECT event_id,command_seq,started_at,planned_ms,actual_ms,ended_at,source,reason,received_at,payload FROM watering_events WHERE device_id=? ORDER BY event_id DESC LIMIT 30", (device_id,))
        predictions = database.all("SELECT prediction_id,as_of,available_at,horizon_minutes,predicted_soil_pct,model_name,data_origin,can_trigger_pump,status,raw_output,created_at FROM ai_predictions WHERE device_id=? ORDER BY prediction_id DESC LIMIT 10", (device_id,))
        for event in events:
            event["payload"] = _unpack_json(event.get("payload"))
        for prediction in predictions:
            prediction["raw_output"] = _unpack_json(prediction.get("raw_output"))
            prediction["can_trigger_pump"] = bool(prediction.get("can_trigger_pump"))
        evaluation = _model_evaluation(app.state.ai_bundle)
        now_unix = int(datetime.now(timezone.utc).timestamp())
        stats_row = database.one("""SELECT
            COUNT(CASE WHEN actual_ms IS NOT NULL AND reason<>'Reboot' THEN 1 END) AS total_events,
            COUNT(CASE WHEN actual_ms IS NOT NULL AND reason<>'Reboot'
                       AND COALESCE(ended_at,started_at)>=? AND COALESCE(ended_at,started_at)<=? THEN 1 END) AS events_last_24h,
            COUNT(CASE WHEN actual_ms IS NOT NULL AND reason<>'Reboot' AND upper(source)='MANUAL' THEN 1 END) AS manual_count,
            COUNT(CASE WHEN actual_ms IS NOT NULL AND reason<>'Reboot' AND upper(source) IN ('AI','RULE','SCHEDULED') THEN 1 END) AS auto_count,
            COALESCE(SUM(CASE WHEN actual_ms IS NOT NULL AND reason<>'Reboot' THEN actual_ms ELSE 0 END),0) AS total_actual_ms
            FROM watering_events WHERE device_id=?""", (now_unix-86400, now_unix, device_id))
        try:
            flow_ml_per_sec = float(os.getenv("SG_PUMP_FLOW_ML_PER_SEC", "10"))
            if not math.isfinite(flow_ml_per_sec) or flow_ml_per_sec <= 0:
                raise ValueError
            flow_configured = "SG_PUMP_FLOW_ML_PER_SEC" in os.environ
        except ValueError:
            flow_ml_per_sec = 10.0
            flow_configured = False
        try:
            max_daily_events = max(1, int(os.getenv("SG_MAX_DAILY_WATERING_EVENTS", "6")))
        except ValueError:
            max_daily_events = 6
        total_actual_ms = int(stats_row["total_actual_ms"] or 0)
        watering_stats = {
            "total_events": int(stats_row["total_events"] or 0),
            "events_last_24h": int(stats_row["events_last_24h"] or 0),
            "max_daily_events": max_daily_events,
            "manual_count": int(stats_row["manual_count"] or 0),
            "auto_count": int(stats_row["auto_count"] or 0),
            "total_actual_ms": total_actual_ms,
            "total_actual_seconds": total_actual_ms / 1000.0,
            "estimated_water_ml": round(total_actual_ms / 1000.0 * flow_ml_per_sec, 1) if flow_configured else None,
            "pump_flow_ml_per_sec": flow_ml_per_sec if flow_configured else None,
            "flow_is_configured": flow_configured,
            "flow_note": ("Theo lưu lượng đã cấu hình" if flow_configured
                          else "Chưa hiệu chuẩn lưu lượng; chưa quy đổi sang ml"),
        }
        return {"device": device, "latest": latest, "history": rows, "commands": commands,
                "watering_events": events, "latest_ai": predictions[0] if predictions else None,
                "ai_history": predictions, "model_evaluation": evaluation, "watering_stats": watering_stats}

    @app.get("/api/v1/web/devices/{device_id}/export-csv")
    def web_export_csv(device_id: str):
        if not database.one("SELECT device_id FROM devices WHERE device_id=?", (device_id,)):
            raise HTTPException(404, detail="Không tìm thấy thiết bị")
        columns = ["device_id", "boot_id", "sample_seq", "measured_at", "received_at", "soil_raw",
                   "soil_pct", "soil_valid", "temperature_c", "humidity_pct", "air_valid", "light_raw",
                   "light_lux", "water_ok", "mode", "pump_running", "storage_fault", "clock_ready", "clock_fault"]
        rows = database.all("SELECT " + ",".join(columns) + " FROM telemetry WHERE device_id=? ORDER BY measured_at,boot_id,sample_seq", (device_id,))
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(column) for column in columns])
        filename = f"smart-garden-{device_id}-telemetry.csv"
        return Response(content="\ufeff" + buffer.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    @app.post("/api/v1/web/devices/{device_id}/commands")
    def web_create_command(device_id: str, body: dict, _: str = Depends(_admin_auth)):
        kind = body.get("kind")
        ttl = body.get("ttl_sec", 30)
        if type(ttl) is not int or not 1 <= ttl <= 60:
            raise HTTPException(400, detail="TTL phải là số nguyên từ 1 đến 60 giây")
        if kind not in {"WATER", "SET_MODE", "STOP"}:
            raise HTTPException(400, detail="Loại lệnh không hợp lệ")
        duration = body.get("duration_ms")
        mode = body.get("mode")
        source = None
        allowed = {"kind", "ttl_sec"} | ({"duration_ms"} if kind == "WATER" else {"mode"} if kind == "SET_MODE" else set())
        if set(body) - allowed:
            raise HTTPException(400, detail="Lệnh chứa trường không phù hợp với loại lệnh")
        if kind == "WATER":
            if type(duration) is not int or duration <= 0:
                raise HTTPException(400, detail="duration_ms phải là số nguyên dương")
            maximum = int(os.getenv("SG_MAX_PULSE_MS", os.getenv("SG_MAX_PUMP_MS", "1000")))
            if duration > maximum:
                raise HTTPException(400, detail=f"Thời gian tưới vượt giới hạn an toàn {maximum} ms")
            latest = database.one("SELECT * FROM telemetry WHERE device_id=? ORDER BY received_at DESC LIMIT 1", (device_id,))
            if not latest:
                raise HTTPException(400, detail="Chưa có telemetry mới; từ chối tưới an toàn")
            water_state = latest.get("water_ok") if latest.get("water_ok") is not None else latest.get("tank_ok")
            if water_state is not True and water_state != 1:
                raise HTTPException(400, detail="Phao báo hết nước hoặc chưa xác nhận đủ nước")
            if latest.get("soil_valid") is not True and latest.get("soil_valid") != 1:
                raise HTTPException(400, detail="Cảm biến độ ẩm đất lỗi hoặc chưa hợp lệ")
            received = latest.get("received_at")
            if isinstance(received, str): received = _parse_time(received, "received_at")
            if received is None or (datetime.now(timezone.utc)-received).total_seconds() > 90:
                raise HTTPException(409, detail="Dữ liệu thiết bị đã cũ; chờ ESP32 kết nối lại")
            if not latest.get("clock_ready") or latest.get("clock_fault"):
                raise HTTPException(409, detail="Đồng hồ thiết bị chưa sẵn sàng")
            if not latest.get("commissioned") or latest.get("storage_fault"):
                raise HTTPException(409, detail="Thiết bị chưa được xác nhận hoặc có lỗi lưu trữ")
            if latest.get("pump_running"):
                raise HTTPException(409, detail="Bơm đang chạy; chờ lần hiện tại kết thúc")
            if latest.get("mode") != "MANUAL":
                raise HTTPException(409, detail="Chờ telemetry xác nhận chế độ MANUAL trước khi tưới")
            measured = latest.get("measured_at")
            if isinstance(measured, str): measured = _parse_time(measured, "measured_at")
            age = (datetime.now(timezone.utc)-measured).total_seconds() if measured else float("inf")
            if age > 90 or age < -5:
                raise HTTPException(409, detail="Mẫu đo đã cũ hoặc thời gian đo không hợp lệ")
            payload = _unpack_json(latest.get("payload")) or {}
            elapsed = max(0, (datetime.now(timezone.utc)-received).total_seconds()*1000)
            if payload.get("cooldown_remaining_ms", 0) > elapsed:
                raise HTTPException(409, detail="Thiết bị đang trong thời gian nghỉ")
            if duration > payload.get("max_pulse_ms", maximum):
                raise HTTPException(400, detail="Thời lượng vượt giới hạn thực của ESP32")
            if ((payload.get("quota_limit_starts", float("inf")) > 0 and payload.get("quota_starts", 0) >= payload.get("quota_limit_starts", float("inf")))
                    or duration + payload.get("quota_reserved_ms", 0) > payload.get("quota_limit_ms", float("inf"))):
                raise HTTPException(409, detail="Đã đạt hạn mức thực của ESP32; không xếp thêm lệnh tưới")
            source = "MANUAL"
        elif kind == "SET_MODE":
            if mode not in MODES:
                raise HTTPException(400, detail="mode phải là OFF, MANUAL hoặc AUTO")
        else:
            duration = mode = None
        now = int(datetime.now(timezone.utc).timestamp())
        with database.transaction() as conn:
            lock = " FOR UPDATE" if not database.sqlite else ""
            device_state = database.one_on(conn, "SELECT last_command_seq FROM devices WHERE device_id=?" + lock, (device_id,))
            if not device_state:
                raise HTTPException(404, detail="Không tìm thấy thiết bị")
            database.execute_on(conn, "UPDATE commands SET status='EXPIRED' WHERE device_id=? AND status='PENDING' AND expires_at<=?", (device_id, now))
            if kind == "STOP" or (kind == "SET_MODE" and mode == "OFF"):
                database.execute_on(conn, "UPDATE commands SET status='EXPIRED',ack_result=COALESCE(ack_result,'superseded_by_stop') WHERE device_id=? AND status='PENDING'", (device_id,))
            elif database.one_on(conn, "SELECT command_seq FROM commands WHERE device_id=? AND status='PENDING' LIMIT 1", (device_id,)):
                raise HTTPException(409, detail="Có lệnh đang chờ ESP32; không gửi lặp")
            max_row = database.one_on(conn, "SELECT MAX(command_seq) AS seq FROM commands WHERE device_id=?", (device_id,))
            telemetry_seq = database.one_on(conn, "SELECT MAX(last_command_seq) AS seq FROM telemetry WHERE device_id=?", (device_id,))
            seq = max(int(device_state.get("last_command_seq") or 0), int(max_row.get("seq") or 0),
                      int(telemetry_seq.get("seq") or 0)) + 1
            values = (device_id, seq, kind, source, duration, mode, now, now + ttl)
            if database.sqlite:
                database.execute_on(conn, "INSERT INTO commands(device_id,command_seq,schema_version,kind,source,duration_ms,mode,issued_at,expires_at,created_at) VALUES(?,?,1,?,?,?,?,?,?,?)",
                                    values + (utc_iso(),))
                database.execute_on(conn, "UPDATE devices SET last_command_seq=? WHERE device_id=?", (seq, device_id))
            else:
                database.execute_on(conn, "INSERT INTO commands(device_id,command_seq,schema_version,kind,source,duration_ms,mode,issued_at,expires_at) VALUES(?,?,1,?,?,?,?,?,?)", values)
                database.execute_on(conn, "UPDATE devices SET last_command_seq=? WHERE device_id=?", (seq, device_id))
        response = {"schema_version": 1, "device_id": device_id, "command_seq": seq, "kind": kind,
                    "issued_at": now, "expires_at": now + ttl, "status": "PENDING"}
        if kind == "WATER":
            response.update(source="MANUAL", duration_ms=duration)
        if kind == "SET_MODE":
            response["mode"] = mode
        return JSONResponse(response, status_code=201)

    @app.get("/api/v1/web/auth/check")
    def web_auth_check(username: str = Depends(_admin_auth)):
        return {"authenticated": True, "username": username}

    @app.post("/api/v1/web/devices/{device_id}/predict")
    def web_predict(device_id: str, body: dict | None = None, _: str = Depends(_admin_auth)):
        if not database.one("SELECT device_id FROM devices WHERE device_id=?", (device_id,)):
            raise HTTPException(404, detail="Không tìm thấy thiết bị")
        history_complete = (body or {}).get("watering_history_complete")
        if history_complete is not None and type(history_complete) is not bool:
            raise HTTPException(400, detail="watering_history_complete phải là boolean")
        return make_prediction(device_id, history_complete)

    return app


app = create_app()
