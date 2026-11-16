"""Verify the publication package without reading the private original export."""
from pathlib import Path
import hashlib,json
import pandas as pd
from prepare_telemetry import prepare
from build_ai_dataset import build
from smart_green_ai.light_features import augment_minutes, light_supervised
p=Path(__file__).resolve().parent
for name,expected in json.loads((p/'manifest.json').read_text())['files_sha256'].items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==expected,name
rows,_,quality=prepare([p/'telemetry.jsonl'])
assert len(rows)==927 and not quality['rejected'] and not quality['duplicates_removed']
journal=json.loads((p/'journal.json').read_text())
base,_=build(rows,journal,as_of=journal['coverage_end'])
actual=augment_minutes(base,rows);expected=pd.read_csv(p/'light-minutes.csv')
expected['excluded_reason']=expected['excluded_reason'].fillna('')  # CSV empty text, not a missing sensor value
pd.testing.assert_frame_equal(actual.reset_index(drop=True),expected,check_dtype=False,check_exact=False)
report=json.loads((p/'evaluation.json').read_text())
for h in (30,60):
    data,_=light_supervised(actual,h);pred=pd.read_csv(p/f'predictions-{h}.csv')
    assert list(pd.to_datetime(pred.timestamp,utc=True))==list(data.index)
    assert list(pd.to_datetime(pred.label_time,utc=True))==list(data.label_time)
    pd.testing.assert_series_equal(pred.target.reset_index(drop=True),data.target.reset_index(drop=True),check_names=False)
    result=next(r for r in report['results'] if r['horizon_minutes']==h)
    assert len(pred)==result['windows']
    for name,mae in result['mae_pp'].items():assert abs((pred[name]-pred.target).abs().mean()-mae)<1e-10
print('W05 package: checksums, 927 raw samples, reconstructed minutes, paired labels and MAEs verified')
