"""Offline regression tests; no database, HTTP server, or device access."""
from datetime import datetime, timedelta, timezone

import pytest

from backend.ai_service import make_recent_minute_dataframe
from smart_green_ai.features import latest_features

START = datetime(2026, 11, 13, 3, tzinfo=timezone.utc)


def samples(n=20):
    return [dict(measured_at=START + timedelta(minutes=i), boot_id='boot1',
                 data_origin='real', calibration_id='cal1', soil_valid=True,
                 air_valid=True, soil_pct=40, temperature_c=25, humidity_pct=60,
                 pump_running=False) for i in range(n)]


def event(start, end):
    return dict(reason='Manual', started_at=int(start.timestamp()),
                ended_at=int(end.timestamp()))


def history():
    return [event(START-timedelta(hours=1), START-timedelta(minutes=59))]


def test_current_minute_does_not_hide_complete_history():
    frame = make_recent_minute_dataframe('garden', samples(), history(),
                                        as_of=START+timedelta(minutes=19, seconds=30))
    assert len(frame) == 19
    assert latest_features(frame).index[-1].minute == 18


def test_one_pumping_sample_invalidates_entire_minute():
    rows = samples()
    rows.append(dict(rows[-1], measured_at=START+timedelta(minutes=19, seconds=30),
                     pump_running=True))
    frame = make_recent_minute_dataframe('garden', rows, history(),
                                        as_of=START+timedelta(minutes=20))
    assert frame.iloc[-1].soil_pct != frame.iloc[-1].soil_pct
    with pytest.raises(ValueError, match='16 complete'):
        latest_features(frame)


def test_long_watering_excludes_middle_even_before_event_ends():
    events = history()+[event(START+timedelta(minutes=1), START+timedelta(minutes=30))]
    frame = make_recent_minute_dataframe('garden', samples(), events,
                                        as_of=START+timedelta(minutes=20))
    assert frame.iloc[1:].soil_pct.isna().all()
    with pytest.raises(ValueError, match='16 complete'):
        latest_features(frame)


def test_watering_end_minute_excluded_then_recovers_after_complete_history():
    events = history()+[event(START, START+timedelta(minutes=2))]
    frame = make_recent_minute_dataframe('garden', samples(), events,
                                        as_of=START+timedelta(minutes=20))
    assert frame.iloc[:3].soil_pct.isna().all()
    assert len(latest_features(frame)) == 1


def test_reversed_event_fails_closed():
    frame = make_recent_minute_dataframe('garden', samples(),
        [event(START, START-timedelta(seconds=1))], as_of=START+timedelta(minutes=20))
    assert frame.empty
