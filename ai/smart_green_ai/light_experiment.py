"""Fixed W01 fit / W02+W03 validation / W04 test ablation; never deploys models."""
import argparse, hashlib, json, platform
from pathlib import Path
import joblib, numpy as np, pandas as pd, sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from .features import FEATURES
from .light_features import augment_minutes, light_supervised, FEATURES_WITH_LIGHT, FEATURE_VERSION

SOURCES = {
 'W01': ('artifacts/session-2026-11-11', 'telemetry.jsonl'),
 'W02': ('artifacts/session-w02-2026-11-12', 'telemetry.jsonl'),
 'W03': ('artifacts/session-w03-2026-11-13', 'telemetry-session.jsonl'),
 'W04': ('artifacts/session-w04-2026-11-14', 'telemetry.jsonl'),
}


def run(output):
    output=Path(output);output.mkdir(parents=True, exist_ok=False)
    datasets={};quality={};hashes={}
    for name,(folder,filename) in SOURCES.items():
        folder=Path(folder);rawpath=folder/filename;basepath=folder/'minute-data.csv'
        for path in [rawpath,basepath]:hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        raw=[json.loads(line) for line in rawpath.read_text().splitlines()]
        base=pd.read_csv(basepath);data=augment_minutes(base,raw);datasets[name]=data
        data.to_csv(output/f'{name}-minutes.csv',index=False)
        values=pd.to_numeric(pd.Series([r.get('light_raw') for r in raw]),errors='coerce')
        finite=np.isfinite(values);valid=finite & values.between(0,4095)
        paired=data[['soil_pct','light_raw']].dropna()
        # Differences only across adjacent valid minutes, not gaps or water exclusions.
        indexed=data.set_index(pd.to_datetime(data.timestamp,utc=True))[['soil_pct','light_raw']]
        delta=indexed.diff().where(indexed.index.to_series().diff().eq(pd.Timedelta(minutes=1)),axis=0).dropna()
        quality[name]={'raw_rows':len(raw),'present_light':int(values.notna().sum()),'valid_adc_rows':int(valid.sum()),'saturated_4095':int(values.eq(4095).sum()),'saturation_percent':float(values.eq(4095).mean()*100),'adc_min':float(values[valid].min()),'adc_max':float(values[valid].max()),'minute_missing_adc':int(data.light_raw.isna().sum()),'minute_saturated':int(data.light_saturated.fillna(False).sum()),'soil_adc_pearson':float(paired.corr().iloc[0,1]),'soil_adc_change_pearson':float(delta.corr().iloc[0,1]),'correlation_note':'Descriptive only; serial dependence, environment and watering confound causality.'}
    reports=[]
    for h in (30,60):
        parts={};counts={}
        for name,data in datasets.items():parts[name],counts[name]=light_supervised(data,h)
        fit=parts['W01'];val=pd.concat([parts['W02'],parts['W03']]);test=parts['W04']
        if min(len(fit),len(val),len(test))<20:raise ValueError('Insufficient common windows')
        assert fit.label_time.max()<val.index.min() and val.label_time.max()<test.index.min()
        predictions=pd.DataFrame({'timestamp':test.index,'label_time':test.label_time.to_numpy(),'target':test.target.to_numpy()})
        metrics={};validation={};models={}
        for light in (False,True):
            features=FEATURES_WITH_LIGHT if light else FEATURES
            for kind in ('linear_regression','random_forest'):
                key=kind+('_light' if light else '_control')
                model=LinearRegression() if kind=='linear_regression' else RandomForestRegressor(n_estimators=150,max_depth=8,min_samples_leaf=10,random_state=42,n_jobs=1)
                model.fit(fit[features],fit.target);models[key]=(model,features)
                vp=np.clip(model.predict(val[features]),0,100)
                validation[key]=float(np.abs(vp-val.target).mean())
        validation['persistence']=float(np.abs(val.soil_pct-val.target).mean())
        validation['linear_extrapolation']=float(np.abs(np.clip(val.soil_pct+val.slope_15*h,0,100)-val.target).mean())
        # Selection frozen on validation before computing any W04 scores.
        selected=min(validation,key=validation.get)
        for key,(model,features) in models.items():predictions[key]=np.clip(model.predict(test[features]),0,100)
        predictions['persistence']=test.soil_pct.to_numpy()
        predictions['linear_extrapolation']=np.clip(test.soil_pct+test.slope_15*h,0,100).to_numpy()
        for key in validation:metrics[key]=float(np.abs(predictions[key]-predictions.target).mean())
        no_sat,_=light_supervised(datasets['W04'],h,exclude_saturated=True)
        subset=predictions[pd.to_datetime(predictions.timestamp,utc=True).isin(no_sat.index)]
        sensitivity={k:float(np.abs(subset[k]-subset.target).mean()) if len(subset) else None for k in validation}
        ranges={f:{'fit_min':float(fit[f].min()),'fit_max':float(fit[f].max()),'test_outside_fit_rows':int(((test[f]<fit[f].min())|(test[f]>fit[f].max())).sum())} for f in FEATURES_WITH_LIGHT}
        report={'horizon_minutes':h,'feature_version':FEATURE_VERSION,'counts':counts,'fit_session':'W01','validation_sessions':['W02','W03'],'test_session':'W04','selected_on_validation':selected,'validation_mae_pp':validation,'test_mae_pp':metrics,'saturation_sensitivity':{'policy':'same fitted models, test subset with no saturated ADC in 16-minute history; diagnostic, not model selection','rows':len(subset),'mae_pp':sensitivity},'ranges':ranges,'automatic_irrigation_approved':False,'can_trigger_pump':False,'split':{n:{'rows':len(p),'first_feature':p.index.min().isoformat(),'last_label':p.label_time.max().isoformat()} for n,p in parts.items()}}
        dest=output/f'horizon-{h}';dest.mkdir();predictions.to_csv(dest/'predictions.csv',index=False)
        for key,(model,features) in models.items():
            joblib.dump({'model':model,'metadata':{**report,'model_name':key,'features':features,'input_sha256':hashes}},dest/f'{key}.joblib')
        (dest/'report.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(report)
    summary={'protocol':'Predeclared fixed session split, paired common windows, no W04 fitting/tuning. W04 previously inspected: exploratory holdout; W05 needed for untouched confirmation. W01–W03 share watering cycle. Saturation retained as censored ADC, no lux conversion or imputation.','versions':{'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__},'input_sha256':hashes,'light_quality':quality,'results':reports,'promote':False}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for f,h in hashes.items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
    print(json.dumps({'quality':quality,'mae':[{ 'horizon':r['horizon_minutes'],'selected':r['selected_on_validation'],'test':r['test_mae_pp']} for r in reports]},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output)
