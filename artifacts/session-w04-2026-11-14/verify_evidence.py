"""Read-only verification of W04 artifacts and previous evidence. Run at repo root."""
from pathlib import Path
import json,hashlib,sys
import numpy as np,pandas as pd
sys.path.insert(0,str(Path.cwd()/'ai'))
from smart_green_ai.features import supervised
root=Path(__file__).parent
for name in ['docs/w01-evidence/backup-manifest.json','docs/w02-evidence/manifest.json','docs/w03-evidence/manifest.json','docs/w04-evidence/manifest.json']:
 m=json.loads(Path(name).read_text());hashes=m.get('files_sha256',m)
 for f,h in hashes.items():
  assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h, f'Hash mismatch: {f}'
 print('Verified:',name,len(hashes),'files')
raw=pd.read_json(root/'telemetry.jsonl',lines=True)
assert len(raw)==1313 and not raw.duplicated(['device_id','boot_id','sample_seq']).any()
assert raw.boot_id.nunique()==1 and (raw['mode']=='OFF').all() and (~raw.pump_on).all()
assert raw.light_raw.notna().all()
minutes=pd.read_csv(root/'minute-data.csv');j=json.loads((root/'watering-journal.json').read_text())
assert len(j['events'])==2 and all(e['method']=='hand' and e['volume_ml'] is None for e in j['events'])
for h in [30,60]:
 report=json.loads((root/f'evaluation-{h}/report.json').read_text());pred=pd.read_csv(root/f'evaluation-{h}/test_predictions.csv')
 rows,_=supervised(minutes,h)
 assert len(rows)==len(pred)==report['rows']
 assert (pd.to_datetime(pred.label_time,utc=True)-pd.to_datetime(pred.timestamp,utc=True)==pd.Timedelta(minutes=h)).all()
 assert np.allclose(pred.target,rows.target) and np.allclose(pred.current_soil_pct,rows.soil_pct)
 for e in j['events']:
  assert not ((rows.index-pd.Timedelta(minutes=15)<=pd.Timestamp(e['ended_at']))&(rows.label_time>=pd.Timestamp(e['started_at']))).any()
 for name,value in report['metrics'].items():
  assert np.isclose((pred[name]-pred.target).abs().mean(),value['mae_pp'])
 assert hashlib.sha256(Path(report['candidate_path']).read_bytes()).hexdigest()==report['candidate_sha256']
 assert hashlib.sha256((root/'minute-data.csv').read_bytes()).hexdigest()==report['dataset_sha256']
 print('Verified horizon',h,report['rows'],'windows, labels, no watering crossing, MAE and unchanged candidate')
print('W04 evidence verification PASSED')
