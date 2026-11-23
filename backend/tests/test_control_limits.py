import pytest
from backend.control_limits import manual_limits
from backend.tests.test_api import client, db, telemetry, headers, DEVICE
from backend.database import utc_iso


@pytest.mark.parametrize('raw,expected',[('1000',1000),('bad',0),('0',0),('-1',0),('60001',0)])
def test_configuration_fails_closed(monkeypatch,raw,expected):
    monkeypatch.setenv('SG_MAX_PULSE_MS',raw)
    assert manual_limits({'max_pulse_ms':3000})['manual_max_ms']==expected


def test_dashboard_and_command_share_effective_limit(client,monkeypatch):
    monkeypatch.setenv('SG_MAX_PULSE_MS','1000')
    row=telemetry();row.update(mode='MANUAL',commissioned=True,timestamp=utc_iso(),max_pulse_ms=3000)
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==200
    dash=client.get(f'/api/v1/web/devices/{DEVICE}/dashboard').json()
    assert dash['control_limits']['manual_max_ms']==1000
    route=f'/api/v1/web/devices/{DEVICE}/commands'
    assert client.post(route,admin=True,json={'kind':'WATER','duration_ms':3000}).status_code==400
    assert client.post(route,admin=True,json={'kind':'WATER','duration_ms':1000}).status_code==201


def test_firmware_limit_can_only_reduce_backend_limit(client,monkeypatch):
    monkeypatch.setenv('SG_MAX_PULSE_MS','1000')
    row=telemetry();row.update(mode='MANUAL',commissioned=True,timestamp=utc_iso(),max_pulse_ms=300)
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==200
    assert client.get(f'/api/v1/web/devices/{DEVICE}/dashboard').json()['control_limits']['manual_max_ms']==300
    assert client.post(f'/api/v1/web/devices/{DEVICE}/commands',admin=True,json={'kind':'WATER','duration_ms':500}).status_code==400


@pytest.mark.parametrize('extra',[{'auto_low_pct':True},{'auto_high_pct':101},{'auto_low_pct':45,'auto_high_pct':38},{'auto_pulse_ms':-1}])
def test_bad_auto_diagnostics_rejected(client,extra):
    row=telemetry();row.update(extra)
    assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==422


def test_old_and_new_firmware_diagnostics_compatible(client):
    for seq,extra in [(1,{}),(2,{'auto_low_pct':38,'auto_high_pct':45,'auto_pulse_ms':3000,'auto_cooldown_ms':300000})]:
        row=telemetry(seq);row.update(extra)
        assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=row).status_code==200


def test_invalid_cap_locks_water_but_does_not_block_stop(client,monkeypatch):
    monkeypatch.setenv('SG_MAX_PULSE_MS','bad')
    route=f'/api/v1/web/devices/{DEVICE}/commands'
    assert client.get(f'/api/v1/web/devices/{DEVICE}/dashboard').json()['control_limits']['manual_max_ms']==0
    assert client.post(route,admin=True,json={'kind':'WATER','duration_ms':500}).status_code==503
    assert client.post(route,admin=True,json={'kind':'STOP'}).status_code==201
