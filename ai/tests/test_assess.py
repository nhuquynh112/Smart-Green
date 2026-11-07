import pandas as pd
from smart_green_ai.assess import assess
from smart_green_ai.simulate import generate


def test_bench_does_not_invent_timestamps_or_water():
    raw = pd.DataFrame({'timestamp':[None], 'received_at':['2026-11-06T05:00:00Z'],
                        'soil_pct':[None], 'device_id':['garden-01']})
    before=raw.copy(deep=True)
    report=assess(raw)
    assert not report['training_pipeline_ready']
    assert 'water_total_ms' in report['missing_columns']
    assert len(report['next_actions'])==3
    pd.testing.assert_frame_equal(raw,before)


def test_synthetic_pass_is_not_real_evidence():
    report=assess(generate(3))
    assert report['training_pipeline_ready']
    assert not report['real_world_evidence_sufficient']
    assert not report['automatic_irrigation_approved']
    assert any('SYNTHETIC' in text for text in report['warnings'])


def test_empty_and_invalid_timestamp_block():
    assert assess(pd.DataFrame())['blockers']
    raw=generate(1);raw.loc[0,'timestamp']=None
    report=assess(raw)
    assert not report['training_pipeline_ready']
    assert report['blockers']
