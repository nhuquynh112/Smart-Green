"""Maintain an explicit watering-history journal; never operate hardware."""
import argparse
import json
import math
from pathlib import Path
from prepare_telemetry import strict_json, timestamp


def instant(value):
    result = timestamp(value)
    if result is None:
        raise ValueError('A timezone-aware timestamp is required')
    return result


def validate_journal(j):
    if not isinstance(j, dict) or j.get('schema_version') != 1:
        raise ValueError('Expected journal schema_version=1')
    for key in ('device_id', 'calibration_id'):
        if not isinstance(j.get(key), str) or not j[key].strip():
            raise ValueError('Missing ' + key)
    if j.get('data_origin') not in ('real', 'synthetic'):
        raise ValueError('Invalid data_origin')
    start, end = instant(j.get('coverage_start')), instant(j.get('coverage_end'))
    if start >= end or type(j.get('history_complete')) is not bool:
        raise ValueError('Invalid coverage interval/history_complete')
    previous = j.get('last_watered_at_before_start')
    if previous is not None and instant(previous) > start:
        raise ValueError('Previous watering must end at or before coverage_start')
    ids, events = set(), []
    if not isinstance(j.get('events'), list) or not isinstance(j.get('unknown_intervals'), list):
        raise ValueError('events and unknown_intervals must be lists')
    for event in j['events']:
        key = event.get('event_id')
        if not isinstance(key, str) or not key or key in ids:
            raise ValueError('Duplicate/missing event_id')
        ids.add(key)
        a, b = instant(event.get('started_at')), instant(event.get('ended_at'))
        if not start <= a <= b <= end:
            raise ValueError('Event outside coverage or reversed')
        if event.get('method') not in ('hand', 'pump'):
            raise ValueError('method must be hand or pump')
        for field in ('volume_ml', 'actual_ms'):
            value = event.get(field)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('Invalid ' + field)
        if event['method'] == 'hand' and event.get('actual_ms') is not None:
            raise ValueError('Hand watering cannot have pump actual_ms')
        events.append((a, b))
    events.sort()
    if any(a <= prev_b for (_, prev_b), (a, _) in zip(events, events[1:])):
        raise ValueError('Overlapping watering events; reconcile the journal')
    for interval in j['unknown_intervals']:
        a, b = instant(interval.get('start')), instant(interval.get('end'))
        if not start <= a < b <= end:
            raise ValueError('Unknown interval outside coverage or reversed')
    return j


def load_journal(path):
    return validate_journal(strict_json(Path(path).read_text(encoding='utf-8')))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    init = sub.add_parser('init')
    init.add_argument('path', type=Path)
    for arg in ('device-id', 'calibration-id', 'start', 'end'):
        init.add_argument('--' + arg, required=True)
    init.add_argument('--origin', choices=['real', 'synthetic'], default='real')
    add = sub.add_parser('add')
    add.add_argument('path', type=Path)
    for arg in ('event-id', 'start', 'end', 'method'):
        add.add_argument('--' + arg, required=True)
    add.add_argument('--volume-ml', type=float)
    add.add_argument('--actual-ms', type=float)
    add.add_argument('--note', default='')
    check = sub.add_parser('check'); check.add_argument('path', type=Path)
    args = p.parse_args()
    try:
        if args.action == 'init':
            j = dict(schema_version=1, device_id=args.device_id, calibration_id=args.calibration_id,
                     data_origin=args.origin, coverage_start=args.start, coverage_end=args.end,
                     history_complete=False, last_watered_at_before_start=None, events=[], unknown_intervals=[])
            validate_journal(j)
            args.path.parent.mkdir(parents=True, exist_ok=True)
            with args.path.open('x', encoding='utf-8') as f:
                f.write(json.dumps(j, indent=2, ensure_ascii=False) + '\n')
        else:
            j = load_journal(args.path)
            if args.action == 'add':
                j['events'].append(dict(event_id=args.event_id, started_at=args.start, ended_at=args.end,
                                        method=args.method, volume_ml=args.volume_ml, actual_ms=args.actual_ms, note=args.note))
                validate_journal(j)
                args.path.write_text(json.dumps(j, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({'events': len(j['events']), 'history_complete': j['history_complete'],
                          'note': 'Review coverage, previous watering and unknown intervals before marking history_complete=true.'}))
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    main()
