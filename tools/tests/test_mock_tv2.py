import importlib.util
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('mock_tv2',Path(__file__).resolve().parents[1]/'mock_tv2.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class MockTest(unittest.TestCase):
    def setUp(self):
        self.root='/api/v1/devices/garden-01'
        self.command=dict(device_id='garden-01',command_seq=4,kind='STOP')
        self.api=m.Contract('test-key',commands=[self.command])

    def test_command_replayed_until_ack_then_removed(self):
        url=self.root+'/commands/next?after_seq=0'
        self.assertEqual(self.api.handle('GET',url,'test-key'),(200,self.command))
        self.assertEqual(self.api.handle('GET',url,'test-key'),(200,self.command))
        ack=dict(device_id='garden-01',command_seq=4,result='duplicate')
        self.assertEqual(self.api.handle('POST',self.root+'/commands/4/ack','test-key',ack)[0],204)
        self.assertEqual(self.api.handle('GET',url,'test-key')[0],204)

    def test_auth_and_wrong_device(self):
        self.assertEqual(self.api.handle('GET',self.root+'/commands/next','bad')[0],401)
        self.assertEqual(self.api.handle('GET','/api/v1/devices/wrong/commands/next','test-key')[0],404)

    def test_event_ack_and_unknown_duration(self):
        event=dict(device_id='garden-01',event_id=1,actual_ms=None,reason='Reboot')
        for _ in range(2):
            self.assertEqual(self.api.handle('POST',self.root+'/events','test-key',event),(200,{'event_id':1}))
        self.assertIsNone(self.api.events[1]['actual_ms'])
        changed=dict(event,actual_ms=0)
        self.assertEqual(self.api.handle('POST',self.root+'/events','test-key',changed)[0],409)

    def test_telemetry_idempotent(self):
        row=dict(device_id='garden-01',boot_id='boot',sample_seq=1,soil_pct=None)
        for _ in range(2):self.assertEqual(self.api.handle('POST',self.root+'/telemetry','test-key',row)[0],200)
        self.assertEqual(len(self.api.telemetry),1)
        self.assertEqual(self.api.handle('POST',self.root+'/telemetry','test-key',dict(row,soil_pct=20))[0],409)
