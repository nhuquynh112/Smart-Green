"""Delta target/reconstruction, causal inputs and split/freeze regression tests."""
import json

import numpy as np
import pandas as pd
import pytest

from smart_green_ai import delta_experiment as experiment
from smart_green_ai.features import FEATURES
from smart_green_ai.light_features import FEATURES_WITH_LIGHT, light_supervised
from smart_green_ai.simulate import generate


def test_delta_reconstruction_and_clipping():
    rows = pd.DataFrame({'soil_pct': [3., 90., 1.], 'target': [2., 100., 0.]})
    np.testing.assert_allclose(experiment.delta_target(rows), [-1, 10, -1])
    class Model:
        def predict(self, x):
            return [-1., 30., -4.]
    np.testing.assert_allclose(experiment.predict_delta(Model(), rows, ['soil_pct']), [2, 100, 0])


@pytest.mark.parametrize('horizon', [30, 60])
def test_future_changes_do_not_enter_features_and_watering_is_excluded(horizon):
    raw = generate(2)
    raw['light_raw'] = 900.
    raw['light_saturated'] = False
    rows, _ = light_supervised(raw, horizon)
    t = rows.index[40]
    times = pd.to_datetime(raw.timestamp, utc=True)
    changed = raw.copy()
    future = times > t
    changed.loc[future, 'soil_pct'] = 80.
    changed.loc[future, 'light_raw'] = 4000.
    changed.loc[future, 'temperature_c'] = 40.
    after, _ = light_supervised(changed, horizon)
    pd.testing.assert_series_equal(rows.loc[t, FEATURES_WITH_LIGHT], after.loc[t, FEATURES_WITH_LIGHT])
    assert rows.loc[t, 'target'] != after.loc[t, 'target']
    watered = raw.copy()
    watered.loc[times >= t + pd.Timedelta(minutes=1), 'water_event_count'] += 1
    assert t not in light_supervised(watered, horizon)[0].index


def test_split_checks_full_history_label_support():
    earlier = pd.DataFrame({'label_time': [pd.Timestamp('2026-01-01T01:00Z')]})
    later = pd.DataFrame(index=[pd.Timestamp('2026-01-01T01:15Z')])
    with pytest.raises(ValueError, match='Overlapping'):
        experiment.check_split(earlier, later)
    later.index += pd.Timedelta(minutes=1)
    experiment.check_split(earlier, later)


def test_models_disable_random_validation_and_ridge_scales_train_only():
    model = experiment.estimator('hist_gradient_boosting', experiment.CANDIDATES['hist_gradient_boosting'][0])
    assert model.early_stopping is False
    ridge = experiment.estimator('ridge', {'alpha': 1.0})
    assert 'standardscaler' in ridge.named_steps


def test_fit_never_reads_holdouts_and_outputs_cannot_be_overwritten(tmp_path, monkeypatch):
    # A tiny deterministic estimator makes the protocol test independent of estimator speed.
    from sklearn.dummy import DummyRegressor
    monkeypatch.setattr(experiment, 'estimator', lambda *args: DummyRegressor())
    monkeypatch.setattr(experiment, 'CANDIDATES', {'ridge': [{'alpha': 1.0}]})
    data = tmp_path/'data'
    data.mkdir()
    for i, session in enumerate(('W01', 'W02', 'W03')):
        raw = generate(2).iloc[:300].copy()
        raw['timestamp'] = pd.to_datetime(raw.timestamp, utc=True) + pd.Timedelta(days=i*3)
        raw['data_origin'] = 'real'
        raw['light_raw'] = 900.
        raw['light_saturated'] = False
        raw.to_csv(data/f'{session}-minutes.csv', index=False)
    # Deliberately invalid holdout: fit must not read it at all.
    (data/'W04-minutes.csv').write_text('not a dataset')
    output = tmp_path/'fit'
    result = experiment.fit(data, output)
    assert len(result['input_sha256']) == 3
    assert all('W04' not in p and 'W05' not in p for p in result['input_sha256'])
    assert set(result['results'][0]['quality']) == {'W01', 'W02', 'W03'}
    with pytest.raises(FileExistsError):
        experiment.fit(data, output)
    (data/'W01-minutes.csv').write_text('changed')
    with pytest.raises(ValueError, match='Input changed'):
        experiment.verify_hashes(result['input_sha256'])


def test_evaluation_uses_frozen_models_without_fit(tmp_path, monkeypatch):
    import joblib
    from sklearn.dummy import DummyRegressor
    monkeypatch.setattr(experiment, 'estimator', lambda *args: DummyRegressor())
    monkeypatch.setattr(experiment, 'CANDIDATES', {'ridge': [{'alpha': 1.0}]})
    data = tmp_path/'data'
    data.mkdir()
    raw_by_session = {}
    for i, session in enumerate(('W01', 'W02', 'W03', 'W04', 'W05')):
        raw = generate(2).iloc[:300].copy()
        raw['timestamp'] = pd.to_datetime(raw.timestamp, utc=True) + pd.Timedelta(days=i*3)
        raw['data_origin'] = 'real'
        raw['light_raw'] = 900.
        raw['light_saturated'] = False
        raw.to_csv(data/f'{session}-minutes.csv', index=False)
        raw_by_session[session] = raw
    frozen = tmp_path/'frozen'
    fitted = experiment.fit(data, frozen)
    old = tmp_path/'old'
    for h in (30, 60):
        rows, quality = experiment.checked_rows(raw_by_session['W01'], h)
        dest = old/f'horizon-{h}'
        dest.mkdir(parents=True)
        for variant, features in experiment.PROTOCOL['features'].items():
            model = DummyRegressor().fit(rows[features], rows.target)
            joblib.dump({'model': model, 'metadata': {'horizon_minutes': h,
                'features': features, 'counts': {'W01': quality}, 'fit_session': 'W01'}},
                dest/f'random_forest_{variant}.joblib')
    def forbidden(*args, **kwargs):
        raise AssertionError('Evaluation must never fit a model')
    monkeypatch.setattr(DummyRegressor, 'fit', forbidden)
    result = experiment.evaluate(frozen, data/'W04-minutes.csv', data/'W05-minutes.csv',
                                 tmp_path/'evaluation', old)
    assert len(result['results']) == 4
    assert result['promote'] is False
    for row in result['results']:
        assert sum(b['rows'] for b in row['moisture_bins']) == row['windows']
        assert row['selected_before_holdout'] == next(
            f['selected_on_validation'] for f in fitted['results'] if f['horizon'] == row['horizon'])
    model_path = next(frozen.glob('horizon-*/*.joblib'))
    model_path.write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='Input changed'):
        experiment.evaluate(frozen, data/'W04-minutes.csv', data/'W05-minutes.csv',
                            tmp_path/'should-not-exist', old)
    assert not (tmp_path/'should-not-exist').exists()
