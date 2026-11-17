import io,json,zipfile,os,uuid
from datetime import datetime,timedelta,timezone
import pytest
from fastapi import HTTPException
from backend.app import create_app
from backend.database import Database
from backend.collection_sessions import checked_document

@pytest.fixture(params=['sqlite','postgres'])
def system(request):
    admin=None;name=None
    if request.param=='postgres':
        url=os.getenv('SG_TEST_POSTGRES_ADMIN_URL')
        if not url:pytest.skip('Set SG_TEST_POSTGRES_ADMIN_URL for disposable PostgreSQL tests')
        import psycopg2
        from psycopg2 import sql
        from psycopg2.extensions import parse_dsn,make_dsn
        admin=psycopg2.connect(url);admin.autocommit=True;name='sg_session_'+uuid.uuid4().hex
        with admin.cursor() as cur:cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        settings=parse_dsn(url);settings['dbname']=name
        db=Database(make_dsn(**settings))
    else:db=Database('sqlite:///:memory:')
    db.ensure_device('garden','test','cal');app=create_app(db=db)
    routes={r.name:r.endpoint for r in app.routes if hasattr(r,'endpoint')}
    yield db,app,routes
    db.close()
    if admin:
        with admin.cursor() as cur:cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        admin.close()

def document():
    now=datetime.now(timezone.utc)
    return dict(name='W05',start=(now-timedelta(hours=2)).isoformat(),end=None,calibration_id='cal',last_watered_at_before_start=(now-timedelta(days=1)).isoformat(),events=[],unknown_intervals=[],notes='',history_complete=False)

def save(system,doc,revision=0,sid='a'*32):
    return system[2]['save_session']('garden',sid,dict(revision=revision,document=doc),username='tester')

def test_retries_versions_single_active(system):
    doc=document();assert save(system,doc)['revision']==1;assert save(system,doc)['revision']==1
    with pytest.raises(HTTPException) as err:save(system,doc,sid='b'*32)
    assert err.value.status_code==409
    doc['notes']='new'
    with pytest.raises(HTTPException) as err:save(system,doc)
    assert err.value.status_code==409
    assert save(system,doc,1)['revision']==2
    assert system[0].one('SELECT count(*) AS n FROM collection_session_revisions')['n']==2
    assert system[0].one('SELECT count(*) AS n FROM commands')['n']==0

def test_export_bounds_and_preserves_telemetry(system):
    db,_,routes=system;doc=document();doc['end']=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat();doc['history_complete']=True;save(system,doc)
    for seq,stamp in enumerate([doc['start'],doc['end']],1):
        db.execute('INSERT INTO telemetry(device_id,boot_id,sample_seq,received_at,data_origin,payload) VALUES(?,?,?,?,?,?)',('garden','boot',seq,stamp.replace('+00:00','Z'),'real','{}'))
    response=routes['export_session']('garden','a'*32)
    with zipfile.ZipFile(io.BytesIO(response.body)) as z:
        assert json.loads(z.read('session.json'))['rows']==1
        assert json.loads(z.read('journal.json'))['history_complete'] is True
    assert db.one('SELECT count(*) AS n FROM telemetry')['n']==2

def test_export_active_and_wrong_device(system):
    save(system,document())
    with pytest.raises(HTTPException) as err:system[2]['export_session']('garden','a'*32)
    assert err.value.status_code==409
    with pytest.raises(HTTPException) as err:system[2]['export_session']('other','a'*32)
    assert err.value.status_code==404

def test_validation():
    doc=document();doc['history_complete']=True
    with pytest.raises(ValueError):checked_document(doc,'garden')
    doc['end']=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat();doc['unknown_intervals']=[dict(start=doc['start'],end=doc['end'])]
    assert checked_document(doc,'garden')['unknown_intervals']
    doc['events']=[dict(event_id='e1',started_at=doc['start'],ended_at=doc['end'],method='hand',actual_ms=None,volume_ml=-1)]
    with pytest.raises(ValueError):checked_document(doc,'garden')

def test_auth_and_backup(system,tmp_path):
    from backend.backup_db import create_backup
    db,app,_=system
    for route in app.routes:
        if '/sessions' in getattr(route,'path',''):
            assert any(d.call.__name__=='_admin_auth' for d in route.dependant.dependencies)
    save(system,document());backup=json.loads(create_backup(db,tmp_path).read_text())
    assert len(backup['tables']['collection_sessions'])==1
    assert len(backup['tables']['collection_session_revisions'])==1


def test_automatic_start_finish_preserves_server_times_and_no_pump(system):
    db,_,routes=system
    before=datetime.now(timezone.utc)
    row=routes['start_session']('garden','c'*32,username='tester')
    assert before <= datetime.fromisoformat(row['start']) <= datetime.now(timezone.utc)
    assert row['calibration_id']=='cal' and row['end'] is None
    assert row['history_complete'] is False and row['last_watered_at_before_start'] is None
    assert routes['start_session']('garden','c'*32,username='tester')==row
    with pytest.raises(HTTPException) as err:
        routes['start_session']('garden','d'*32,username='tester')
    assert err.value.status_code==409
    doc={k:v for k,v in row.items() if k not in ('session_id','device_id','revision')}
    doc['notes']='hand watering not yet reconciled'
    updated=save(system,doc,1,'c'*32)
    with pytest.raises(HTTPException) as err:
        routes['finish_session']('garden','c'*32,{'revision':1},username='tester')
    assert err.value.status_code==409
    finished=routes['finish_session']('garden','c'*32,{'revision':updated['revision']},username='tester')
    assert finished['end']>row['start'] and finished['history_complete'] is False
    assert finished['notes']==doc['notes']
    assert routes['finish_session']('garden','c'*32,{'revision':updated['revision']},username='tester')==finished
    assert db.one('SELECT count(*) AS n FROM collection_session_revisions')['n']==3
    assert db.one('SELECT count(*) AS n FROM commands')['n']==0
    assert db.one('SELECT count(*) AS n FROM telemetry')['n']==0
    assert routes['start_session']('garden','d'*32,username='tester')['end'] is None


def test_w05_observations_export_and_bounds(system):
    doc=document();doc['end']=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat()
    doc['observations']=[dict(at=doc['start'],kind='shade_start',note='Covered light sensor only'),dict(at=doc['end'],kind='shade_end',note='Removed cover')]
    row=save(system,doc)
    assert row['observations']==doc['observations']
    response=system[2]['export_session']('garden','a'*32)
    with zipfile.ZipFile(io.BytesIO(response.body)) as z:
        assert json.loads(z.read('journal.json'))['observations']==doc['observations']
    assert system[0].one('SELECT count(*) AS n FROM commands')['n']==0
    doc['observations'][0]['at']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError):checked_document(doc,'garden')


def test_list_sessions_orders_actual_time_across_offsets(system):
    # 10:00 +07 is earlier than 04:00 UTC despite its larger text representation.
    first = document()
    first.update(start='2026-01-01T10:00:00+07:00', end='2026-01-01T10:30:00+07:00',
                 last_watered_at_before_start=None)
    second = dict(first, start='2026-01-01T04:00:00Z', end='2026-01-01T04:30:00Z')
    save(system, first, sid='e'*32)
    save(system, second, sid='f'*32)
    rows = system[2]['list_sessions']('garden')
    assert [r['session_id'] for r in rows] == ['f'*32, 'e'*32]
