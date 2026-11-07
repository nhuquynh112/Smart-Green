"""Audit an input CSV before training; never infer missing measurement/watering data."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from .features import REQUIRED, chronological_split, supervised


def assess(raw: pd.DataFrame, horizon: int = 30) -> dict:
    if horizon not in (30, 60):
        raise ValueError('horizon must be 30 or 60')
    missing_columns = sorted(set(REQUIRED) - set(raw.columns))
    missing_values = {k: int(raw[k].isna().sum()) for k in REQUIRED if k in raw}
    report = {
        'input_rows': len(raw), 'horizon_minutes': horizon,
        'missing_columns': missing_columns, 'missing_values': missing_values,
        'training_pipeline_ready': False, 'real_world_evidence_sufficient': False,
        'automatic_irrigation_approved': False,
        'blockers': [], 'warnings': [], 'next_actions': [],
    }
    if raw.empty:
        report['blockers'].append('Empty dataset')
    if missing_columns:
        report['blockers'].append('Missing required columns: ' + ', '.join(missing_columns))
    if 'timestamp' not in raw or raw.timestamp.isna().any():
        report['next_actions'].append('Collect timezone-aware measurement timestamps; received_at remains separate. Do not backfill historical measurement time with current time.')
    if 'soil_pct' not in raw or raw.soil_pct.isna().any():
        report['next_actions'].append('Calibrate soil using real dry/wet reference soil and collect valid soil_pct with a stable calibration_id.')
    if any(k not in raw or raw[k].isna().any() for k in ('minutes_since_water', 'water_total_ms')):
        report['next_actions'].append('Collect complete watering events to derive cumulative actual pump time and minutes since watering. Unknown stays missing, not zero.')
    if 'received_at' in raw:
        report['warnings'].append('Laptop received_at is not automatically substituted for device timestamp.')
    if report['blockers']:
        return report
    try:
        rows, quality = supervised(raw, horizon)
        report['quality'] = quality
        train, val, test = chronological_split(rows)
        report['split_rows'] = {'train': len(train), 'validation': len(val), 'test': len(test)}
        report['training_pipeline_ready'] = True
    except (ValueError, TypeError) as exc:
        report['blockers'].append(str(exc))
    report['warnings'].append('Passing pipeline checks does not establish enough independent drying/watering cycles for scientific evaluation.')
    if 'data_origin' in raw and 'synthetic' in raw.data_origin.values:
        report['warnings'].append('SYNTHETIC data: software verification only, not measured AI performance.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--horizon', type=int, choices=[30,60], default=30)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = assess(pd.read_csv(args.csv), args.horizon)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
