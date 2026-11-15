import numpy as np
import pandas as pd
import pytest
from smart_green_ai.simulate import generate
from smart_green_ai.features import FEATURES, supervised
from smart_green_ai.light_features import LIGHT_FEATURES, augment_minutes, light_supervised


def fixture():
    raw=generate(2)
    raw['light_raw']=1000+np.arange(len(raw))%1000
    raw['light_saturated']=False
    return raw


@pytest.mark.parametrize('horizon',[30,60])
def test_light_features_are_causal_and_same_water_windows(horizon):
    raw=fixture();rows,_=light_supervised(raw,horizon)
    t=rows.index[50];changed=raw.copy()
    changed.loc[pd.to_datetime(changed.timestamp,utc=True)>t,'light_raw']=4000
    after,_=light_supervised(changed,horizon)
    pd.testing.assert_series_equal(rows.loc[t,LIGHT_FEATURES],after.loc[t,LIGHT_FEATURES])
    baseline,_=supervised(raw,horizon)
    assert rows.index.equals(baseline.index)
    pd.testing.assert_frame_equal(rows[FEATURES],baseline[FEATURES])
    grid=raw.set_index(pd.to_datetime(raw.timestamp,utc=True))
    assert rows.loc[t,'light_mean_15']==grid.loc[t-pd.Timedelta(minutes=14):t,'light_raw'].mean()
    for ts in rows.index:
        assert grid.loc[ts,'water_event_count']==grid.loc[ts+pd.Timedelta(minutes=horizon),'water_event_count']


def test_missing_adc_invalidates_history_not_future_or_baseline():
    raw=fixture();baseline,_=supervised(raw,30);t=baseline.index[80]
    raw.loc[pd.to_datetime(raw.timestamp,utc=True)==t,'light_raw']=np.nan
    rows,_=light_supervised(raw,30)
    assert not ((rows.index>=t)&(rows.index<=t+pd.Timedelta(minutes=15))).any()
    assert t-pd.Timedelta(minutes=1) in rows.index  # future light is not used
    assert t in supervised(raw,30)[0].index


def test_saturation_is_preserved_and_sensitivity_explicit():
    raw=fixture();t=supervised(raw,30)[0].index[80]
    mask=pd.to_datetime(raw.timestamp,utc=True)==t
    raw.loc[mask,'light_raw']=4095;raw.loc[mask,'light_saturated']=True
    rows,_=light_supervised(raw,30);assert rows.loc[t,'light_raw']==4095
    filtered,_=light_supervised(raw,30,exclude_saturated=True)
    assert t not in filtered.index


def test_minute_adc_rejects_partial_missing_out_of_range_and_bool():
    base=pd.DataFrame({'timestamp':pd.date_range('2026-01-01',periods=4,freq='min',tz='UTC').astype(str)})
    telemetry=[]
    for t,values in zip(base.timestamp,[(1000,1200),(4095,4000),(1000,None),(True,5000)]):
        for seconds,v in zip([0,30],values):telemetry.append({'timestamp':(pd.Timestamp(t)+pd.Timedelta(seconds=seconds)).isoformat(),'light_raw':v})
    result=augment_minutes(base,telemetry)
    assert result.light_raw.iloc[0]==1100
    assert result.light_raw.iloc[1]==4047.5 and result.light_saturated.iloc[1]
    assert result.light_raw.iloc[2:].isna().all()
