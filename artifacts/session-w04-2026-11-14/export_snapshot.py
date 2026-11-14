"""Read-only bounded W04 snapshot; bounds are observed, pending user session journal."""
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
out=Path(__file__).parent
config=json.loads(Path('artifacts/backend-local/runtime-env.json').read_text())
start='2026-11-14T10:15:00+07:00'
end='2026-11-14T21:12:00+07:00'
c=psycopg2.connect(config['DATABASE_URL'],connect_timeout=5)
c.set_session(readonly=True,isolation_level='REPEATABLE READ')
with c,c.cursor(cursor_factory=RealDictCursor) as q:
 q.execute("SELECT * FROM telemetry WHERE device_id=%s AND data_origin='real' AND received_at >= %s AND received_at <= %s ORDER BY received_at,boot_id,sample_seq",('garden-01',start,end));rows=q.fetchall()
 q.execute("SELECT * FROM watering_events WHERE device_id=%s AND received_at >= %s AND received_at <= %s ORDER BY received_at",('garden-01',start,end));events=q.fetchall()
c.close()
with (out/'database-rows.jsonl').open('x') as f:
 for r in rows:f.write(json.dumps(r,default=str,ensure_ascii=False)+'\n')
with (out/'telemetry.jsonl').open('x') as f:
 for r in rows:
  p=r['payload'];p=json.loads(p) if isinstance(p,str) else p
  assert (p['device_id'],p['boot_id'],p['sample_seq'])==(r['device_id'],r['boot_id'],r['sample_seq'])
  f.write(json.dumps(dict(p,received_at=r['received_at'].isoformat()),ensure_ascii=False)+'\n')
with (out/'pump-events.json').open('x') as f:json.dump(events,f,default=str,indent=2)
(out/'snapshot-scope.json').write_text(json.dumps(dict(start_inclusive=start,end_inclusive=end,rows=len(rows),pump_events=len(events),journal_status='handoff_nominal_times_with_uncertainty',note='Bounds from W04 handoff; watering event 2 time approximate.'),indent=2)+'\n')
print('Exported',len(rows),'samples;',len(events),'pump events')
