from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd

from smart_green_ai.inference import predict


AI_COLUMNS = ["timestamp", "device_id", "calibration_id", "data_origin", "soil_pct",
              "temperature_c", "humidity_pct", "minutes_since_water", "water_event_count",
              "time_basis"]
STATIC_DEMO_BOOT_ID = "seed-synthetic-v2"
AI_UNAVAILABLE_HISTORY = "Chưa đủ điều kiện: Chưa tích xác nhận đối soát lịch sử tưới hoặc cây vừa được tưới trong 15 phút gần nhất (độ ẩm đang biến động mạnh)."
AI_UNAVAILABLE_DATA = "Chưa đủ điều kiện dữ liệu: Cần tối thiểu 16 phút dữ liệu hoàn tất liên tiếp gần nhất (hiện chỉ có {minutes} phút hoặc dữ liệu đã cũ/ngắt quãng)."
AI_UNAVAILABLE_MODEL = "Mô hình không tương thích: Bundle AI hiện tại được huấn luyện cho định danh/nguồn dữ liệu khác (calibration_id / data_origin không khớp với thiết bị đang chọn)."


def make_recent_minute_dataframe(device_id: str, telemetry: list[dict], events: list[dict]) -> pd.DataFrame:
    """Aggregate stored device-timestamp telemetry to complete UTC minute bins.

    The caller must only use this for devices whose watering history was explicitly
    reviewed as complete. Missing minutes remain absent and are rejected by inference.
    """
    if not telemetry:
        return pd.DataFrame(columns=AI_COLUMNS)
    samples: list[dict[str, Any]] = []
    latest_boot = telemetry[-1].get("boot_id")
    for row in telemetry:
        if latest_boot is not None and row.get("boot_id") != latest_boot:
            continue
        stamp = row.get("measured_at")
        if not stamp or row.get("data_origin") not in {"real", "synthetic"}:
            continue
        ts = pd.Timestamp(stamp)
        if ts.tzinfo is None:
            continue
        ts = ts.tz_convert("UTC")
        samples.append({"timestamp": ts, "device_id": device_id,
                        "calibration_id": row.get("calibration_id"),
                        "data_origin": row.get("data_origin"),
                        "soil_pct": row.get("soil_pct") if row.get("soil_valid") else None,
                        "temperature_c": row.get("temperature_c") if row.get("air_valid") else None,
                        "humidity_pct": row.get("humidity_pct") if row.get("air_valid") else None,
                        "_soil_bad": not bool(row.get("soil_valid")),
                        "_air_bad": not bool(row.get("air_valid"))})
    if not samples:
        return pd.DataFrame(columns=AI_COLUMNS)
    frame = pd.DataFrame(samples).sort_values("timestamp")
    identity = ["device_id", "calibration_id", "data_origin"]
    if any(frame[col].nunique(dropna=False) != 1 for col in identity):
        return pd.DataFrame(columns=AI_COLUMNS)
    frame["timestamp"] = frame.timestamp.dt.floor("min")
    minute = frame.groupby("timestamp", as_index=False).agg(
        device_id=("device_id", "last"), calibration_id=("calibration_id", "last"),
        data_origin=("data_origin", "last"), soil_pct=("soil_pct", "median"),
        temperature_c=("temperature_c", "median"), humidity_pct=("humidity_pct", "median"),
        _soil_bad=("_soil_bad", "any"), _air_bad=("_air_bad", "any"))
    minute.loc[minute._soil_bad, "soil_pct"] = float("nan")
    minute.loc[minute._air_bad, ["temperature_c", "humidity_pct"]] = float("nan")
    minute = minute.drop(columns=["_soil_bad", "_air_bad"])
    minute = minute.sort_values("timestamp")
    usable_events = []
    for event in events:
        if event.get("reason") == "Reboot":
            # Unknown watering duration/time makes downstream features untrustworthy.
            return pd.DataFrame(columns=AI_COLUMNS)
        if event.get("reason") == "ManualHandWatering":
            ended = pd.Timestamp(int(event["started_at"]), unit="s", tz="UTC")
        elif event.get("reason") == "Manual":
            if event.get("ended_at") is None:
                return pd.DataFrame(columns=AI_COLUMNS)
            ended = pd.Timestamp(int(event["ended_at"]), unit="s", tz="UTC")
        elif event.get("actual_ms") is None:
            return pd.DataFrame(columns=AI_COLUMNS)
        else:
            ended = pd.Timestamp(int(event["started_at"]), unit="s", tz="UTC") + pd.Timedelta(milliseconds=event["actual_ms"])
        usable_events.append(ended)
    counts, since = [], []
    for ts in minute.timestamp:
        complete_at = ts + pd.Timedelta(minutes=1)
        past = [e for e in usable_events if e < complete_at]
        counts.append(len(past))
        since.append((complete_at - max(past)).total_seconds() / 60 if past else None)
    minute["water_event_count"] = counts
    minute["minutes_since_water"] = since
    minute["time_basis"] = "device_timestamp"
    return minute[AI_COLUMNS]


