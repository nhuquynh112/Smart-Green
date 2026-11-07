from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from .features import FEATURES, FEATURE_VERSION, chronological_split, supervised


def predictions(name, estimator, rows, horizon):
    if name == "persistence":
        values = rows.soil_pct.to_numpy()
    elif name == "linear_extrapolation":
        values = (rows.soil_pct + rows.slope_15*horizon).to_numpy()
    else:
        values = estimator.predict(rows[FEATURES])
    return np.clip(values, 0, 100)


def train(csv_path: Path, output: Path, horizon: int = 30):
    raw = pd.read_csv(csv_path)
    rows, quality = supervised(raw, horizon)
    fit, val, test = chronological_split(rows)
    models = {"persistence": None, "linear_extrapolation": None,
              "linear_regression": LinearRegression(),
              "random_forest": RandomForestRegressor(n_estimators=150, max_depth=8,
                                                       min_samples_leaf=10, random_state=42, n_jobs=1)}
    for model in models.values():
        if model is not None:
            model.fit(fit[FEATURES], fit.target)
    validation = {name: float(mean_absolute_error(val.target, predictions(name, model, val, horizon)))
                  for name, model in models.items()}
    selected = min(validation, key=validation.get)  # baseline may legitimately win
    test_mae = {}
    falling = test.target < test.soil_pct
    falling_mae = {}
    exported = pd.DataFrame({"timestamp": test.index, "target": test.target.to_numpy()})
    for name, model in models.items():
        pred = predictions(name, model, test, horizon)
        test_mae[name] = float(mean_absolute_error(test.target, pred))
        falling_mae[name] = (float(mean_absolute_error(test.target[falling], pred[falling.to_numpy()]))
                             if falling.any() else None)
        exported[name] = pred
    versions = {"python": platform.python_version(), "numpy": np.__version__,
                "pandas": pd.__version__, "sklearn": sklearn.__version__, "joblib": joblib.__version__}
    report = {
        "feature_version": FEATURE_VERSION, "features": FEATURES, "horizon_minutes": horizon,
        "quality": quality, "versions": versions,
        "dataset_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "split": {name: {"rows": len(part), "first": part.index.min().isoformat(),
                           "last": part.index.max().isoformat(), "last_label": part.label_time.max().isoformat()}
                  for name, part in [("train", fit), ("validation", val), ("test", test)]},
        "validation_mae_percentage_points": validation, "test_mae_percentage_points": test_mae,
        "falling_soil_test": {
            "definition": "target_soil_pct < current_soil_pct within complete no-additional-watering windows",
            "rows": int(falling.sum()), "mae_percentage_points": falling_mae,
            "limitation": "Retrospective subset based on observed target; not a runtime trigger or independent cycle count",
        },
        "selected_by_validation": selected, "automatic_irrigation_approved": False,
        "limitations": ["Conditional dry-down evaluation only; not overall control effectiveness",
                        "Time-correlated windows are not independent trials",
                        "Real hardware evaluation and manual promotion review are required"],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output/"report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    exported.to_csv(output/"test_predictions.csv", index=False)
    joblib.dump({"model": models[selected], "metadata": report}, output/"candidate.joblib")
    return report


def main():
    parser = argparse.ArgumentParser(description="Offline candidate training; never authorizes pump control")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/candidate"))
    parser.add_argument("--horizon", type=int, choices=[30, 60], default=30)
    args = parser.parse_args()
    print(json.dumps(train(args.csv, args.output, args.horizon), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
