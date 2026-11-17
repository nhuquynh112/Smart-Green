"""Offline delta-target experiment. Separate fit/freeze and holdout evaluation commands.

Never imports backend/inference or sends device commands. W04/W05 are never fit.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURES
from .light_features import FEATURES_WITH_LIGHT, light_supervised

VERSION = 'experimental-delta-v1'
BINS = [0, 5, 10, 20, 40, 60, 100]
CANDIDATES = {
    'ridge': [{'alpha': a} for a in (1.0, 10.0, 100.0)],
    'hist_gradient_boosting': [
        {'max_leaf_nodes': n, 'l2_regularization': 10.0} for n in (3, 7)],
    'random_forest': [{'max_depth': d, 'min_samples_leaf': 20} for d in (3, 6)],
}
PROTOCOL = {
    'version': VERSION,
    'fit': ['W01'], 'validation': ['W02', 'W03'], 'holdouts': ['W04', 'W05'],
    'cycles': {'W01': 'C1', 'W02': 'C1', 'W03': 'C1', 'W04': 'C2', 'W05': 'C2'},
    'selection': 'Lowest mean of W02 and W03 MAE, equal session weights; persistence wins exact ties. No refit.',
    'limitations': 'Validation is later time in the SAME C1 cycle, not independent cycle validation. W04/W05 jointly test transfer to C2, not two independent cycles. Previous absolute-model results on W05 were already observed. No new untouched prospective cycle exists.',
    'target': 'soil_future - soil_current; reconstruct current + delta then clip to [0,100]',
    'features': {'control': FEATURES, 'light': FEATURES_WITH_LIGHT},
    'candidates': CANDIDATES, 'seed': 42,
    'moisture_bins_current_soil': BINS,
    'paired_rows': 'Both feature sets use common eligible windows; complete 16-minute history and no watering/missing measurements through forecast horizon.',
    'saturation': 'Retain raw ADC 4095 as censored readings; report exclusion sensitivity, no lux conversion.',
    'automatic_irrigation_approved': False, 'can_trigger_pump': False,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def verify_hashes(hashes):
    for path, expected in hashes.items():
        if digest(path) != expected:
            raise ValueError('Input changed: ' + path)


def delta_target(rows):
    return rows.target - rows.soil_pct


def predict_delta(model, rows, features):
    return np.clip(rows.soil_pct.to_numpy() + model.predict(rows[features]), 0, 100)


def estimator(kind, params):
    if kind == 'ridge':
        return make_pipeline(StandardScaler(), Ridge(**params))
    if kind == 'hist_gradient_boosting':
        # Disable internal random validation split: session validation is external.
        return HistGradientBoostingRegressor(max_iter=100, learning_rate=0.05,
                                            min_samples_leaf=20, early_stopping=False,
                                            random_state=42, **params)
    if kind == 'random_forest':
        return RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=1, **params)
    raise ValueError('Unknown model ' + kind)


def checked_rows(raw, horizon):
    rows, quality = light_supervised(raw, horizon)
    if len(rows) < 20:
        raise ValueError('Need at least 20 complete common windows')
    if quality['data_origin'] != 'real':
        raise ValueError('This experiment requires real reviewed data')
    return rows, quality


def check_split(earlier, later):
    # Purge entire lag/label support, not just prediction timestamps.
    if earlier.label_time.max() >= later.index.min() - pd.Timedelta(minutes=15):
        raise ValueError('Overlapping feature/label support between sessions')


def check_identity(a, b):
    for field in ('device_id', 'calibration_id', 'data_origin', 'time_basis'):
        if a[field] != b[field]:
            raise ValueError('Dataset identity mismatch: ' + field)


def mae(actual, predicted):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def fit(data_dir, output):
    """This phase deliberately reads ONLY W01/W02/W03, never W04 or W05."""
    data_dir, output = Path(data_dir), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'protocol.json', PROTOCOL)
    paths = {s: data_dir/f'{s}-minutes.csv' for s in ('W01', 'W02', 'W03')}
    hashes = {str(p): digest(p) for p in paths.values()}
    data = {s: pd.read_csv(p) for s, p in paths.items()}
    results = []
    for h in (30, 60):
        parts, quality = {}, {}
        for s, raw in data.items():
            parts[s], quality[s] = checked_rows(raw, h)
            check_identity(quality['W01'], quality[s])
        check_split(parts['W01'], parts['W02'])
        check_split(parts['W02'], parts['W03'])
        train = parts['W01']
        validation = {s: p for s, p in parts.items() if s != 'W01'}
        baseline = {s: mae(p.target, p.soil_pct) for s, p in validation.items()}
        choices = {'persistence': float(np.mean(list(baseline.values())))}
        grid, selected = {}, {}
        dest = output/f'horizon-{h}'
        dest.mkdir()
        for light, features in PROTOCOL['features'].items():
            for kind, candidates in CANDIDATES.items():
                key = kind + '_' + light
                grid[key] = []
                fitted = []
                for params in candidates:
                    model = estimator(kind, params)
                    model.fit(train[features], delta_target(train))
                    scores = {s: mae(p.target, predict_delta(model, p, features))
                              for s, p in validation.items()}
                    score = float(np.mean(list(scores.values())))
                    grid[key].append({'params': params, 'mae_by_session': scores, 'mean_mae': score})
                    fitted.append(model)
                best = min(range(len(candidates)), key=lambda i: grid[key][i]['mean_mae'])
                selected[key] = grid[key][best]
                choices[key] = grid[key][best]['mean_mae']
                joblib.dump({'model': fitted[best], 'metadata': {
                    'version': VERSION, 'horizon': h, 'features': features,
                    'target': 'delta', 'params': candidates[best],
                    'can_trigger_pump': False, 'automatic_irrigation_approved': False,
                }}, dest/f'{key}.joblib')
        ranges = {f: [float(train[f].min()), float(train[f].max())]
                  for f in FEATURES_WITH_LIGHT + ['target']}
        ranges['delta'] = [float(delta_target(train).min()), float(delta_target(train).max())]
        result = {'horizon': h, 'quality': quality, 'grid': grid, 'selected_parameters': selected,
                  'validation_persistence': baseline, 'validation_scores': choices,
                  'selected_on_validation': min(choices, key=choices.get),
                  'fit_ranges': ranges,
                  'split': {s: {'rows': len(p), 'first_feature': p.index.min().isoformat(),
                                'last_label': p.label_time.max().isoformat()} for s, p in parts.items()}}
        results.append(result)
    verify_hashes(hashes)
    frozen = {'protocol': PROTOCOL, 'input_sha256': hashes, 'results': results,
              'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__,
                           'numpy': np.__version__, 'pandas': pd.__version__, 'joblib': joblib.__version__},
              'model_sha256': {str(p): digest(p) for p in sorted(output.glob('horizon-*/*.joblib'))}}
    write_json(output/'frozen.json', frozen)
    return frozen


def range_diagnostics(rows, fit_ranges):
    values = {f: rows[f] for f in FEATURES_WITH_LIGHT + ['target']}
    values['delta'] = delta_target(rows)
    return {f: {'fit_min': lo, 'fit_max': hi, 'test_min': float(values[f].min()),
                'test_max': float(values[f].max()),
                'outside_rows': int(((values[f] < lo) | (values[f] > hi)).sum()),
                'outside_percent': float(((values[f] < lo) | (values[f] > hi)).mean()*100)}
            for f, (lo, hi) in fit_ranges.items()}


def score_table(pred, keys):
    return {key: {'mae_pp': mae(pred.target, pred[key]),
                  'bias_pp': float((pred[key]-pred.target).mean()),
                  'improvement_vs_persistence_pp': mae(pred.target, pred.persistence)-mae(pred.target, pred[key])}
            for key in keys}


def evaluate(frozen_dir, w04, w05, output, old_models):
    """Only predict with previously frozen estimators. No fitting or test selection."""
    frozen_dir, output, old_models = Path(frozen_dir), Path(output), Path(old_models)
    freeze_path = frozen_dir/'frozen.json'
    freeze_hash = digest(freeze_path)
    frozen = json.loads(freeze_path.read_text())
    if frozen['protocol'] != PROTOCOL:
        raise ValueError('Frozen protocol does not match this evaluator')
    verify_hashes(frozen['input_sha256'])
    verify_hashes(frozen['model_sha256'])
    paths = {'W04': Path(w04), 'W05': Path(w05)}
    hashes = {str(p): digest(p) for p in paths.values()}
    hashes[str(freeze_path)] = freeze_hash
    # Existing absolute RF light experiment: paired comparator, not the earlier W01-only candidate.
    for h in (30, 60):
        for variant in ('control', 'light'):
            p = old_models/f'horizon-{h}'/f'random_forest_{variant}.joblib'
            hashes[str(p)] = digest(p)
    data = {s: pd.read_csv(p) for s, p in paths.items()}
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for fitted in frozen['results']:
        h = fitted['horizon']
        previous = None
        for session, raw in data.items():
            rows, quality = checked_rows(raw, h)
            check_identity(fitted['quality']['W01'], quality)
            val_end = max(pd.Timestamp(p['last_label']) for p in fitted['split'].values())
            if rows.index.min()-pd.Timedelta(minutes=15) <= val_end:
                raise ValueError('Holdout overlaps fit/validation support')
            if previous is not None:
                check_split(previous, rows)
            previous = rows
            pred = pd.DataFrame({'timestamp': rows.index, 'label_time': rows.label_time.to_numpy(),
                                 'soil_current': rows.soil_pct.to_numpy(), 'target': rows.target.to_numpy(),
                                 'persistence': rows.soil_pct.to_numpy()})
            for key in fitted['selected_parameters']:
                bundle = joblib.load(frozen_dir/f'horizon-{h}'/f'{key}.joblib')
                meta = bundle['metadata']
                features = PROTOCOL['features'][key.rsplit('_', 1)[1]]
                if (meta['version'] != VERSION or meta['horizon'] != h or meta['target'] != 'delta'
                        or meta['features'] != features or meta['can_trigger_pump']
                        or meta['automatic_irrigation_approved']):
                    raise ValueError('Bad delta bundle contract')
                pred[key] = predict_delta(bundle['model'], rows, features)
            for variant in ('control', 'light'):
                bundle = joblib.load(old_models/f'horizon-{h}'/f'random_forest_{variant}.joblib')
                meta = bundle['metadata']
                if meta['horizon_minutes'] != h or meta['features'] != PROTOCOL['features'][variant]:
                    raise ValueError('Bad absolute comparator contract')
                check_identity(meta['counts'][meta['fit_session']], quality)
                pred['absolute_rf_'+variant] = np.clip(bundle['model'].predict(rows[meta['features']]), 0, 100)
            keys = list(pred.columns[4:])
            bins = []
            for lo, hi in zip(BINS[:-1], BINS[1:]):
                mask = (pred.soil_current >= lo) & ((pred.soil_current <= hi) if hi == 100 else (pred.soil_current < hi))
                subset = pred[mask]
                bins.append({'current_soil_range': f'[{lo},{hi}{"]" if hi == 100 else ")"}',
                             'rows': len(subset), 'scores': score_table(subset, keys) if len(subset) else None})
            # Forecast windows that do not overlap; fixed first eligible anchor. Descriptive only.
            chosen, next_time = [], rows.index.min()
            for i, t in enumerate(rows.index):
                if t >= next_time:
                    chosen.append(i)
                    next_time = t + pd.Timedelta(minutes=h+16)
            no_sat, _ = light_supervised(raw, h, exclude_saturated=True)
            saturated_subset = pred[pd.to_datetime(pred.timestamp, utc=True).isin(no_sat.index)]
            report = {'session': session, 'horizon': h, 'windows': len(rows), 'quality': quality,
                      'selected_before_holdout': fitted['selected_on_validation'],
                      'scores': score_table(pred, keys), 'moisture_bins': bins,
                      'ranges': range_diagnostics(rows, fitted['fit_ranges']),
                      'nonoverlapping_support': {'rows': len(chosen), 'scores': score_table(pred.iloc[chosen], keys)},
                      'without_saturated_history': {'rows': len(saturated_subset),
                          'scores': score_table(saturated_subset, keys) if len(saturated_subset) else None}}
            reports.append(report)
            pred.to_csv(output/f'{session}-predictions-{h}.csv', index=False)
    verify_hashes(hashes)
    verify_hashes(frozen['input_sha256'])
    verify_hashes(frozen['model_sha256'])
    report = {'version': VERSION, 'protocol': PROTOCOL, 'input_sha256': hashes,
              'results': reports, 'promote': False, 'can_trigger_pump': False,
              'note': 'Report all predeclared families. Do not choose a new winner from W05; validation selection remains frozen.'}
    write_json(output/'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('fit')
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('evaluate')
    p.add_argument('--frozen-dir', type=Path, required=True)
    p.add_argument('--w04', type=Path, required=True)
    p.add_argument('--w05', type=Path, required=True)
    p.add_argument('--old-models', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop('command')
    result = fit(**args) if command == 'fit' else evaluate(**args)
    print(json.dumps({'phase': command, 'results': [
        {k: r[k] for k in ('session', 'horizon', 'selected_on_validation', 'selected_before_holdout', 'scores') if k in r}
        for r in result['results']]}, indent=2))


if __name__ == '__main__':
    main()
