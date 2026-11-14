"""Offline W03 temporal holdout. Never fit, deploy or modify W01 bundles."""
import hashlib,json,sys
from pathlib import Path
import joblib,numpy as np,pandas as pd
sys.path.insert(0,str(Path.cwd()/'ai'))
from smart_green_ai.features import supervised,FEATURES,FEATURE_VERSION
from smart_green_ai.train import predictions
root=Path('artifacts/session-w03-2026-11-13');csv=root/'minute-data.csv'
raw=pd.read_csv(csv)
for h in (30,60):
 source=Path(f'artifacts/ai-train-w01-20261112/horizon-{h}')
 bundle_path=source/'candidate.joblib';bundle=joblib.load(bundle_path);meta=bundle['metadata']
 rows,quality=supervised(raw,h)
 assert meta['feature_version']==FEATURE_VERSION and meta['features']==FEATURES
 assert meta['horizon_minutes']==h and not meta['automatic_irrigation_approved']
 for key in ['device_id','calibration_id','data_origin','time_basis']:assert quality[key]==meta['quality'][key]
 assert rows.index.min()>pd.Timestamp(meta['split']['test']['last_label'])
 selected=meta['selected_by_validation']
 names=list(dict.fromkeys(['persistence','linear_extrapolation',selected]))
 exported=pd.DataFrame({'timestamp':rows.index,'label_time':rows.label_time.to_numpy(),'current_soil_pct':rows.soil_pct.to_numpy(),'target':rows.target.to_numpy()})
 falling=(rows.target<rows.soil_pct).to_numpy();metrics={}
 for name in names:
  pred=predictions(name,bundle['model'] if name==selected else None,rows,h)
  assert np.isfinite(pred).all()
  exported[name]=pred
  error=np.abs(pred-rows.target.to_numpy())
  metrics[name]={'mae_pp':float(error.mean()),'falling_mae_pp':float(error[falling].mean()) if falling.any() else None}
 domain={}
 w01=pd.read_csv('artifacts/session-2026-11-11/minute-data.csv');old,_=supervised(w01,h)
 from smart_green_ai.features import chronological_split
 fit,_,_=chronological_split(old)
 for key in FEATURES:
  low,high=float(fit[key].min()),float(fit[key].max())
  domain[key]={'w01_fit_min':low,'w01_fit_max':high,'w03_min':float(rows[key].min()),'w03_max':float(rows[key].max()),'outside_fit_range_rows':int(((rows[key]<low)|(rows[key]>high)).sum())}
 report={'evaluation':'Frozen W01 candidate on all eligible W03 windows, no fitting or selection on W03','horizon_minutes':h,'quality':quality,'feature_version':FEATURE_VERSION,'selected_on_w01_validation':selected,'evaluated_models':names,'not_evaluated':'Unselected fitted W01 ML models were not saved; do not refit or claim their W03 scores.','rows':len(rows),'falling_rows':int(falling.sum()),'first_feature_time':rows.index.min().isoformat(),'last_label_time':rows.label_time.max().isoformat(),'metrics':metrics,'feature_ranges':domain,'dataset_sha256':hashlib.sha256(csv.read_bytes()).hexdigest(),'candidate_path':str(bundle_path),'candidate_sha256':hashlib.sha256(bundle_path.read_bytes()).hexdigest(),'w01_versions':meta['versions'],'automatic_irrigation_approved':False,'limitation':'W03 is a later recording of the same watering cycle, not an independent watering cycle. No interpolation across outage or reboot.'}
 out=root/f'evaluation-{h}';out.mkdir(exist_ok=False)
 exported.to_csv(out/'test_predictions.csv',index=False);(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(h,'windows',len(rows),'falling',int(falling.sum()),'selected',selected,'metrics',metrics)
 # Verify exported errors independently after serialization.
 check=pd.read_csv(out/'test_predictions.csv')
 for name,m in metrics.items():assert np.isclose((check[name]-check.target).abs().mean(),m['mae_pp'])
 assert hashlib.sha256(bundle_path.read_bytes()).hexdigest()==report['candidate_sha256']
