from __future__ import annotations

import pandas as pd
from .features import FEATURE_VERSION, latest_features
from .train import predictions


def predict(bundle: dict, recent: pd.DataFrame, now: str) -> dict:
    """TV2 calls this with an already-loaded trusted bundle and UTC minute data.

    This function returns advice only, never a pump command.
    """
    meta = bundle["metadata"]
    if meta["feature_version"] != FEATURE_VERSION:
        raise ValueError("Feature version mismatch")
    x = latest_features(recent)
    current = pd.Timestamp(now)
    if current.tzinfo is None:
        raise ValueError("now must include timezone")
    age = (current-(x.index[-1] + pd.Timedelta(minutes=1))).total_seconds()
    if not 0 <= age <= 120:
        raise ValueError("Stale or incomplete/future minute data")
    for key in ("device_id", "calibration_id", "data_origin"):
        if str(recent[key].iloc[0]) != meta["quality"][key]:
            raise ValueError(f"Model/data {key} mismatch")
    basis = str(recent.time_basis.iloc[0]) if 'time_basis' in recent else 'device_timestamp'
    if basis != meta['quality'].get('time_basis', 'device_timestamp'):
        raise ValueError('Model/data time_basis mismatch')
    name = meta["selected_by_validation"]
    value = float(predictions(name, bundle["model"], x, meta["horizon_minutes"])[0])
    return {"predicted_soil_pct": value, "horizon_minutes": meta["horizon_minutes"],
            "as_of": x.index[-1].isoformat(), "model": name, "time_basis": basis,
            "available_at": (x.index[-1] + pd.Timedelta(minutes=1)).isoformat(),
            "conditional_on": "no_additional_irrigation", "can_trigger_pump": False}
