"""Offline robustness checks; no fitting, no deployment. Run from repository root."""
import sys,json,copy,hashlib
from pathlib import Path
import pandas as pd,numpy as np,joblib
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'ai')]
from prepare_telemetry import prepare
from build_ai_dataset import build
from smart_green_ai.features import supervised
from smart_green_ai.train import predictions
root=Path(__file__).parent
journal=json.loads((root/'watering-journal.json').read_text())
rows,_,_=prepare([root/'telemetry.jsonl']);results={}
for variant in ['expanded_events','prior_W01_assumption']:
 j=copy.deepcopy(journal)
 if variant=='expanded_events':
  for e in j['events']:
   e['started_at']=(pd.Timestamp(e['started_at'])-pd.Timedelta(minutes=1)).isoformat()
   e['ended_at']=(pd.Timestamp(e['ended_at'])+pd.Timedelta(minutes=1)).isoformat()
 else:j['last_watered_at_before_start']='2026-11-11T12:14:00+07:00'
 out=root/'sensitivity'/variant;out.mkdir(parents=True,exist_ok=True)
 (out/'journal.json').write_text(json.dumps(j,indent=2)+'\n')
 data,quality=build(rows,j,time_basis='device_timestamp',as_of=journal['coverage_end']);data.to_csv(out/'minute-data.csv',index=False)
 results[variant]={'quality':quality,'evaluation':{}}
 for h in (30,60):
  samples,_=supervised(data,h)
  for e in j['events']:
   start=pd.Timestamp(e['started_at']);end=pd.Timestamp(e['ended_at'])
   assert not ((samples.index-pd.Timedelta(minutes=15)<=end)&(samples.label_time>=start)).any()
  bp=Path(f'artifacts/ai-train-w01-20261112/horizon-{h}/candidate.joblib');before=hashlib.sha256(bp.read_bytes()).hexdigest();bundle=joblib.load(bp);selected=bundle['metadata']['selected_by_validation']
  metrics={}
  for name in dict.fromkeys(['persistence','linear_extrapolation',selected]):
   pred=predictions(name,bundle['model'] if name==selected else None,samples,h)
   metrics[name]=float(np.abs(pred-samples.target.to_numpy()).mean())
  results[variant]['evaluation'][str(h)]={'rows':len(samples),'mae_pp':metrics}
  assert before==hashlib.sha256(bp.read_bytes()).hexdigest()
(root/'sensitivity-report.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
