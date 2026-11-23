"""Native AUTO controller + actual backend handlers, in-memory SQLite only.

No device sockets/serial/GPIO. Authentication/HTTP transport are covered by
existing API/loopback suites; this suite checks cross-layer state and journals.
"""
import json
import subprocess
import time

import pytest

from integration.test_http_runtime import binary  # pytest host compiler fixture
from backend.app import create_app
from backend.database import Database
from backend.tests.test_api import SyncASGIClient, KEY


@pytest.fixture
def system(binary):
    db = Database('sqlite:///:memory:')
    # Firmware simulator protocol identity is garden-01.
    db.ensure_device('garden-01', KEY, 'cal-v1')
    client = SyncASGIClient(create_app(db=db, bundle=None))
    process = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def core(ms, op='tick', **kwargs):
        request = dict(ms=ms, op=op, utc=int(time.time()), **kwargs)
        process.stdin.write(json.dumps(request)+'\n'); process.stdin.flush()
        return json.loads(process.stdout.readline())
    yield db, client, core
    process.stdin.close(); process.wait(timeout=3); process.stdout.close(); db.close()
    assert process.returncode == 0


WEB = '/api/v1/web/devices/garden-01/commands'
ROOT = '/api/v1/devices/garden-01'
HEADERS = {'X-API-Key': KEY}


def enable_auto(client, core):
    queued = client.post(WEB, admin=True, json={'kind':'SET_MODE','mode':'AUTO'})
    assert queued.status_code == 201
    cmd = client.get(ROOT+'/commands/next?after_seq=0', headers=HEADERS).json()
    result = core(2000, 'command', payload=cmd)
    assert result['result'] == 'mode_set' and not result['pump_on']
    ack = dict(schema_version=1, device_id='garden-01', command_seq=cmd['command_seq'], result=result['result'])
    assert client.post(ROOT+f"/commands/{cmd['command_seq']}/ack", headers=HEADERS,json=ack).status_code == 204


def test_auto_rule_event_backend_retry_conflict_and_fifo_ack(system):
    db, client, core = system
    enable_auto(client, core)
    for ms in (3000,4000,5000): state = core(ms)
    assert state['pump_on']
    state = core(6000)
    assert not state['pump_on']
    event = state['events'][0]
    assert (event['source'],event['command_seq'],event['reason'],event['actual_ms']) == ('RULE',0,'Duration',1000)
    for _ in range(2):
        response = client.post(ROOT+'/events',headers=HEADERS,json=event)
        assert response.status_code == 200
    assert db.one('SELECT count(*) AS n FROM watering_events')['n'] == 1
    conflict = dict(event, actual_ms=999)
    assert client.post(ROOT+'/events',headers=HEADERS,json=conflict).status_code == 409
    assert core(6000,'ack_event',event_id=event['event_id'])['events'] == []
    assert core(6000)['starts_reserved'] == 1


@pytest.mark.parametrize('body',[{'kind':'STOP'},{'kind':'SET_MODE','mode':'OFF'}])
def test_backend_stop_or_off_ends_running_auto_and_supersedes_pending(system,body):
    db,client,core=system
    enable_auto(client,core)
    for ms in (3000,4000,5000):state=core(ms)
    assert state['pump_on']
    # An older pending AUTO mode must not survive the stop fence.
    pending=client.post(WEB,admin=True,json={'kind':'SET_MODE','mode':'AUTO'}).json()
    assert client.post(WEB,admin=True,json=body).status_code==201
    cmd=client.get(ROOT+'/commands/next?after_seq=0',headers=HEADERS).json()
    assert cmd['kind']==body['kind']
    state=core(5100,'command',payload=cmd)
    assert not state['pump_on'] and state['mode']=='OFF'
    for ms in (6000,7000,8000):assert not core(ms)['pump_on']
    assert db.one('SELECT status FROM commands WHERE command_seq=?',(pending['command_seq'],))['status']=='EXPIRED'
    assert state['events'][0]['reason']=='Stop'


def test_auto_mode_ack_does_not_override_stale_or_empty_sensor(system):
    _,client,core=system
    enable_auto(client,core)
    for ms in (5000,6000,7000):
        assert not core(ms,sampled_ms=1)['pump_on']
    for ms in (8000,9000,10000):
        assert not core(ms,tank_ok=False)['pump_on']
    assert core(11000,tank_ok=True)['pump_on']
    state=core(11100,valid=False)
    assert not state['pump_on'] and state['events'][0]['reason']=='Sensor'


def test_runtime_reboot_disarms_auto_preserves_event_and_requires_new_command(system):
    _,client,core=system
    enable_auto(client,core)
    for ms in (3000,4000,5000): state=core(ms)
    assert state['pump_on']
    state=core(0,'reboot')
    assert state['mode']=='OFF' and not state['pump_on']
    assert state['starts_reserved']==1
    assert state['events'][0]['reason']=='Reboot'
    assert state['events'][0]['actual_ms'] is None
    for ms in (2000,3000,4000): assert not core(ms)['pump_on']
    enable_auto(client,core)
    for ms in (5000,6000,7000): state=core(ms)
    assert state['pump_on'] and state['starts_reserved']==2