def _trailing_complete_minutes(recent: pd.DataFrame) -> int:
    if recent.empty or "timestamp" not in recent:
        return 0
    required = ["soil_pct", "temperature_c", "humidity_pct", "minutes_since_water", "water_event_count"]
    if any(name not in recent for name in required):
        return 0
    frame = recent.sort_values("timestamp")
    count = 0
    previous = None
    for _, row in frame.iloc[::-1].iterrows():
        stamp = pd.Timestamp(row["timestamp"])
        if stamp.tzinfo is None or any(pd.isna(row[name]) for name in required):
            break
        if previous is not None and previous - stamp != pd.Timedelta(minutes=1):
            break
        count += 1
        previous = stamp
    return count


def unavailable_reason(error: Exception | str, recent: pd.DataFrame,
                       bundle: dict | None = None) -> str:
    message = str(error).lower()
    quality = (bundle or {}).get("metadata", {}).get("quality", {})
    if any(token in message for token in ("model/data", "feature version", "time_basis mismatch", "data_origin must")):
        return AI_UNAVAILABLE_MODEL
    if not recent.empty and "minutes_since_water" in recent and len(recent):
        latest_since = pd.to_numeric(recent["minutes_since_water"], errors="coerce").iloc[-1]
        if pd.notna(latest_since) and float(latest_since) <= 15:
            return AI_UNAVAILABLE_HISTORY
        if "water_event_count" in recent:
            tail = recent["water_event_count"].tail(16).dropna()
            if len(tail) > 1 and tail.nunique() > 1:
                return AI_UNAVAILABLE_HISTORY
    minutes = _trailing_complete_minutes(recent)
    # Detect metadata incompatibility before a short-window validation error masks it.
    if bundle and not recent.empty and quality:
        for column, key in (("device_id", "device_id"), ("calibration_id", "calibration_id"), ("data_origin", "data_origin")):
            if column in recent and str(recent[column].iloc[0]) != str(quality.get(key)):
                return AI_UNAVAILABLE_MODEL
    return AI_UNAVAILABLE_DATA.format(minutes=minutes)


def run_prediction(bundle: dict, recent: pd.DataFrame, now: str | None = None,
                   predictor: Callable = predict) -> dict:
    """Run safe advice inference. Never turns an advice object into a pump command."""
    try:
        result = predictor(bundle, recent, now or datetime.now(timezone.utc).isoformat())
        return {"status": "available", **result, "can_trigger_pump": False}
    except (ValueError, KeyError, TypeError) as exc:
        return {"status": "unavailable", "reason": unavailable_reason(exc, recent, bundle),
                "detail": str(exc), "can_trigger_pump": False}


def rebase_demo_window(recent: pd.DataFrame, now: str | datetime | None = None) -> pd.DataFrame:
    """Move a static synthetic sample to the latest closed UTC minute.

    Only demo/static data should use this helper. Relative minute spacing and
    derived watering features are preserved; the model still validates identity,
    feature version, complete windows, and recent-watering exclusions.
    """
    if recent.empty or "timestamp" not in recent:
        raise ValueError("Cannot rebase an empty or invalid demo window")
    frame = recent.copy()
    stamps = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    current = pd.Timestamp(now or datetime.now(timezone.utc))
    if current.tzinfo is None:
        raise ValueError("now must include timezone")
    current = current.tz_convert("UTC")
    latest_closed = current.floor("min") - pd.Timedelta(minutes=1)
    shift = latest_closed - stamps.max()
    frame["timestamp"] = stamps + shift
    return frame
