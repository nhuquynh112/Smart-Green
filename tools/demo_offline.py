"""Run the TV1 synthetic telemetry -> journal -> minute CSV -> AI/report demo, without hardware."""
import argparse
import json
from pathlib import Path

import pandas as pd
from smart_green_ai.simulate import generate
from smart_green_ai.assess import assess
from smart_green_ai.train import train
from smart_green_ai.inference import predict
import joblib
from prepare_telemetry import prepare
from watering_journal import validate_journal
from build_ai_dataset import build
from export_ai_report import export


def run(output, days=3):
    if days < 2:
        raise ValueError('Use at least 2 synthetic days for the demo')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    synthetic = generate(days)
    first = pd.Timestamp(synthetic.timestamp.iloc[0])
    end = pd.Timestamp(synthetic.timestamp.iloc[-1]) + pd.Timedelta(minutes=1)
    journal = dict(schema_version=1, device_id='SIM-ONLY', calibration_id='SIM-v1', data_origin='synthetic',
                   coverage_start=first.isoformat(), coverage_end=end.isoformat(), history_complete=True,
                   last_watered_at_before_start=first.isoformat(), unknown_intervals=[], events=[])
    records, previous_count = [], 0
    for i, row in enumerate(synthetic.to_dict('records')):
        t = pd.Timestamp(row['timestamp'])
        if row['water_event_count'] > previous_count:
            journal['events'].append(dict(event_id=f'synthetic-{i}',method='hand',started_at=t.isoformat(),
                                          ended_at=(t+pd.Timedelta(seconds=20)).isoformat(),volume_ml=None,actual_ms=None))
        previous_count = row['water_event_count']
        records.append(dict(schema_version=1,device_id='SIM-ONLY',boot_id='synthetic-boot',sample_seq=i+1,
                            uptime_ms=i*60000,calibration_id='SIM-v1',data_origin='synthetic',timestamp=t.isoformat(),
                            received_at=(t+pd.Timedelta(seconds=2)).isoformat(),soil_raw=1800,light_raw=900,
                            soil_pct=row['soil_pct'],soil_valid=True,temperature_c=row['temperature_c'],
                            humidity_pct=row['humidity_pct'],air_valid=True,light_lux=None,tank_ok=True,pump_on=False))
    source = output/'telemetry.synthetic.jsonl'
    source.write_text(''.join(json.dumps(r)+'\n' for r in records),encoding='utf-8')
    validate_journal(journal)
    (output/'watering.synthetic.json').write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    rows, _, quality = prepare(source)
    dataset, normalization = build(rows,journal,as_of=end.isoformat())
    csv = output/'minutes.synthetic.csv';dataset.to_csv(csv,index=False)
    readiness = assess(dataset)
    (output/'quality.json').write_text(json.dumps(dict(telemetry=quality,normalization=normalization,readiness=readiness),indent=2)+'\n')
    if not readiness['training_pipeline_ready']:
        raise ValueError('Synthetic demo did not pass readiness checks')
    report = train(csv,output/'model',30)
    advice = predict(joblib.load(output/'model/candidate.joblib'),dataset,end.isoformat())
    (output/'advice.synthetic.json').write_text(json.dumps(advice,indent=2)+'\n')
    export(output/'model',output/'report')
    summary = dict(data_origin='synthetic',feature_version=report['feature_version'],
                   selected_by_validation=report['selected_by_validation'],
                   test_mae=report['test_mae_percentage_points'],can_trigger_pump=advice['can_trigger_pump'],
                   html=str(output/'report/index.html'))
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True,help='New directory; existing evidence will not be overwritten')
    p.add_argument('--days',type=int,default=3)
    a=p.parse_args()
    try:
        print(json.dumps(run(a.output,a.days),indent=2))
    except (ValueError,OSError) as exc:
        p.error(str(exc))


if __name__=='__main__':main()
