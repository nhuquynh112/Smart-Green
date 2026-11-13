import json,sys,hashlib
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
out=Path(__file__).parent
config=json.loads(Path('artifacts/backend-local/runtime-env.json').read_text())
conn=psycopg2.connect(config['DATABASE_URL'],connect_timeout=5)
conn.set_session(readonly=True,isolation_level='REPEATABLE READ')
with conn,conn.cursor(cursor_factory=RealDictCursor) as q:
 q.execute("SELECT * FROM telemetry WHERE device_id=%s AND data_origin='real' AND received_at >= %s AND received_at < %s ORDER BY received_at,boot_id,sample_seq",('garden-01','2026-11-12T14:55:00+07:00','2026-11-12T22:55:00+07:00')); rows=q.fetchall()
 q.execute("SELECT * FROM watering_events WHERE device_id=%s AND received_at >= %s AND received_at < %s ORDER BY received_at",('garden-01','2026-11-12T14:55:00+07:00','2026-11-12T22:55:00+07:00'));events=q.fetchall()
conn.close()
with (out/'database-rows.jsonl').open('x') as f:
 for r in rows:f.write(json.dumps(r,default=str,ensure_ascii=False)+'\n')
with (out/'telemetry.jsonl').open('x') as f:
 for r in rows:
  p=r['payload'];p=json.loads(p) if isinstance(p,str) else p
  assert (p['device_id'],p['boot_id'],p['sample_seq'])==(r['device_id'],r['boot_id'],r['sample_seq'])
  f.write(json.dumps(dict(p,received_at=r['received_at'].isoformat()),ensure_ascii=False)+'\n')
(out/'pump-events.json').write_text(json.dumps(events,default=str,indent=2))
print('Exported',len(rows),'samples;',len(events),'pump events')
