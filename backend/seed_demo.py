"""Load transparent Fittonia bench sample and the v2 synthetic AI showcase."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "ai") not in sys.path:
    sys.path.insert(0, str(ROOT / "ai"))

from backend.ai_service import (STATIC_DEMO_BOOT_ID, make_recent_minute_dataframe,
                                rebase_demo_window, run_prediction)
from backend.database import Database, canonical_json, utc_iso


BENCH_ID = "fittonia-bench"
BENCH_KEY = "local-demo-fittonia-key"
SIM_KEY = "local-demo-sim-only-key"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _epoch(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def _sensor_payload(device_id: str, boot_id: str, seq: int, at: datetime, *, calibration_id: str,
                    origin: str, soil_raw: int, soil_pct: float | None, soil_valid: bool,
                    temperature: float | None, humidity: float | None, light_raw: int, tank_ok: bool,
                    uptime_ms: int, mode: str = "OFF") -> dict[str, Any]:
    return {
        "schema_version": 1, "build_stage": "demo_seed", "device_id": device_id,
        "boot_id": boot_id, "sample_seq": seq, "timestamp": _iso(at), "uptime_ms": uptime_ms,
        "data_origin": origin, "calibration_id": calibration_id, "soil_raw": soil_raw,
        "soil_pct": soil_pct, "soil_valid": soil_valid,
        "air_valid": temperature is not None and humidity is not None,
        "temperature_c": temperature, "humidity_pct": humidity, "light_raw": light_raw,
        "light_lux": None, "tank_ok": tank_ok, "pump_on": False, "mode": mode,
        "commissioned": False, "storage_fault": False, "clock_ready": True,
        "clock_fault": False, "server_available": True, "last_command_seq": 0,
        "queued_events": 0, "telemetry_overwrites": 0,
    }


def _telemetry_tuple(db: Database, payload: dict, received_at: datetime) -> tuple:
    marks = "?::jsonb" if not db.sqlite else "?"
    return (
        payload["device_id"], payload["boot_id"], payload["sample_seq"], 1, payload["build_stage"],
        payload["timestamp"], _iso(received_at), payload["uptime_ms"], payload["data_origin"],
        payload["calibration_id"], payload["soil_raw"], payload["soil_pct"], payload["soil_valid"],
        payload["temperature_c"], payload["humidity_pct"], payload["air_valid"], payload["light_raw"],
        payload["light_lux"], payload["tank_ok"], payload["tank_ok"], payload["mode"], payload["pump_on"],
        payload["commissioned"], payload["storage_fault"], payload["clock_ready"], payload["clock_fault"],
        payload["server_available"], payload["last_command_seq"], payload["queued_events"],
        payload["telemetry_overwrites"], canonical_json(payload),
    )


def _upsert_device(db: Database, device_id: str, key: str, display_name: str, calibration_id: str,
                   *, is_demo: bool, dry_raw: int | None, wet_raw: int | None, history_complete: bool) -> None:
    db.ensure_device(device_id, key, calibration_id)
    if db.sqlite:
        db.execute("UPDATE devices SET display_name=?,is_demo=?,connected=0,last_seen_at=?,calibration_id=?,dry_raw=?,wet_raw=?,last_command_seq=0,watering_history_complete=? WHERE device_id=?",
                   (display_name, int(is_demo), utc_iso(), calibration_id, dry_raw, wet_raw,
                    int(history_complete), device_id))
    else:
        db.execute("UPDATE devices SET display_name=?,is_demo=?,connected=false,last_seen_at=?,calibration_id=?,dry_raw=?,wet_raw=?,last_command_seq=0,watering_history_complete=? WHERE device_id=?",
                   (display_name, is_demo, utc_iso(), calibration_id, dry_raw, wet_raw,
                    history_complete, device_id))


def _reset_seed_data(db: Database, device_ids: list[str]) -> None:
    with db.transaction() as conn:
        for device_id in device_ids:
            for table in ("ai_predictions", "watering_events", "commands", "telemetry"):
                db.execute_on(conn, f"DELETE FROM {table} WHERE device_id=?", (device_id,))


def _store_demo_prediction(db: Database, device_id: str, bundle: dict) -> dict:
    rows = db.all("SELECT * FROM telemetry WHERE device_id=? AND boot_id=? AND measured_at IS NOT NULL ORDER BY measured_at DESC LIMIT 240",
                  (device_id, STATIC_DEMO_BOOT_ID))
    rows.reverse()
    events = db.all("SELECT * FROM watering_events WHERE device_id=? AND reason IN ('Manual','Scheduled') ORDER BY started_at", (device_id,))
    recent = make_recent_minute_dataframe(device_id, rows, events)
    prediction_now = datetime.now(timezone.utc)
    recent = rebase_demo_window(recent, prediction_now)
    prediction = run_prediction(bundle, recent, now=prediction_now.isoformat())
    if prediction["status"] != "available":
        raise RuntimeError(f"Seed AI demo did not produce a prediction: {prediction.get('reason')}")
    latest = db.one("SELECT boot_id,sample_seq FROM telemetry WHERE device_id=? ORDER BY measured_at DESC LIMIT 1", (device_id,))
    if latest:
        db.execute("UPDATE telemetry SET received_at=? WHERE device_id=? AND boot_id=? AND sample_seq=?",
                   (prediction["available_at"], device_id, latest["boot_id"], latest["sample_seq"]))
    raw = canonical_json(prediction)
    quality = bundle["metadata"]["quality"]
    values = (device_id, prediction["as_of"], prediction["available_at"], prediction["horizon_minutes"],
              prediction["predicted_soil_pct"], prediction["model"], quality["data_origin"], False,
              prediction["status"], raw)
    if db.sqlite:
        db.execute("INSERT INTO ai_predictions(device_id,as_of,available_at,horizon_minutes,predicted_soil_pct,model_name,data_origin,can_trigger_pump,status,raw_output,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   values + (utc_iso(),))
    else:
        db.execute("INSERT INTO ai_predictions(device_id,as_of,available_at,horizon_minutes,predicted_soil_pct,model_name,data_origin,can_trigger_pump,status,raw_output) VALUES(?,?,?,?,?,?,?,?,?,?::jsonb)", values)
    return prediction


def seed_demo(db: Database, model_path: str | Path | None = None,
              data_dir: str | Path | None = None, now: datetime | None = None) -> dict:
    data_dir = Path(data_dir or ROOT / "artifacts" / "offline-demo-v2")
    model_path = Path(model_path or os.getenv("SG_AI_MODEL_PATH", ROOT / "artifacts" / "offline-demo-v2" / "model" / "candidate.joblib"))
    if model_path.is_file():
        import joblib
        bundle = joblib.load(model_path)
    else:
        bundle = None
    if bundle is None:
        raise FileNotFoundError("AI candidate.joblib not found; set SG_AI_MODEL_PATH")
    metadata = bundle["metadata"]["quality"]
    demo_id = metadata["device_id"]
    calibration_id = metadata["calibration_id"]
    if metadata["data_origin"] != "synthetic" or metadata.get("time_basis") != "device_timestamp":
        raise ValueError("The demo seed expects the v2 synthetic, device_timestamp model bundle")
    csv_path = data_dir / "minutes.synthetic.csv"
    journal_path = data_dir / "watering.synthetic.json"
    if not csv_path.is_file() or not journal_path.is_file():
        raise FileNotFoundError("Expected minutes.synthetic.csv and watering.synthetic.json in the demo artifact directory")
    with csv_path.open(newline="", encoding="utf-8") as stream:
        minutes = list(csv.DictReader(stream))
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if not minutes:
        raise ValueError("AI demo minute dataset is empty")
    if any(row["device_id"] != demo_id or row["calibration_id"] != calibration_id or row["data_origin"] != "synthetic"
           or row["time_basis"] != metadata["time_basis"] for row in minutes):
        raise ValueError("AI demo dataset metadata does not match the candidate bundle")

    now = now or datetime.now(timezone.utc)
    now = now.astimezone(timezone.utc)
    closed_minute = now.replace(second=0, microsecond=0)
    original_last = datetime.fromisoformat(minutes[-1]["timestamp"].replace("Z", "+00:00"))
    target_last = closed_minute - timedelta(minutes=1)
    offset = target_last - original_last

    _upsert_device(db, BENCH_ID, os.getenv("SG_BENCH_API_KEY", BENCH_KEY),
                   "Cây Cẩm nhung (Fittonia) · Kịch bản Bench", "fittonia-dry2511-wet979-v1",
                   is_demo=True, dry_raw=2511, wet_raw=979, history_complete=False)
    _upsert_device(db, demo_id, os.getenv("SG_SIM_API_KEY", SIM_KEY),
                   "Mô phỏng AI v2 (SIM-ONLY · 14.400 mẫu)", calibration_id,
                   is_demo=True, dry_raw=None, wet_raw=None, history_complete=True)
    device_ids = [BENCH_ID, demo_id]
    _reset_seed_data(db, device_ids)

    bench_samples = []
    bench_start = closed_minute - timedelta(minutes=60)
    for seq in range(1, 61):
        soil_pct = 44.0 - seq * 0.12
        raw = round(2511 + soil_pct * (979 - 2511) / 100)
        at = bench_start + timedelta(minutes=seq - 1)
        payload = _sensor_payload(BENCH_ID, "demo-bench-boot", seq, at,
                                  calibration_id="fittonia-dry2511-wet979-v1", origin="synthetic",
                                  soil_raw=raw, soil_pct=soil_pct, soil_valid=True,
                                  temperature=26.8 + (seq % 5) * .1, humidity=61.0 - (seq % 4) * .2,
                                  light_raw=890 + seq % 22, tank_ok=True, uptime_ms=seq * 60000)
        bench_samples.append(_telemetry_tuple(db, payload, at + timedelta(minutes=1)))

    minute_samples = []
    for index, row in enumerate(minutes, start=1):
        at = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) + offset
        soil = float(row["soil_pct"]) if row["soil_pct"] else None
        valid = soil is not None
        raw = max(0, min(4095, round(2511 + (soil if soil is not None else 0) * (979 - 2511) / 100)))
        payload = _sensor_payload(demo_id, STATIC_DEMO_BOOT_ID, index, at,
                                  calibration_id=calibration_id, origin="synthetic", soil_raw=raw,
                                  soil_pct=soil, soil_valid=valid,
                                  temperature=float(row["temperature_c"]) if row["temperature_c"] else None,
                                  humidity=float(row["humidity_pct"]) if row["humidity_pct"] else None,
                                  light_raw=0, tank_ok=True,
                                  uptime_ms=index * 60000)
        minute_samples.append(_telemetry_tuple(db, payload, at + timedelta(minutes=1)))

    telemetry_sql = "INSERT INTO telemetry(device_id,boot_id,sample_seq,schema_version,build_stage,measured_at,received_at,uptime_ms,data_origin,calibration_id,soil_raw,soil_pct,soil_valid,temperature_c,humidity_pct,air_valid,light_raw,light_lux,water_ok,tank_ok,mode,pump_running,commissioned,storage_fault,clock_ready,clock_fault,server_available,last_command_seq,queued_events,telemetry_overwrites,payload) VALUES(" + ",".join(["?"]*30 + (["?::jsonb"] if not db.sqlite else ["?"])) + ")"
    with db.transaction() as conn:
        db.executemany_on(conn, telemetry_sql, bench_samples + minute_samples)
        # Preserve the pre-session watering anchor, then import nine events with
        # representative pump timing so the dashboard can explain each duration.
        first_at = datetime.fromisoformat(minutes[0]["timestamp"].replace("Z", "+00:00")) + offset
        baseline_end = int(first_at.timestamp())
        baseline = {"schema_version": 1, "device_id": demo_id, "event_id": 1,
                    "command_seq": 0, "started_at": baseline_end, "ended_at": baseline_end,
                    "planned_ms": 1000, "actual_ms": 1000, "source": "MANUAL", "reason": "Scheduled",
                    "data_origin": "synthetic", "baseline": True}
        journal_events = [(demo_id, 1, 0, baseline_end, 1000, 1000, baseline_end, "MANUAL", "Scheduled",
                           utc_iso(), canonical_json(baseline))]
        for event_id, event in enumerate(journal.get("events", []), start=2):
            started = datetime.fromisoformat(event["started_at"].replace("Z", "+00:00")) + offset
            ended = datetime.fromisoformat(event["ended_at"].replace("Z", "+00:00")) + offset
            payload = {"schema_version": 1, "device_id": demo_id, "event_id": event_id,
                       "command_seq": 0, "started_at": int(started.timestamp()),
                       "ended_at": int(ended.timestamp()), "planned_ms": 1000,
                       "actual_ms": 1000, "source": "MANUAL", "reason": "Scheduled", "method": event.get("method"),
                       "volume_ml": event.get("volume_ml"), "data_origin": "synthetic", "fixture_seed": True}
            journal_events.append((demo_id, event_id, 0, payload["started_at"], payload["planned_ms"],
                                   1000, payload["ended_at"], "MANUAL", "Scheduled", utc_iso(), canonical_json(payload)))
        event_marks = "?::jsonb" if not db.sqlite else "?"
        event_sql = ("INSERT INTO watering_events(device_id,event_id,schema_version,command_seq,started_at,planned_ms,actual_ms,ended_at,source,reason,received_at,payload) "
                     f"VALUES(?,?,1,?,?,?,?,?,?,?,?,{event_marks})")
        db.executemany_on(conn, event_sql, journal_events)

        # Visible sample events for the Fittonia bench card, each more than 20
        # minutes before the final seeded reading and outside the prediction tail.
        bench_end = int((closed_minute - timedelta(minutes=1)).timestamp())
        bench_events = []
        for event_id, minutes_ago in ((1, 50), (2, 35)):
            ended = bench_end - minutes_ago * 60
            started = ended - 20
            payload = {"schema_version": 1, "device_id": BENCH_ID, "event_id": event_id,
                       "command_seq": 0, "started_at": started, "ended_at": ended,
                       "planned_ms": 1000, "actual_ms": 1000, "source": "MANUAL",
                       "reason": "ManualCheck", "method": "pump-check", "data_origin": "synthetic",
                       "fixture_seed": True}
            bench_events.append((BENCH_ID, event_id, 0, started, 1000, 1000, ended,
                                 "MANUAL", "ManualCheck", utc_iso(), canonical_json(payload)))
        db.executemany_on(conn, event_sql, bench_events)

    prediction = _store_demo_prediction(db, demo_id, bundle)
    return {"bench_device_id": BENCH_ID, "bench_samples": len(bench_samples),
            "demo_device_id": demo_id, "demo_samples": len(minute_samples),
            "demo_events": len(journal_events), "bench_events": len(bench_events), "prediction": prediction,
            "data_origin": "synthetic", "can_trigger_pump": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="Overrides DATABASE_URL; defaults to its configured value")
    parser.add_argument("--model", help="Overrides SG_AI_MODEL_PATH")
    parser.add_argument("--data-dir", help="Defaults to artifacts/offline-demo-v2")
    args = parser.parse_args()
    db = Database(args.database_url)
    try:
        print(json.dumps(seed_demo(db, args.model, args.data_dir), ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
