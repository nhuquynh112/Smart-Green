"""Evaluate frozen light/control bundles on a reviewed minute dataset. Never fits."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import FEATURES
from .light_features import FEATURES_WITH_LIGHT, FEATURE_VERSION, light_supervised


def evaluate(data, model_dir, output):
    data, model_dir, output = Path(data), Path(model_dir), Path(output)
    raw = pd.read_csv(data)
    results = []
    predictions = {}
    hashes = {str(data): hashlib.sha256(data.read_bytes()).hexdigest()}
    for horizon in (30, 60):
        rows, quality = light_supervised(raw, horizon)
        if rows.empty:
            raise ValueError('No eligible windows: review watering history, coverage and sensor validity; do not fabricate missing features')
        pred = pd.DataFrame({'timestamp': rows.index, 'label_time': rows.label_time.to_numpy(),
                             'target': rows.target.to_numpy()})
        for kind in ('linear_regression', 'random_forest'):
            for light in (False, True):
                name = kind + ('_light' if light else '_control')
                path = model_dir / f'horizon-{horizon}' / f'{name}.joblib'
                hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
                bundle = joblib.load(path)
                meta = bundle['metadata']
                features = FEATURES_WITH_LIGHT if light else FEATURES
                if (meta['feature_version'] != FEATURE_VERSION or meta['horizon_minutes'] != horizon
                        or meta['features'] != features or meta['automatic_irrigation_approved']):
                    raise ValueError('Unexpected bundle contract')
                fit_quality = meta['counts'][meta['fit_session']]
                for field in ('device_id', 'calibration_id', 'data_origin', 'time_basis'):
                    if quality[field] != fit_quality[field]:
                        raise ValueError('Holdout identity/time basis mismatch: ' + field)
                fit_end = pd.Timestamp(meta['split'][meta['fit_session']]['last_label'])
                validation_end = max(pd.Timestamp(meta['split'][s]['last_label'])
                                     for s in meta['validation_sessions'])
                if rows.index.min() <= max(fit_end, validation_end):
                    raise ValueError('Holdout overlaps training/validation timeline')
                for source, expected in meta['input_sha256'].items():
                    if hashlib.sha256(Path(source).read_bytes()).hexdigest() != expected:
                        raise ValueError('Frozen model source changed: ' + source)
                pred[name] = np.clip(bundle['model'].predict(rows[features]), 0, 100)
        pred['persistence'] = rows.soil_pct.to_numpy()
        pred['linear_extrapolation'] = np.clip(rows.soil_pct + rows.slope_15*horizon, 0, 100).to_numpy()
        scores = {k: float(np.abs(pred[k]-pred.target).mean()) for k in pred.columns[3:]}
        results.append({'horizon_minutes': horizon, 'windows': len(rows), 'quality': quality,
                        'mae_pp': scores, 'first_feature': rows.index.min().isoformat(),
                        'last_label': rows.label_time.max().isoformat(),
                        'same_test_rows_for_all_models': True})
        predictions[horizon] = pred
    # Validate everything before creating output. Never overwrite an earlier evaluation.
    output.mkdir(parents=True, exist_ok=False)
    for horizon, pred in predictions.items():
        pred.to_csv(output / f'predictions-{horizon}.csv', index=False)
    report = {'policy': 'Frozen W01-fit models; no fit/tuning/selection on this holdout',
              'results': results, 'input_sha256': hashes, 'can_trigger_pump': False,
              'limitations': 'Overlapping windows are not independent repetitions; same plant; watering history must be reviewed before constructing input.'}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    for source, expected in hashes.items():
        assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == expected
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--models', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.data, args.models, args.output), indent=2))
