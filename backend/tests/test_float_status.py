import time
from backend.tests.test_api import client, db, telemetry, headers, DEVICE


def test_float_does_not_create_or_modify_sensor_samples(client,db):
    t=telemetry();assert client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=t).status_code==200
    route=f'/api/v1/devices/{DEVICE}/float-status'
    body={'boot_id':t['boot_id'],'uptime_ms':100000,'tank_ok':False,'observed_at':int(time.time())}
    assert client.post(route,headers=headers(),json=body).status_code==200
    d=client.get(f'/api/v1/web/devices/{DEVICE}/dashboard').json()
    assert d['float_status']['tank_ok'] is False
    assert len(d['history'])==1 and d['latest']['soil_raw']==t['soil_raw']
    before=db.one('SELECT * FROM float_status WHERE device_id=?',(DEVICE,))
    assert client.post(route,headers=headers(),json=body).json()['accepted'] is False
    assert db.one('SELECT * FROM float_status WHERE device_id=?',(DEVICE,))==before
    bad={**body,'boot_id':'wrong-boot'}
    assert client.post(route,headers=headers(),json=bad).status_code==409
    assert client.post(route,headers={},json=body).status_code==401
    assert client.post(route,headers=headers(),json={**body,'tank_ok':1}).status_code==422


def test_old_boot_float_not_used(client):
    t=telemetry();client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=t)
    client.post(f'/api/v1/devices/{DEVICE}/float-status',headers=headers(),json={'boot_id':t['boot_id'],'uptime_ms':100000,'tank_ok':False,'observed_at':int(time.time())})
    t=telemetry(2);t['boot_id']='new-boot';client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=t)
    assert client.get(f'/api/v1/web/devices/{DEVICE}/dashboard').json()['float_status'] is None


def test_delayed_or_older_float_cannot_override_newer_observation(client,db):
    t=telemetry();client.post(f'/api/v1/devices/{DEVICE}/telemetry',headers=headers(),json=t)
    route=f'/api/v1/devices/{DEVICE}/float-status'
    b={'boot_id':t['boot_id'],'uptime_ms':100000,'tank_ok':False,'observed_at':int(time.time())}
    assert client.post(route,headers=headers(),json=b).status_code==200
    assert client.post(route,headers=headers(),json={**b,'uptime_ms':99999,'tank_ok':True}).json()['accepted'] is False
    assert client.post(route,headers=headers(),json={**b,'observed_at':int(time.time())-120}).status_code==409
    assert db.one('SELECT tank_ok FROM float_status WHERE device_id=?',(DEVICE,))['tank_ok']==0
