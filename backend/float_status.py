"""Independent float observations; never insert sensor samples or control commands."""
import re
from datetime import datetime, timezone
from fastapi import Header, HTTPException
from backend.database import utc_iso


def install(app, db, authenticate):
    db.execute('''CREATE TABLE IF NOT EXISTS float_status (
        device_id TEXT PRIMARY KEY REFERENCES devices(device_id), boot_id TEXT NOT NULL,
        uptime_ms BIGINT NOT NULL, tank_ok INTEGER NOT NULL, received_at TEXT NOT NULL, observed_at TEXT NOT NULL)''')

    @app.post('/api/v1/devices/{device_id}/float-status')
    def post_float_status(device_id: str, body: dict, x_api_key: str | None = Header(default=None)):
        authenticate(db, device_id, x_api_key)
        if (set(body) != {'boot_id','uptime_ms','tank_ok','observed_at'}
            or not isinstance(body['boot_id'],str)
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',body['boot_id'])
            or type(body['uptime_ms']) is not int or not 0 <= body['uptime_ms'] <= 4294967295
            or type(body['tank_ok']) is not bool
            or type(body['observed_at']) is not int):
            raise HTTPException(422, 'Invalid float observation')
        now=datetime.now(timezone.utc)
        age=now.timestamp()-body['observed_at']
        if not -5 <= age <= 90:
            raise HTTPException(409,'Float observation expired or clock unavailable')
        with db.transaction() as conn:
            db.one_on(conn,'SELECT device_id FROM devices WHERE device_id=?'+('' if db.sqlite else ' FOR UPDATE'),(device_id,))
            latest=db.one_on(conn,'SELECT boot_id,uptime_ms FROM telemetry WHERE device_id=? ORDER BY received_at DESC LIMIT 1',(device_id,))
            if not latest or latest['boot_id'] != body['boot_id']:
                raise HTTPException(409,'Wait for telemetry from this boot')
            old=db.one_on(conn,'SELECT * FROM float_status WHERE device_id=?',(device_id,))
            if old and old['boot_id']==body['boot_id'] and ((body['uptime_ms']-old['uptime_ms']) & 0xffffffff) not in range(1,0x80000000):
                return {'accepted':False}  # Retries must not refresh observation age.
            db.execute_on(conn,'''INSERT INTO float_status VALUES(?,?,?,?,?,?)
                ON CONFLICT(device_id) DO UPDATE SET boot_id=excluded.boot_id,uptime_ms=excluded.uptime_ms,
                tank_ok=excluded.tank_ok,received_at=excluded.received_at,observed_at=excluded.observed_at''',
                (device_id,body['boot_id'],body['uptime_ms'],int(body['tank_ok']),utc_iso(now),utc_iso(datetime.fromtimestamp(body['observed_at'],timezone.utc))))
        return {'accepted':True}


def latest_status(db, device_id, telemetry):
    row=db.one('SELECT * FROM float_status WHERE device_id=?',(device_id,))
    if not row or not telemetry or row['boot_id']!=telemetry['boot_id']:
        return None
    if ((row['uptime_ms']-(telemetry.get('uptime_ms') or 0)) & 0xffffffff) >= 0x80000000:
        return None
    row['tank_ok']=bool(row['tank_ok'])
    return row
