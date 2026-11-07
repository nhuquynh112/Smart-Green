"""Local contract simulator for TV1. Not the production backend or database."""
import argparse
import hmac
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


class Contract:
    def __init__(self, key, device='garden-01', commands=()):
        self.key, self.device = key, device
        self.commands = list(commands)
        self.acks, self.events, self.telemetry = {}, {}, {}
        ids=[c['command_seq'] for c in self.commands]
        if any(type(x) is not int or x<=0 for x in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Command sequences must be unique positive integers')
        if any(c.get('device_id')!=device for c in self.commands):
            raise ValueError('Command device mismatch')

    def handle(self, method, url, key, body=None):
        if not hmac.compare_digest(key or '', self.key):
            return 401, {'error':'unauthorized'}
        parsed=urlsplit(url)
        root=f'/api/v1/devices/{self.device}'
        if not parsed.path.startswith(root+'/'):
            return 404, {'error':'device_or_route'}
        route=parsed.path[len(root):]
        if method=='GET' and route=='/commands/next':
            try: after=int(parse_qs(parsed.query).get('after_seq',['0'])[0])
            except ValueError:return 400, {'error':'after_seq'}
            pending=[c for c in self.commands if c['command_seq']>after and c['command_seq'] not in self.acks]
            return (200, min(pending,key=lambda c:c['command_seq'])) if pending else (204,None)
        if method!='POST' or not isinstance(body,dict) or body.get('device_id')!=self.device:
            return 400, {'error':'body_or_device'}
        if route=='/telemetry':
            identity=(body.get('boot_id'),body.get('sample_seq'))
            if not isinstance(identity[0],str) or type(identity[1]) is not int or identity[1]<=0:
                return 400, {'error':'identity'}
            if identity in self.telemetry and self.telemetry[identity]!=body:
                return 409, {'error':'identity_conflict'}
            self.telemetry[identity]=body
            return 200, {'stored':True}
        if route=='/events':
            event_id=body.get('event_id')
            if type(event_id) is not int or event_id<=0:return 400, {'error':'event_id'}
            if event_id in self.events and self.events[event_id]!=body:return 409, {'error':'event_conflict'}
            self.events[event_id]=body
            return 200, {'event_id':event_id}
        parts=route.strip('/').split('/')
        if len(parts)==3 and parts[0]=='commands' and parts[2]=='ack':
            try: seq=int(parts[1])
            except ValueError:return 400, {'error':'sequence'}
            if body.get('command_seq')!=seq or not isinstance(body.get('result'),str):return 400, {'error':'ack'}
            if seq not in {c['command_seq'] for c in self.commands}:return 404, {'error':'unknown_command'}
            self.acks.setdefault(seq,body)
            return 204,None
        return 404, {'error':'route'}


def make_server(contract, host='127.0.0.1', port=0, faults=None):
    """Fault injection is only for host tests; never connect a real pump to this mock."""
    faults={} if faults is None else faults
    lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def respond(self):
            body=None
            if self.command=='POST':
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=4096:raise ValueError()
                    body=json.loads(self.rfile.read(size))
                except (ValueError,UnicodeDecodeError):
                    self.send_error(400);return
            route=urlsplit(self.path).path
            with lock:
                steps=faults.get((self.command,route),[])
                fault=steps.pop(0) if steps else {}
            if fault.get('delay'):
                time.sleep(fault['delay'])
            with lock:
                if 'status' in fault:
                    code,result=fault['status'],{'error':'injected_fault'}
                else:
                    code,result=contract.handle(self.command,self.path,self.headers.get('X-API-Key',''),body)
            if fault.get('drop_after_store'):
                self.close_connection=True
                try:self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:pass
                return
            payload=json.dumps(result).encode() if result is not None else b''
            self.send_response(code);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(payload)));self.end_headers()
            try:self.wfile.write(payload)
            except (BrokenPipeError,ConnectionResetError):pass
        do_GET=respond
        do_POST=respond
        def log_message(self, *_):
            pass
        def setup(self):
            super().setup();self.connection.settimeout(3)

    return HTTPServer((host,port),Handler)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,default=8000)
    p.add_argument('--device',default='garden-01')
    p.add_argument('--commands',type=Path)
    args=p.parse_args()
    key=os.environ.get('SMART_GREEN_MOCK_KEY')
    if not key:p.error('Set SMART_GREEN_MOCK_KEY locally; do not use production API keys')
    commands=json.loads(args.commands.read_text()) if args.commands else []
    contract=Contract(key,args.device,commands)

    print(f'MOCK ONLY listening on {args.host}:{args.port}; in-memory state is lost on exit. No pump connected.')
    with make_server(contract,args.host,args.port) as server:
        try:server.serve_forever()
        except KeyboardInterrupt:pass


if __name__=='__main__':main()
