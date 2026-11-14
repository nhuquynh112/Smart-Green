import copy
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from build_ai_dataset import build
from watering_journal import validate_journal
from smart_green_ai.features import supervised
from smart_green_ai.assess import assess


def journal():
    return dict(schema_version=1, device_id='SIM-ONLY', calibration_id='SIM-v1', data_origin='synthetic',
                coverage_start='2026-01-01T00:00:00Z', coverage_end='2026-01-02T00:00:00Z',
                history_complete=True, last_watered_at_before_start='2025-12-31T23:00:00Z',
                events=[], unknown_intervals=[])


def telemetry(n=400):
    rows=[]
    for i,t in enumerate(pd.date_range('2026-01-01', periods=n, freq='min', tz='UTC')):
        rows.append(dict(schema_version=1,device_id='SIM-ONLY',calibration_id='SIM-v1',data_origin='synthetic',
                         timestamp=t.isoformat(),received_at=(t+pd.Timedelta(seconds=2)).isoformat(),
                         boot_id='one',sample_seq=i+1,uptime_ms=i*60000,soil_raw=1800,light_raw=1000,
                         soil_pct=70-i*.01,soil_valid=True,air_valid=True,temperature_c=25.,humidity_pct=60.,
                         light_lux=None,tank_ok=True,pump_on=False))
    return rows


def convert(rows=None, j=None, **kwargs):
    return build(telemetry() if rows is None else rows, journal() if j is None else j,
                 as_of='2026-01-02T00:00:00Z', **kwargs)


def test_manual_event_no_fake_motor_duration_and_purged_windows():
    j=journal()
    j['events']=[dict(event_id='hand-1',method='hand',started_at='2026-01-01T02:00:10Z',
                      ended_at='2026-01-01T02:00:50Z',volume_ml=None,actual_ms=None)]
    frame,_=convert(j=j)
    assert 'water_total_ms' not in frame
    assert pd.isna(frame.iloc[120].soil_pct)
    assert frame.iloc[121].water_event_count==1
    assert frame.iloc[121].minutes_since_water==pytest.approx(70/60)
    windows,_=supervised(frame)
    event=pd.Timestamp('2026-01-01T02:00:00Z')
    assert not ((windows.index<=event)&(windows.label_time>=event)).any()
    assert not ((windows.index>=event)&(windows.index<=event+pd.Timedelta(minutes=15))).any()
    assert assess(frame)['training_pipeline_ready']


def test_legacy_clock_requires_explicit_proxy():
    rows=telemetry()
    for r in rows:r['timestamp']=None
    with pytest.raises(ValueError,match='No timestamps'):convert(rows)
    frame,report=convert(rows,time_basis='received_at_proxy')
    assert report['time_proxy']
    assert frame.time_basis.eq('received_at_proxy').all()
    assert all(r['timestamp'] is None for r in rows)


def test_unknown_history_and_unreviewed_journal_block():
    j=journal();j['history_complete']=False
    frame,_=convert(j=j)
    assert frame.soil_pct.isna().all()
    j=journal();j['unknown_intervals']=[dict(start='2026-01-01T01:00:00Z',end='2026-01-01T01:10:00Z')]
    frame,_=convert(j=j)
    assert frame.iloc[60:].soil_pct.isna().all()
    j=journal();j['last_watered_at_before_start']=None
    frame,_=convert(j=j)
    assert frame.minutes_since_water.isna().all()


def test_closed_minutes_only_and_median():
    rows=telemetry(3); extra=copy.deepcopy(rows[0]);extra['soil_pct']=60;extra['sample_seq']=4
    frame,_=build([rows[0],extra,*rows[1:]],journal(),as_of='2026-01-01T00:02:30Z')
    assert len(frame)==2
    assert frame.iloc[0].soil_pct==65
    assert frame.iloc[0].sample_count==2


def test_gap_invalid_sensor_and_reboot_mask():
    rows=telemetry(100);del rows[30]
    rows[40]['air_valid']=False;rows[40]['temperature_c']=None;rows[40]['humidity_pct']=None
    for r in rows[60:]:r['boot_id']='two'
    frame,_=convert(rows)
    assert pd.isna(frame.iloc[30].soil_pct)
    assert pd.isna(frame.iloc[41].temperature_c)
    assert frame.iloc[61].excluded_reason=='boot_boundary'
    assert frame.iloc[62].soil_pct>0


