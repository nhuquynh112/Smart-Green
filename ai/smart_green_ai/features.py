from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_VERSION = "v1-no-additional-irrigation"
FEATURES = ["soil_pct", "soil_lag_5", "soil_lag_15", "slope_15",
            "temperature_c", "humidity_pct", "minutes_since_water", "hour_sin", "hour_cos"]
REQUIRED = ["timestamp", "device_id", "calibration_id", "data_origin", "soil_pct",
            "temperature_c", "humidity_pct", "minutes_since_water", "water_total_ms"]


def validate(raw: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED) - set(raw.columns))
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if raw.empty:
        raise ValueError("Empty dataset")
    df = raw.copy()
    for key in ["device_id", "calibration_id", "data_origin"]:
        if df[key].isna().any() or df[key].nunique() != 1:
            raise ValueError(f"Use one non-null {key} per dataset")
    if df.data_origin.iloc[0] not in {"real", "synthetic"}:
        raise ValueError("data_origin must be real or synthetic")
    # Reject naive timestamps instead of silently guessing the user's timezone.
    timestamps = [pd.Timestamp(value) for value in df.timestamp]
    if any(pd.isna(t) or t.tzinfo is None for t in timestamps):
        raise ValueError("timestamp requires an explicit UTC offset")
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    df = df.sort_values("timestamp").set_index("timestamp")
    if df.index.has_duplicates:
        raise ValueError("Duplicate timestamps; deduplicate using device/boot/sample identity first")
    if not (df.index == df.index.floor("min")).all():
        raise ValueError("CSV must use exact UTC minute bins; see docs/DATA_AND_AI.md")
    for column in REQUIRED[4:]:
        df[column] = pd.to_numeric(df[column], errors="raise")
        if np.isinf(df[column].to_numpy(dtype=float)).any():
            raise ValueError(f"Infinite values in {column}")
    for column, low, high in [("soil_pct", 0, 100), ("humidity_pct", 0, 100),
                              ("temperature_c", -40, 85), ("minutes_since_water", 0, np.inf),
                              ("water_total_ms", 0, np.inf)]:
        values = df[column].dropna()
        if ((values < low) | (values > high)).any():
            raise ValueError(f"Out-of-range {column}")
    if (df.water_total_ms.dropna().diff().dropna() < 0).any():
        raise ValueError("water_total_ms reset; split the recording into separate sessions")
    # Missing minutes stay missing. Never interpolate over a watering event or outage.
    return df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="min", name="timestamp"))


def feature_frame(grid: pd.DataFrame) -> pd.DataFrame:
    f = grid[["soil_pct", "temperature_c", "humidity_pct", "minutes_since_water"]].copy()
    f["soil_lag_5"] = grid.soil_pct.shift(5)
    f["soil_lag_15"] = grid.soil_pct.shift(15)
    f["slope_15"] = (f.soil_pct - f.soil_lag_15) / 15.0
    hour = grid.index.hour + grid.index.minute / 60.0
    f["hour_sin"] = np.sin(2*np.pi*hour/24)
    f["hour_cos"] = np.cos(2*np.pi*hour/24)
    complete = grid[REQUIRED[4:]].notna().all(axis=1)
    history_ok = complete.rolling(16, min_periods=16).sum().eq(16)
    # Do not extrapolate the sharp wetting transient with a dry-down model.
    dry_history = grid.water_total_ms.eq(grid.water_total_ms.shift(15))
    return f[FEATURES].where(history_ok & dry_history, np.nan)


def supervised(raw: pd.DataFrame, horizon: int = 30) -> tuple[pd.DataFrame, dict]:
    if horizon not in (30, 60):
        raise ValueError("horizon must be 30 or 60 minutes")
    grid = validate(raw)
    f = feature_frame(grid)
    complete = grid[REQUIRED[4:]].notna().all(axis=1)
    future_complete = complete.rolling(horizon+1, min_periods=horizon+1).sum().shift(-horizon).eq(horizon+1)
    no_future_water = grid.water_total_ms.eq(grid.water_total_ms.shift(-horizon))
    f["target"] = grid.soil_pct.shift(-horizon)
    f["label_time"] = grid.index + pd.Timedelta(minutes=horizon)
    rows = f.loc[future_complete & no_future_water].dropna()
    info = {
        "input_rows": len(raw), "grid_minutes": len(grid), "usable_windows": len(rows),
        "missing_minutes": int(grid.device_id.isna().sum()),
        "watering_counter_increments": int((grid.water_total_ms.diff() > 0).sum()),
        "device_id": str(raw.device_id.iloc[0]), "calibration_id": str(raw.calibration_id.iloc[0]),
        "data_origin": str(raw.data_origin.iloc[0]),
        "scope": "Only complete dry history and futures with no additional watering",
    }
    return rows, info


def latest_features(raw: pd.DataFrame) -> pd.DataFrame:
    last = feature_frame(validate(raw)).iloc[[-1]]
    if last.isna().any().any():
        raise ValueError("Need 16 complete consecutive minutes with no watering in the last 15 minutes")
    return last


def chronological_split(rows: pd.DataFrame):
    if len(rows) < 150:
        raise ValueError("Need >=150 usable windows to exercise train/validation/test; this is NOT evidence of sufficient real data")
    a, b = int(len(rows)*0.6), int(len(rows)*0.8)
    val_start, test_start = rows.index[a], rows.index[b]
    train = rows.iloc[:a].loc[lambda x: x.label_time < val_start]
    val = rows.iloc[a:b].loc[lambda x: x.label_time < test_start]
    test = rows.iloc[b:]
    if min(len(train), len(val), len(test)) < 20:
        raise ValueError("Too few windows after purging forecast labels at split boundaries")
    return train, val, test
