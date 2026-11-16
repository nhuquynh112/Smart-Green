from datetime import datetime, timedelta, timezone
import pytest
from backend.reviewed_history import reconcile
from backend.ai_service import make_recent_minute_dataframe
from smart_green_ai.features import latest_features

T=datetime(2026,11,15,10,tzinfo=timezone.utc)
def setup():
    doc=dict(name='W',start=T.isoformat(),end=(T+timedelta(minutes=30)).isoformat(),
             calibration_id='cal',last_watered_at_before_start=(T-timedelta(hours=1)).isoformat(),
             events=[],unknown_intervals=[],notes='',history_complete=True)
    rows=[dict(measured_at=T+timedelta(minutes=i),boot_id='b',data_origin='real',calibration_id='cal',
               soil_valid=True,air_valid=True,soil_pct=40,temperature_c=25,humidity_pct=60,pump_running=False)
          for i in range(30)]
    return doc,rows

def call(doc,rows,pumps):return reconcile(doc,'g','cal',rows,pumps,T+timedelta(minutes=30))
def pump(a,b=None):return dict(started_at=a.timestamp(),actual_ms=None if b is None else (b-a).total_seconds()*1000,reason='Reboot' if b is None else 'Duration')

def test_old_reset_recovers_only_after_known_water_anchor():
    doc,rows=setup();selected,events=call(doc,rows,[pump(T-timedelta(hours=2))])
    frame=make_recent_minute_dataframe('g',selected,events,as_of=T+timedelta(minutes=30))
    assert len(latest_features(frame))==1
    with pytest.raises(ValueError,match='Reset'):
        call(doc,rows,[pump(T-timedelta(minutes=30))])


def test_hand_water_count_and_pump_duplicate_reconciled():
    doc,rows=setup();a=T+timedelta(minutes=2);b=a+timedelta(milliseconds=500)
    doc['events']=[dict(event_id='p',started_at=a.isoformat(),ended_at=b.isoformat(),method='pump',actual_ms=500,volume_ml=None)]
    selected,events=call(doc,rows,[pump(a,b)])
    assert len(events)==2  # previous anchor + one pump, not two pumps
    frame=make_recent_minute_dataframe('g',selected,events,as_of=T+timedelta(minutes=30))
    assert frame.iloc[2].soil_pct != frame.iloc[2].soil_pct
    assert frame.iloc[-1].water_event_count==2
    doc['events'][0].update(method='hand',actual_ms=None)
    with pytest.raises(ValueError,match='chồng'):
        call(doc,rows,[pump(a,b)])
    selected,events=call(doc,rows,[])
    assert len(events)==2
    frame=make_recent_minute_dataframe('g',selected,events,as_of=T+timedelta(minutes=30))
    assert abs(frame.iloc[-1].minutes_since_water-(27+59.5/60))<1e-6

@pytest.mark.parametrize('change',[{'history_complete':False},{'last_watered_at_before_start':None},{'calibration_id':'other'},{'unknown_intervals':[{'start':T.isoformat(),'end':(T+timedelta(minutes=1)).isoformat()}]}])
def test_unreviewed_missing_anchor_wrong_calibration_unknown_rejected(change):
    doc,rows=setup();doc.update(change)
    with pytest.raises(ValueError):call(doc,rows,[])

def test_pump_outside_coverage_and_unmatched_journal_pump_rejected():
    doc,rows=setup()
    with pytest.raises(ValueError,match='vượt'):
        call(doc,rows,[pump(T-timedelta(minutes=10),T-timedelta(minutes=9))])
    doc['events']=[dict(event_id='p',started_at=T.isoformat(),ended_at=(T+timedelta(seconds=1)).isoformat(),method='pump',actual_ms=1000,volume_ml=None)]
    with pytest.raises(ValueError,match='chưa khớp'):call(doc,rows,[])