def test_quality_counts_invalid_sensor_minutes_without_discarding_valid_sensor():
    rows = telemetry(3)
    rows[0].update(soil_valid=False, soil_pct=None)
    rows[1].update(air_valid=False, temperature_c=None, humidity_pct=None)
    rows[2].update(soil_valid=False, soil_pct=None, air_valid=False,
                   temperature_c=None, humidity_pct=None)
    frame, report = convert(rows)
    assert report['excluded_minutes'] == 3
    assert report['exclusions'] == {'invalid_soil_sensor': 2, 'invalid_air_sensor': 2}
    assert frame.iloc[0].excluded_reason == 'invalid_soil_sensor'
    assert frame.iloc[0].temperature_c == 25
    assert frame.iloc[1].soil_pct > 0
    assert pd.isna(frame.iloc[1].temperature_c)
    assert frame.iloc[2].excluded_reason == 'invalid_soil_sensor;invalid_air_sensor'


@pytest.mark.parametrize('fault',['id','overlap','hand_duration','naive','bad_coverage','negative_volume'])
def test_bad_journal(fault):
    j=journal()
    e=dict(event_id='a',method='hand',started_at='2026-01-01T01:00:00Z',ended_at='2026-01-01T01:00:30Z',volume_ml=10,actual_ms=None)
    j['events']=[e]
    if fault=='id':j['events'].append(copy.deepcopy(e))
    if fault=='overlap':j['events'].append(dict(e,event_id='b'))
    if fault=='hand_duration':e['actual_ms']=1000
    if fault=='naive':e['started_at']='2026-01-01T01:00:00'
    if fault=='bad_coverage':j['coverage_end']=j['coverage_start']
    if fault=='negative_volume':e['volume_ml']=-1
    with pytest.raises(ValueError):validate_journal(j)


def test_clock_mixed_calibration_and_origin_rejected():
    rows=telemetry(3);rows[2]['timestamp']=rows[0]['timestamp']
    with pytest.raises(ValueError,match='Clock'):convert(rows)
    rows=telemetry(3);rows[1]['calibration_id']='changed'
    with pytest.raises(ValueError,match='matching'):convert(rows)


def test_cli_round_trip_and_journal_append(tmp_path):
    jpath=tmp_path/'journal.json'
    base=[sys.executable,str(ROOT/'tools/watering_journal.py')]
    result=subprocess.run(base+['init',str(jpath),'--device-id','SIM-ONLY','--calibration-id','SIM-v1',
                               '--origin','synthetic','--start','2026-01-01T00:00:00Z','--end','2026-01-02T00:00:00Z'],capture_output=True)
    assert result.returncode==0,result.stderr
    assert not json.loads(jpath.read_text())['history_complete']
    result=subprocess.run(base+['add',str(jpath),'--event-id','a','--method','hand',
                               '--start','2026-01-01T02:00:00Z','--end','2026-01-01T02:00:30Z'],capture_output=True)
    assert result.returncode==0,result.stderr
    j=json.loads(jpath.read_text());j['history_complete']=True;j['last_watered_at_before_start']='2025-12-31T23:00:00Z'
    jpath.write_text(json.dumps(j))
    source=tmp_path/'telemetry.jsonl';source.write_text('\n'.join(json.dumps(r) for r in telemetry()))
    output=tmp_path/'minutes.csv'
    result=subprocess.run([sys.executable,str(ROOT/'tools/build_ai_dataset.py'),str(source),'--journal',str(jpath),
                           '--output',str(output),'--as-of','2026-01-02T00:00:00Z'],capture_output=True)
    assert result.returncode==0,result.stderr
    assert len(pd.read_csv(output))==400
    assert json.loads(output.with_suffix('.quality.json').read_text())['input_sha256']


def test_future_samples_and_events_do_not_change_earlier_bins():
    rows=telemetry(100)
    before,_=convert(rows)
    changed=copy.deepcopy(rows)
    for r in changed[60:]:r['soil_pct']=10
    j=journal();j['events']=[dict(event_id='future',method='hand',started_at='2026-01-01T01:10:00Z',
                                ended_at='2026-01-01T01:10:30Z',volume_ml=None,actual_ms=None)]
    after,_=convert(changed,j)
    pd.testing.assert_frame_equal(before.iloc[:60],after.iloc[:60])


def test_previous_watering_unknown_recovers_only_after_observed_event():
    j=journal();j['last_watered_at_before_start']=None
    j['events']=[dict(event_id='known',method='hand',started_at='2026-01-01T00:10:00Z',
                      ended_at='2026-01-01T00:10:30Z',volume_ml=None,actual_ms=None)]
    frame,_=convert(telemetry(30),j)
    assert frame.iloc[:11].minutes_since_water.isna().all()
    assert frame.iloc[11].minutes_since_water==1.5
    assert frame.iloc[11].water_event_count==1
