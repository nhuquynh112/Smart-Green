"""Experimental causal ADC features. Does not alter the production v2 contract."""
import numpy as np
import pandas as pd
from .features import FEATURES, supervised, validate

FEATURE_VERSION = 'experimental-v3-light-adc'
LIGHT_FEATURES = ['light_raw', 'light_lag_5', 'light_lag_15', 'light_mean_15', 'light_slope_15']
FEATURES_WITH_LIGHT = FEATURES + LIGHT_FEATURES


def augment_minutes(base, telemetry):
    """Join closed-minute ADC to an already reviewed dataset; never fill missing ADC."""
    frame = pd.DataFrame(telemetry).copy()
    frame['timestamp'] = pd.to_datetime(frame['timestamp'], utc=True)
    frame = frame.dropna(subset=['timestamp'])
    frame['minute'] = frame.timestamp.dt.floor('min')
    def adc(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return np.nan
        return float(value) if np.isfinite(value) and 0 <= value <= 4095 else np.nan
    frame['adc'] = frame.get('light_raw', pd.Series(index=frame.index, dtype=float)).map(adc)
    group = frame.groupby('minute')['adc']
    median = group.median().where(group.count().eq(group.size()))
    result = base.copy()
    times = pd.to_datetime(result.timestamp, utc=True)
    result['light_raw'] = times.map(median)
    result['light_saturated'] = times.map(group.apply(lambda x: bool((x == 4095).any())))
    return result


def light_supervised(raw, horizon=30, exclude_saturated=False):
    rows, quality = supervised(raw, horizon)
    grid = validate(raw)
    light = pd.to_numeric(grid['light_raw'], errors='coerce')
    light = light.where(np.isfinite(light) & light.between(0, 4095))
    if exclude_saturated:
        light = light.mask(grid['light_saturated'].fillna(False).astype(bool))
    features = pd.DataFrame(index=grid.index)
    features['light_raw'] = light
    features['light_lag_5'] = light.shift(5)
    features['light_lag_15'] = light.shift(15)
    features['light_mean_15'] = light.rolling(15, min_periods=15).mean()
    features['light_slope_15'] = (light-light.shift(15))/15
    # Require complete causal history, including samples between lag endpoints.
    features = features.where(light.notna().rolling(16, min_periods=16).sum().eq(16), np.nan)
    common = rows.join(features).dropna(subset=LIGHT_FEATURES)
    return common, {**quality, 'v2_windows': len(rows), 'common_windows': len(common),
                    'excluded_for_light': len(rows)-len(common), 'exclude_saturated': exclude_saturated}
