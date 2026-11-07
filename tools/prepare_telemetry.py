"""Validate bench JSONL/logs and export CSV + quality report without fabricating time."""
import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path


SENSOR_FIELDS = ('soil_pct', 'temperature_c', 'humidity_pct', 'light_lux')
TIME_FIELDS = ('timestamp', 'received_at')


def strict_json(line):
    def reject_constant(value):
        raise ValueError('non-finite JSON constant: ' + value)

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('non-finite JSON number')
        return result

    return json.loads(line, parse_constant=reject_constant, parse_float=finite_float, object_pairs_hook=unique_keys)


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError('timestamp must be a string or null')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.utcoffset() is None:
        raise ValueError('timezone required')
    return result


def validate(r):
    if not isinstance(r, dict):
        raise ValueError('not an object')
    for k in ('device_id', 'boot_id', 'calibration_id', 'data_origin'):
        if not isinstance(r.get(k), str) or not r[k]:
            raise ValueError('missing/string: ' + k)
    for k in ('sample_seq', 'uptime_ms', 'soil_raw', 'light_raw'):
        if type(r.get(k)) is not int or r[k] < 0:
            raise ValueError('invalid integer: ' + k)
    if r['sample_seq'] == 0 or r['soil_raw'] > 4095 or r['light_raw'] > 4095:
        raise ValueError('sequence/ADC range')
    for k in ('soil_valid', 'air_valid', 'tank_ok', 'pump_on'):
        if type(r.get(k)) is not bool:
            raise ValueError('invalid boolean: ' + k)
    for k in SENSOR_FIELDS:
        if k not in r:
            raise ValueError('missing field: ' + k)
        v = r[k]
        if v is not None and (type(v) not in (int, float) or not math.isfinite(v)):
            raise ValueError('invalid number: ' + k)
    for k in ('soil_pct', 'humidity_pct'):
        if r.get(k) is not None and not 0 <= r[k] <= 100:
            raise ValueError('range: ' + k)
    if r['soil_valid'] != (r.get('soil_pct') is not None):
        raise ValueError('soil validity mismatch')
    if r['air_valid'] != (r.get('temperature_c') is not None and r.get('humidity_pct') is not None):
        raise ValueError('air validity mismatch')
    if not r['air_valid'] and (r['temperature_c'] is not None or r['humidity_pct'] is not None):
        raise ValueError('invalid air readings must both be null')
    if r['light_lux'] is not None and r['light_lux'] < 0:
        raise ValueError('negative light_lux')
    if r['data_origin'] not in ('real', 'synthetic'):
        raise ValueError('invalid data_origin')
    timestamp(r.get('timestamp'))
    timestamp(r.get('received_at'))


def _lines(paths):
    for path in paths:
        with Path(path).open(encoding='utf-8', errors='replace') as source:
            for number, line in enumerate(source, 1):
                yield str(path), number, line


def prepare(path):
    rows, seen, last = [], {}, {}
    errors, gaps, time_issues = [], [], []
    duplicates = 0
    paths = [path] if isinstance(path, (str, Path)) else list(path)
    for source, number, line in _lines(paths):
        if not line.strip():
            continue
        try:
            r = strict_json(line)
            validate(r)
        except (ValueError, TypeError, AttributeError) as exc:
            errors.append({'source': source, 'line': number, 'reason': str(exc)[:120]})
            continue
        key = (r['device_id'], r['boot_id'], r['sample_seq'])
        if key in seen:
            # Reception time may differ when the same telemetry is replayed.
            payload = lambda x: {k: v for k, v in x.items() if k != 'received_at'}
            if payload(r) != payload(seen[key]):
                errors.append({'source': source, 'line': number, 'reason': 'conflicting duplicate identity'})
            else:
                duplicates += 1
            continue
        session = key[:2]
        previous = last.get(session)
        if previous:
            delta = r['sample_seq'] - previous['sample_seq']
            if delta != 1:
                gaps.append({'source': source, 'line': number, 'previous_seq': previous['sample_seq'], 'seq': r['sample_seq'], 'missing': max(0, delta-1)})
            if r['uptime_ms'] <= previous['uptime_ms']:
                time_issues.append({'source': source, 'line': number, 'reason': 'uptime reversed/wrapped'})
            a, b = timestamp(previous.get('received_at')), timestamp(r.get('received_at'))
            if a and b and b < a:
                time_issues.append({'source': source, 'line': number, 'reason': 'received_at reversed'})
        seen[key] = r
        last[session] = r
        rows.append(r)
    columns = list(dict.fromkeys(k for r in rows for k in r))
    report = {
        'source': str(path), 'sources': [str(p) for p in paths], 'accepted': len(rows), 'duplicates_removed': duplicates,
        'rejected': errors, 'sequence_issues': gaps, 'time_issues': time_issues,
        'sessions': len(last),
        'missing': {k: sum(r.get(k) is None for r in rows) for k in dict.fromkeys([*columns, *TIME_FIELDS])},
        'soil_valid_counts': dict(Counter(str(r['soil_valid']) for r in rows)),
        'ai_ready': False,
        'note': 'Bench export only. received_at is laptop reception time, not device measurement time. AI needs calibrated soil and complete watering history.'
    }
    return rows, columns, report


def export(rows, columns, report, prefix):
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with prefix.with_suffix('.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    prefix.with_suffix('.quality.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    # A fixed schema staging CSV for PostgreSQL; preserve the complete payload.
    with prefix.with_suffix('.postgres.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['device_id','boot_id','sample_seq','measured_at','received_at','payload'])
        for r in rows:
            writer.writerow([r['device_id'],r['boot_id'],r['sample_seq'],r.get('timestamp'),r.get('received_at'),json.dumps(r,allow_nan=False)])
    return prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, nargs='+')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    prefix = args.output_dir / (args.input[0].stem if len(args.input) == 1 else 'combined')
    outputs = [prefix.with_suffix(s).resolve() for s in ('.csv', '.quality.json', '.postgres.csv')]
    if any(p.resolve() in outputs for p in args.input):
        parser.error('output would overwrite an input file')
    rows, columns, report = prepare(args.input)
    export(rows, columns, report, prefix)
    print(json.dumps({'accepted':len(rows),'rejected':len(report['rejected']), 'output_prefix':str(prefix)},ensure_ascii=False))


if __name__ == '__main__':
    main()
