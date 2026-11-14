"""Real loopback HTTP + shared C++ core. Does not emulate ESP32 scheduling/NVS/Wi-Fi."""
import http.client
from http.client import RemoteDisconnected
import importlib.util
import json
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mock_tv2',ROOT/'tools/mock_tv2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
NOW=1800000001
ROOT_URL='/api/v1/devices/garden-01'


def command(seq, kind='WATER', **kwargs):
    return dict(schema_version=1,device_id='garden-01',command_seq=seq,kind=kind,
                issued_at=NOW-1,expires_at=NOW+59,source='MANUAL',duration_ms=1000,**kwargs)


@pytest.fixture(scope='session')
def binary(tmp_path_factory):
    output=tmp_path_factory.mktemp('native')/'runtime_bridge'
    headers=ROOT/'firmware/.pio/libdeps/bringup/ArduinoJson/src'
    if not headers.exists():headers=ROOT/'firmware/.pio/libdeps/esp32dev/ArduinoJson/src'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'firmware/include'),
                    '-I'+str(headers),str(ROOT/'firmware/test/native/runtime_bridge.cpp'),'-o',str(output)],check=True)
    return output


@pytest.fixture
def core(binary):
    process=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1)
    def call(op='tick',ms=2000,**kwargs):
        process.stdin.write(json.dumps(dict(op=op,ms=ms,utc=NOW,**kwargs))+'\n');process.stdin.flush()
        result=process.stdout.readline()
        assert result, 'native simulator exited'
        return json.loads(result)
    yield call
    process.stdin.close();process.wait(timeout=3);process.stdout.close()
    assert process.returncode==0


@pytest.fixture
def backend():
    resources=[]
    def start(commands=(),faults=None):
        api=m.Contract('test-key',commands=commands)
        server=m.make_server(api,faults=faults)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
        resources.append((server,thread))
        def request(method,path,body=None,key='test-key',timeout=1):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=timeout)
            data=json.dumps(body) if body is not None else None
            try:
                conn.request(method,ROOT_URL+path,data,headers={'X-API-Key':key,'Content-Type':'application/json'})
                response=conn.getresponse();payload=response.read()
                return response.status,json.loads(payload) if payload else None
            finally:conn.close()
        return api,request
    yield start
    for server,thread in resources:
        server.shutdown();server.server_close();thread.join(timeout=2)


def manual(core):
    assert core('command',payload=command(1,'SET_MODE',mode='MANUAL'))['result']=='mode_set'


def test_lost_command_ack_reboot_and_event_recovery(core,backend):
    manual(core)
    water=command(2)
    _,http=backend([water],{('POST',ROOT_URL+'/commands/2/ack'):[{'status':503}]})
    status,payload=http('GET','/commands/next?after_seq=0');assert status==200
    result=core('command',ms=3000,payload=payload);assert result['pump_on']
    ack=dict(schema_version=1,device_id='garden-01',command_seq=2,result=result['result'])
    assert http('POST','/commands/2/ack',ack)[0]==503
    # Reset while pumping: persistent-state simulator retains command/event, physical duration unknown.
    reboot=core('reboot',ms=0);assert not reboot['pump_on']
    assert reboot['events'][0]['reason']=='Reboot' and reboot['events'][0]['actual_ms'] is None
    _,payload=http('GET','/commands/next?after_seq=0')
    replay=core('command',ms=2000,payload=payload)
    assert replay['result']=='duplicate' and replay['starts_reserved']==1 and not replay['pump_on']
    ack['result']=replay['result'];assert http('POST','/commands/2/ack',ack)[0]==204
    assert http('GET','/commands/next?after_seq=0')[0]==204
    event=replay['events'][0]
    status,received=http('POST','/events',event);assert status==200
    assert core('ack_event',event_id=received['event_id'])['events']==[]


def test_server_slow_core_still_can_stop_and_telemetry_retries(core,backend):
    manual(core);assert core('command',ms=3000,payload=command(2))['pump_on']
    api,http=backend(faults={('POST',ROOT_URL+'/telemetry'):[{'delay':.25}]})
    row=dict(device_id='garden-01',boot_id='SIM',sample_seq=1,soil_pct=20)
    with pytest.raises((TimeoutError,socket.timeout)):http('POST','/telemetry',row,timeout=.04)
    # We drive virtual core time: proves core has no HTTP dependency, not real ESP32 latency.
    stopped=core(ms=4000);assert not stopped['pump_on'] and stopped['events'][0]['reason']=='Duration'
    time.sleep(.3)
    assert http('POST','/telemetry',row)[0]==200
    assert len(api.telemetry)==1


def test_event_saved_but_response_lost_is_idempotent(core,backend):
    manual(core);core('command',ms=3000,payload=command(2));event=core(ms=4000)['events'][0]
    api,http=backend(faults={('POST',ROOT_URL+'/events'):[{'drop_after_store':True}]})
    with pytest.raises((RemoteDisconnected,ConnectionResetError)):
        http('POST','/events',event)
    assert len(core()['events'])==1
    status,ack=http('POST','/events',event);assert status==200 and len(api.events)==1
    assert core('ack_event',event_id=ack['event_id'])['acknowledged']


def test_expired_wrong_device_and_auth_never_start(core,backend):
    manual(core);expired=command(2);expired['expires_at']=NOW
    assert core('command',payload=expired)['result']=='expired_or_clock'
    wrong=command(3);wrong['device_id']='other'
    assert core('command',payload=wrong)['result']=='device'
    _,http=backend([command(4)])
    assert http('GET','/commands/next?after_seq=0',key='bad')[0]==401
    assert not core()['pump_on']


def test_auto_without_server_respects_empty_tank(core):
    assert core('command',payload=command(1,'SET_MODE',mode='AUTO'))['result']=='mode_set'
    for ms in (3000,4000,5000):state=core(ms=ms,tank_ok=False)
    assert not state['pump_on']
    state=core(ms=6000,tank_ok=True);assert state['pump_on']
    assert not core(ms=6100,tank_ok=False)['pump_on']
