"""Reviewed collection journals. Never issues device commands or mutates telemetry."""
from datetime import datetime, timezone
from pathlib import Path
import csv
import io
import json
import re
import sys
import zipfile

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from backend.database import canonical_json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from watering_journal import instant, validate_journal


def checked_document(body, device_id, now=None):
    now = now or datetime.now(timezone.utc)
    allowed = {'name', 'start', 'end', 'calibration_id', 'last_watered_at_before_start',
               'events', 'unknown_intervals', 'notes', 'history_complete', 'observations'}
    if set(body) - allowed:
        raise ValueError('Trường nhật ký không hợp lệ')
    if not isinstance(body.get('name'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', body['name']):
        raise ValueError('Tên phiên dùng 1–40 chữ, số, dấu - hoặc _')
    start = instant(body.get('start'))
    end = instant(body['end']) if body.get('end') else None
    if start > now or (end and end > now):
        raise ValueError('Không ghi phiên ở thời điểm tương lai')
    if not isinstance(body.get('notes', ''), str) or len(body.get('notes', '')) > 4000:
        raise ValueError('Ghi chú tối đa 4000 ký tự')
    if type(body.get('history_complete', False)) is not bool:
        raise ValueError('Xác nhận nhật ký phải là boolean')
    if body.get('history_complete') and end is None:
        raise ValueError('Chỉ xác nhận nhật ký sau khi kết thúc phiên')
    j = dict(schema_version=1, device_id=device_id, calibration_id=body.get('calibration_id'),
             data_origin='real', coverage_start=start.isoformat(), coverage_end=(end or now).isoformat(),
             history_complete=body.get('history_complete', False),
             last_watered_at_before_start=body.get('last_watered_at_before_start'),
             events=body.get('events', []), unknown_intervals=body.get('unknown_intervals', []))
    validate_journal(j)
    observations = body.get('observations', [])
    kinds = {'shade_start', 'shade_end', 'light_change', 'plant_move', 'sensor_move', 'power_loss', 'reset', 'other'}
    if not isinstance(observations, list) or len(observations) > 500:
        raise ValueError('Tối đa 500 mốc thực nghiệm mỗi phiên')
    for item in observations:
        if not isinstance(item, dict) or set(item) != {'at', 'kind', 'note'}:
            raise ValueError('Mốc thực nghiệm cần at, kind, note')
        if not isinstance(item['kind'], str) or item['kind'] not in kinds:
            raise ValueError('Loại mốc thực nghiệm không hợp lệ')
        if not start <= instant(item['at']) <= (end or now):
            raise ValueError('Mốc thực nghiệm ngoài thời gian phiên')
        if not isinstance(item['note'], str) or len(item['note']) > 1000:
            raise ValueError('Ghi chú mốc tối đa 1000 ký tự')
    return dict(name=body['name'], start=start.isoformat(), end=end.isoformat() if end else None,
                calibration_id=j['calibration_id'], last_watered_at_before_start=j['last_watered_at_before_start'],
                events=j['events'], unknown_intervals=j['unknown_intervals'],
                history_complete=j['history_complete'], notes=body.get('notes', ''), observations=observations)


def install_session_routes(app, db, admin_auth):
    # Called only on next backend start. Identical TEXT schema works on SQLite/PG.
    db.execute('''CREATE TABLE IF NOT EXISTS collection_sessions (
        session_id TEXT PRIMARY KEY, device_id TEXT NOT NULL REFERENCES devices(device_id),
        revision INTEGER NOT NULL, active INTEGER NOT NULL, document TEXT NOT NULL)''')
    db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS collection_sessions_active_device
        ON collection_sessions(device_id) WHERE active=1''')
    db.execute('''CREATE TABLE IF NOT EXISTS collection_session_revisions (
        session_id TEXT NOT NULL REFERENCES collection_sessions(session_id), revision INTEGER NOT NULL,
        document TEXT NOT NULL, reviewed_by TEXT NOT NULL, saved_at TEXT NOT NULL,
        PRIMARY KEY(session_id,revision))''')

    def unpack(row):
        return dict(session_id=row['session_id'], device_id=row['device_id'], revision=row['revision'],
                    **json.loads(row['document']))

    @app.get('/api/v1/web/devices/{device_id}/sessions')
    def list_sessions(device_id: str, _: str = Depends(admin_auth)):
        rows = db.all('SELECT * FROM collection_sessions WHERE device_id=?', (device_id,))
        return sorted([unpack(r) for r in rows], key=lambda r: r['start'], reverse=True)

    @app.put('/api/v1/web/devices/{device_id}/sessions/{session_id}')
    def save_session(device_id: str, session_id: str, body: dict, username: str = Depends(admin_auth)):
        if not re.fullmatch(r'[a-f0-9]{32}', session_id):
            raise HTTPException(400, 'Mã phiên không hợp lệ')
        revision = body.get('revision')
        if type(revision) is not int or revision < 0 or set(body) != {'revision','document'}:
            raise HTTPException(400, 'Cần revision và document hợp lệ')
        try:
            doc = checked_document(body['document'], device_id)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise HTTPException(400, str(exc))
        encoded = canonical_json(doc)
        with db.transaction() as conn:
            device = db.one_on(conn, 'SELECT device_id FROM devices WHERE device_id=?'+('' if db.sqlite else ' FOR UPDATE'), (device_id,))
            if not device:
                raise HTTPException(404, 'Không tìm thấy thiết bị')
            old = db.one_on(conn, 'SELECT * FROM collection_sessions WHERE session_id=?', (session_id,))
            if old and old['device_id'] != device_id:
                raise HTTPException(404, 'Không tìm thấy phiên')
            # Retries after lost responses must not create duplicate records/revisions.
            if old and old['document'] == encoded and old['revision'] == revision+1:
                return unpack(old)
            if (old['revision'] if old else 0) != revision:
                raise HTTPException(409, 'Phiên đã được sửa ở nơi khác; tải lại trước khi lưu')
            if not doc['end']:
                other = db.one_on(conn, 'SELECT session_id FROM collection_sessions WHERE device_id=? AND active=1 AND session_id<>?', (device_id,session_id))
                if other:
                    raise HTTPException(409, 'Thiết bị đang có một phiên chưa kết thúc')
            new_revision = revision+1
            if old:
                db.execute_on(conn, 'UPDATE collection_sessions SET revision=?,active=?,document=? WHERE session_id=?',
                              (new_revision,int(doc['end'] is None),encoded,session_id))
            else:
                db.execute_on(conn, 'INSERT INTO collection_sessions VALUES(?,?,?,?,?)',
                              (session_id,device_id,new_revision,int(doc['end'] is None),encoded))
            db.execute_on(conn, 'INSERT INTO collection_session_revisions VALUES(?,?,?,?,?)',
                          (session_id,new_revision,encoded,username,datetime.now(timezone.utc).isoformat()))
        return dict(session_id=session_id,device_id=device_id,revision=new_revision,**doc)

    @app.post('/api/v1/web/devices/{device_id}/sessions/{session_id}/start')
    def start_session(device_id: str, session_id: str, username: str = Depends(admin_auth)):
        # Client-generated ID makes a retry after a lost response safe.
        if not re.fullmatch(r'[a-f0-9]{32}', session_id):
            raise HTTPException(400, 'Mã phiên không hợp lệ')
        old = db.one('SELECT * FROM collection_sessions WHERE session_id=?', (session_id,))
        if old:
            if old['device_id'] != device_id:
                raise HTTPException(404, 'Không tìm thấy phiên')
            return unpack(old)
        device = db.one('SELECT * FROM devices WHERE device_id=?', (device_id,))
        if not device:
            raise HTTPException(404, 'Không tìm thấy thiết bị')
        latest = db.one("SELECT calibration_id FROM telemetry WHERE device_id=? AND data_origin='real' ORDER BY received_at DESC LIMIT 1", (device_id,))
        calibration = (latest or {}).get('calibration_id') or device.get('calibration_id')
        if not calibration:
            raise HTTPException(409, 'Thiết bị chưa có mã hiệu chuẩn; kiểm tra trước khi bắt đầu')
        now = datetime.now(timezone.utc)
        doc = dict(name='W-'+now.strftime('%Y%m%d-%H%M%S')+'-'+session_id[:4],
                   start=now.isoformat(), end=None, calibration_id=calibration,
                   last_watered_at_before_start=None, events=[], unknown_intervals=[],
                   notes='', history_complete=False)
        return save_session(device_id, session_id, dict(revision=0, document=doc), username)

    @app.post('/api/v1/web/devices/{device_id}/sessions/{session_id}/finish')
    def finish_session(device_id: str, session_id: str, body: dict, username: str = Depends(admin_auth)):
        revision = body.get('revision')
        if set(body) != {'revision'} or type(revision) is not int or revision < 1:
            raise HTTPException(400, 'Cần revision hợp lệ')
        old = db.one('SELECT * FROM collection_sessions WHERE session_id=? AND device_id=?', (session_id, device_id))
        if not old:
            raise HTTPException(404, 'Không tìm thấy phiên')
        doc = json.loads(old['document'])
        if doc['end']:
            if old['revision'] in (revision, revision+1):
                return unpack(old)
            raise HTTPException(409, 'Phiên đã được sửa; tải lại trước khi tiếp tục')
        if old['revision'] != revision:
            raise HTTPException(409, 'Phiên đã được sửa; tải lại trước khi kết thúc')
        doc['end'] = datetime.now(timezone.utc).isoformat()
        doc['history_complete'] = False  # Ending acquisition is not a review of hand watering.
        return save_session(device_id, session_id, dict(revision=revision, document=doc), username)

    @app.get('/api/v1/web/devices/{device_id}/sessions/{session_id}/export')
    def export_session(device_id: str, session_id: str, _: str = Depends(admin_auth)):
        with db.transaction() as conn:
            if not db.sqlite:
                db.execute_on(conn, 'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            row = db.one_on(conn, 'SELECT * FROM collection_sessions WHERE session_id=? AND device_id=?', (session_id,device_id))
            if not row:
                raise HTTPException(404, 'Không tìm thấy phiên')
            doc = unpack(row)
            if not doc['end']:
                raise HTTPException(409, 'Kết thúc phiên trước khi xuất dữ liệu')
            # Match existing W01–W03 reception-based session boundaries, normalize UTC.
            start,end = [instant(doc[k]).astimezone(timezone.utc).isoformat().replace('+00:00','Z') for k in ['start','end']]
            rows = db.all_on(conn, "SELECT * FROM telemetry WHERE device_id=? AND data_origin='real' AND received_at>=? AND received_at<? ORDER BY received_at", (device_id,start,end))
        j = dict(schema_version=1,device_id=device_id,calibration_id=doc['calibration_id'],data_origin='real',
                 coverage_start=doc['start'],coverage_end=doc['end'],history_complete=doc['history_complete'],
                 last_watered_at_before_start=doc['last_watered_at_before_start'],events=doc['events'],
                 unknown_intervals=doc['unknown_intervals'],notes=[doc['notes']],observations=doc.get('observations', []))
        buf=io.BytesIO(); csvbuf=io.StringIO()
        columns=['received_at','measured_at','soil_pct','temperature_c','humidity_pct','soil_raw','light_raw']
        writer=csv.DictWriter(csvbuf,fieldnames=columns);writer.writeheader()
        for r in rows: writer.writerow({c:r.get(c) for c in columns})
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('journal.json',json.dumps(j,ensure_ascii=False,indent=2))
            z.writestr('session.json',json.dumps(dict(**doc,rows=len(rows),selection='received_at: start inclusive, end exclusive; raw real samples; not filtered by calibration'),ensure_ascii=False,indent=2))
            z.writestr('telemetry.csv',csvbuf.getvalue())
            z.writestr('database-rows.jsonl',''.join(json.dumps(r,default=str,ensure_ascii=False)+'\n' for r in rows))
        return Response(buf.getvalue(),media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{doc["name"]}-{session_id[:8]}.zip"'})
