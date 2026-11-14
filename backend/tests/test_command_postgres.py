"""Opt-in concurrency test; creates and drops its own disposable PostgreSQL DB.

SG_TEST_POSTGRES_ADMIN_URL must point to a role permitted to CREATE DATABASE.
No application database tables are read or written.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app import create_app
from backend.database import Database
from backend.tests.test_api import SyncASGIClient


def test_postgres_request_replay_and_concurrent_fence():
    url = os.getenv('SG_TEST_POSTGRES_ADMIN_URL')
    if not url:
        pytest.skip('Set SG_TEST_POSTGRES_ADMIN_URL to enable isolated PostgreSQL test')
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import parse_dsn, make_dsn
    settings = parse_dsn(url)
    settings['dbname'] = 'postgres'
    name = 'sg_test_' + uuid.uuid4().hex
    admin = psycopg2.connect(**settings)
    admin.autocommit = True
    created = False
    try:
        with admin.cursor() as cur:
            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        created = True
        settings['dbname'] = name
        db = Database(make_dsn(**settings))
        # Emulate the pre-request-ID schema and preserve an old STOP row.
        db.ensure_device('legacy-device', 'test-only')
        db.execute("INSERT INTO commands(device_id,command_seq,kind,issued_at,expires_at) VALUES('legacy-device',1,'STOP',1800000000,1800000030)")
        db.execute("ALTER TABLE commands DROP COLUMN request_id, DROP COLUMN request_fingerprint")
        Database(make_dsn(**settings))
        assert db.one("SELECT command_seq,request_id FROM commands WHERE device_id='legacy-device'")=={'command_seq':1,'request_id':None}
        # Schema upgrade must also be repeatable.
        Database(make_dsn(**settings))
        db.ensure_device('test-device', 'test-only')
        client = SyncASGIClient(create_app(db=db, bundle=None))
        endpoint = '/api/v1/web/devices/test-device/commands'
        body = {'kind':'SET_MODE','mode':'MANUAL','request_id':'same-request-0001','expected_seq':0}
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _:client.post(endpoint,admin=True,json=body), range(4)))
        assert sorted(r.status_code for r in results) == [200,200,200,201]
        assert {r.json()['command_seq'] for r in results} == {1}
        db.execute("UPDATE commands SET status='ACKED',ack_result='mode_set'")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda i:client.post(endpoint,admin=True,json={**body,'expected_seq':1,'request_id':f'different-request-{i}'}),range(2)))
        assert sorted(r.status_code for r in results) == [201,409]
        stop=client.post(endpoint,admin=True,json={'kind':'STOP','request_id':'stop-request-0001','expected_seq':0})
        assert stop.status_code == 201
        delayed=client.post(endpoint,admin=True,json={**body,'request_id':'delayed-request-001','expected_seq':1})
        assert delayed.status_code == 409
        # Replaying an old accepted request never creates or reactivates it.
        replay=client.post(endpoint,admin=True,json=body)
        assert replay.status_code == 200 and replay.json()['command_seq']==1
        assert db.one("SELECT COUNT(*) AS n FROM commands WHERE device_id='test-device'")["n"]==3
    finally:
        if created:
            with admin.cursor() as cur:
                cur.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()
