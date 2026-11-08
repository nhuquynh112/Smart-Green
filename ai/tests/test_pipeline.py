import numpy as np
import pandas as pd
import pytest
import joblib
from smart_green_ai.features import supervised, chronological_split, latest_features, validate, FEATURES
from smart_green_ai.simulate import generate
from smart_green_ai.train import train
from smart_green_ai.inference import predict


def test_future_irrigation_and_purge():
    raw=generate(3)
    rows, _=supervised(raw)
    grid=validate(raw)
    for t in rows.index:
        assert grid.loc[t,"water_event_count"]==grid.loc[t+pd.Timedelta(minutes=30),"water_event_count"]
    fit,val,test=chronological_split(rows)
    assert fit.label_time.max()<val.index.min()
    assert val.label_time.max()<test.index.min()


def test_gap_not_filled():
    raw=generate(2).drop(index=100)
    rows,meta=supervised(raw)
    gap=pd.Timestamp("2026-01-01T01:40:00Z")
    assert meta["missing_minutes"]==1
    assert not ((rows.index<=gap)&(rows.label_time>=gap)).any()
    assert not ((rows.index>=gap)&(rows.index<=gap+pd.Timedelta(minutes=15))).any()


def test_training_and_inference_features_equal():
    raw=generate(2)
    rows,_=supervised(raw)
    t=rows.index[100]
    history=raw.loc[pd.to_datetime(raw.timestamp,utc=True)<=t]
    pd.testing.assert_frame_equal(latest_features(history),rows.loc[[t],FEATURES],check_freq=False)


@pytest.mark.parametrize("fault",["duplicate","naive","mixed","range","counter","infinite"])
def test_invalid_input(fault):
    raw=generate(1)
    if fault=="duplicate":raw=pd.concat([raw,raw.iloc[[0]]])
    if fault=="naive":raw.loc[0,"timestamp"]="2026-01-01 00:00:00"
    if fault=="mixed":raw.loc[1,"calibration_id"]="other"
    if fault=="range":raw.loc[1,"soil_pct"]=101
    if fault=="counter":raw.loc[0,"water_event_count"]=99999
    if fault=="infinite":raw.loc[0,"soil_pct"]=np.inf
    with pytest.raises(ValueError):validate(raw)


def test_round_trip_and_no_auto_promotion(tmp_path):
    raw=generate(3)
    csv=tmp_path/"synthetic.csv";raw.to_csv(csv,index=False)
    report=train(csv,tmp_path/"out")
    assert report["quality"]["data_origin"]=="synthetic"
    assert not report["automatic_irrigation_approved"]
    bundle=joblib.load(tmp_path/"out/candidate.joblib")
    now=(pd.Timestamp(raw.timestamp.iloc[-1])+pd.Timedelta(minutes=1)).isoformat()
    advice=predict(bundle,raw,now)
    assert not advice["can_trigger_pump"]
    assert 0<=advice["predicted_soil_pct"]<=100
    with pytest.raises(ValueError,match="Stale"):
        predict(bundle,raw,"2027-01-01T00:00:00Z")


def test_future_values_do_not_change_past_features():
    raw=generate(2)
    t=pd.Timestamp(raw.timestamp.iloc[100])
    a,_=supervised(raw)
    raw.loc[131:,"soil_pct"]=50
    b,_=supervised(raw)
    pd.testing.assert_series_equal(a.loc[t,FEATURES],b.loc[t,FEATURES])


def test_falling_soil_report_matches_exported_predictions(tmp_path):
    raw=generate(2)
    csv=tmp_path/'input.csv';raw.to_csv(csv,index=False)
    report=train(csv,tmp_path/'out')
    exported=pd.read_csv(tmp_path/'out/test_predictions.csv')
    rows,_=supervised(raw)
    _,_,test=chronological_split(rows)
    mask=(test.target < test.soil_pct).to_numpy()
    assert report['falling_soil_test']['rows']==int(mask.sum())
    for name,value in report['falling_soil_test']['mae_percentage_points'].items():
        if mask.any():
            assert value==pytest.approx(np.abs(exported.loc[mask,'target']-exported.loc[mask,name]).mean())
        else:
            assert value is None


def test_inference_rejects_old_bundle_time_basis_mismatch_and_open_minute(tmp_path):
    raw=generate(1)
    csv=tmp_path/'input.csv';raw.to_csv(csv,index=False)
    train(csv,tmp_path/'model')
    bundle=joblib.load(tmp_path/'model/candidate.joblib')
    now=(pd.Timestamp(raw.timestamp.iloc[-1])+pd.Timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError,match='incomplete'):
        predict(bundle,raw,raw.timestamp.iloc[-1])
    proxy=raw.copy();proxy['time_basis']='received_at_proxy'
    with pytest.raises(ValueError,match='time_basis'):
        predict(bundle,proxy,now)
    bundle['metadata']['feature_version']='v1-no-additional-irrigation'
    with pytest.raises(ValueError,match='version'):
        predict(bundle,raw,now)


def test_fractional_event_counts_rejected():
    raw=generate(1);raw['water_event_count']=raw.water_event_count.astype(float)
    raw.loc[0,'water_event_count']=0.5
    with pytest.raises(ValueError,match='integer'):
        validate(raw)
