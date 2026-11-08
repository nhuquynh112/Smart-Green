"""Build closed UTC minute bins from validated telemetry and a reviewed watering journal."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

from prepare_telemetry import prepare
from watering_journal import instant, load_journal, validate_journal


def build(rows, journal, *, time_basis='device_timestamp', as_of):
    validate_journal(journal)
    if time_basis not in ('device_timestamp', 'received_at_proxy'):
        raise ValueError('Unsupported time_basis')
    closed_before = pd.Timestamp(instant(as_of)).tz_convert('UTC').floor('min')
    field = 'timestamp' if time_basis == 'device_timestamp' else 'received_at'
    for row in rows:
        if any(row[k] != journal[k] for k in ('device_id', 'calibration_id', 'data_origin')):
            raise ValueError('Select one device, calibration and origin matching the journal')
    timed = [dict(r, _time=pd.Timestamp(instant(r[field])).tz_convert('UTC'))
             for r in rows if r.get(field) is not None]
    if not timed:
        raise ValueError('No timestamps for selected basis; never infer old measurement times')
    # Reject backward host/device clocks within each boot before sorting.
    previous = {}
    for r in timed:
        key = (r['device_id'], r['boot_id'])
        if key in previous and r['_time'] < previous[key]:
            raise ValueError('Clock moved backward inside a boot; split/review session')
        previous[key] = r['_time']
    timed.sort(key=lambda r: r['_time'])
    frame = pd.DataFrame(timed)
    frame['_minute'] = frame['_time'].dt.floor('min')
    frame = frame[frame['_minute'] < closed_before]
    if frame.empty:
        raise ValueError('No closed minutes available')
    groups = dict(tuple(frame.groupby('_minute')))
    start = pd.Timestamp(instant(journal['coverage_start']))
    end = pd.Timestamp(instant(journal['coverage_end']))
    events = sorted([(pd.Timestamp(instant(e['started_at'])), pd.Timestamp(instant(e['ended_at'])))
                     for e in journal['events']])
    unknown = [pd.Timestamp(instant(i['start'])) for i in journal['unknown_intervals']]
    last_before = journal.get('last_watered_at_before_start')
    last_before = pd.Timestamp(instant(last_before)) if last_before else None
    output, exclusions = [], {}
    previous_boot = None
    for minute in pd.date_range(frame['_minute'].min(), frame['_minute'].max(), freq='min'):
        until = minute + pd.Timedelta(minutes=1)
        group = groups.get(minute)
        reasons = []
        if group is None:
            reasons.append('missing_telemetry')
        elif group.boot_id.nunique() != 1:
            reasons.append('mixed_boot_minute')
            previous_boot = None
        else:
            boot = group.boot_id.iloc[0]
            if previous_boot is not None and previous_boot != boot:
                reasons.append('boot_boundary')
            previous_boot = boot
            if group.pump_on.any():
                reasons.append('pump_on')
        if not journal['history_complete']:
            reasons.append('unreviewed_watering_history')
        if minute < start or until > end:
            reasons.append('outside_journal_coverage')
        if any(t < until for t in unknown):
            reasons.append('unknown_history_requires_new_session')
        if any(a < until and b >= minute for a, b in events):
            reasons.append('watering_minute')
        ended = [b for _, b in events if b < until]
        last = ended[-1] if ended else last_before
        if last is None:
            reasons.append('unknown_previous_watering')
        record = dict(timestamp=minute.isoformat(), time_basis=time_basis,
                      **{k: journal[k] for k in ('device_id', 'calibration_id', 'data_origin')},
                      soil_pct=None, temperature_c=None, humidity_pct=None,
                      minutes_since_water=None, water_event_count=None,
                      sample_count=0 if group is None else len(group), excluded_reason=';'.join(reasons))
        if not reasons:
            # An invalid reading invalidates that sensor's whole minute; never fill gaps.
            if group.soil_valid.all():
                record['soil_pct'] = float(group.soil_pct.median())
            if group.air_valid.all():
                record['temperature_c'] = float(group.temperature_c.median())
                record['humidity_pct'] = float(group.humidity_pct.median())
            record['minutes_since_water'] = (until - last).total_seconds() / 60
            record['water_event_count'] = len(ended)
        for reason in reasons:
            exclusions[reason] = exclusions.get(reason, 0) + 1
        output.append(record)
    result = pd.DataFrame(output)
    for column in ('soil_pct', 'temperature_c', 'humidity_pct', 'minutes_since_water', 'water_event_count'):
        result[column] = result[column].astype('float64')
    report = dict(input_rows=len(rows), rows_without_selected_time=len(rows)-len(timed),
                  output_minutes=len(result), excluded_minutes=int((result.excluded_reason != '').sum()),
                  exclusions=exclusions, time_basis=time_basis, as_of=as_of,
                  time_proxy=time_basis == 'received_at_proxy', data_origin=journal['data_origin'],
                  feature_version='v2-watering-events', automatic_irrigation_approved=False,
                  note='Closed-minute aggregates. Proxy timestamps remain labelled; no pump duration inferred from hand watering.')
    return result, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('telemetry', type=Path, nargs='+')
    p.add_argument('--journal', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--as-of', required=True, help='Timezone-aware cutoff; incomplete minute is excluded')
    p.add_argument('--time-basis', choices=['device_timestamp', 'received_at_proxy'], default='device_timestamp')
    args = p.parse_args()
    try:
        sources = [*args.telemetry, args.journal]
        report_path = args.output.with_suffix('.quality.json')
        if any(s.resolve() in (args.output.resolve(), report_path.resolve()) for s in sources):
            raise ValueError('Output must not overwrite an input')
        rows, _, telemetry_report = prepare(args.telemetry)
        if any('conflicting' in e['reason'] for e in telemetry_report['rejected']):
            raise ValueError('Conflicting telemetry identities must be resolved first')
        data, report = build(rows, load_journal(args.journal), time_basis=args.time_basis, as_of=args.as_of)
        report['telemetry_quality'] = telemetry_report
        report['input_sha256'] = {str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(args.output, index=False)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k not in ('telemetry_quality', 'input_sha256')}, ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    main()
