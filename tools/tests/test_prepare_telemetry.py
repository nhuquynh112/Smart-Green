import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prepare_telemetry', ROOT / 'tools/prepare_telemetry.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrepareTest(unittest.TestCase):
    def record(self, seq=1):
        return dict(device_id='test',boot_id='boot',sample_seq=seq,uptime_ms=seq*3000,
                    calibration_id='unset',data_origin='synthetic',soil_raw=2500,light_raw=900,
                    soil_valid=False,soil_pct=None,air_valid=True,temperature_c=30.,humidity_pct=60.,
                    light_lux=None,tank_ok=False,pump_on=False,timestamp=None,
                    received_at=f'2026-11-06T05:00:{seq*3:02d}+00:00')

    def run_rows(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.jsonl'
            p.write_text('\n'.join(x if isinstance(x,str) else json.dumps(x) for x in lines))
            return module.prepare(p)

    def test_broken_duplicate_and_gap(self):
        rows, _, report = self.run_rows([self.record(), 'corrupt', self.record(), self.record(3)])
        self.assertEqual(len(rows),2)
        self.assertEqual(report['duplicates_removed'],1)
        self.assertEqual(len(report['rejected']),1)
        self.assertEqual(report['sequence_issues'][0]['missing'],1)
        self.assertIsNone(rows[0]['timestamp'])
        self.assertIsNone(rows[0]['soil_pct'])

    def test_conflict_not_silently_overwritten(self):
        r=self.record(); conflict=copy.deepcopy(r);conflict['soil_raw']=2000
        rows,_,report=self.run_rows([r,conflict])
        self.assertEqual(rows[0]['soil_raw'],2500)
        self.assertIn('conflicting',report['rejected'][0]['reason'])

    def test_reject_bad_types_time_and_nan(self):
        cases=[]
        for key,value in [('sample_seq',True),('tank_ok','false'),('soil_raw',5000),
                          ('temperature_c',float('nan')),('received_at','2026-11-06T05:00:00'),
                          ('soil_pct',10)]:
            r=self.record();r[key]=value;cases.append(r)
        rows,_,report=self.run_rows(cases)
        self.assertEqual(rows,[])
        self.assertEqual(len(report['rejected']),len(cases))

    def test_reboot_is_separate_session(self):
        a=self.record();b=self.record();b['boot_id']='another'
        rows,_,report=self.run_rows([a,b])
        self.assertEqual(len(rows),2)
        self.assertEqual(report['sessions'],2)
        self.assertFalse(report['sequence_issues'])

    def test_reversed_clock_reported(self):
        a=self.record();b=self.record(2);b['received_at']='2026-11-06T05:00:00+00:00'
        _,_,report=self.run_rows([a,b])
        self.assertEqual(len(report['time_issues']),1)

    def test_missing_fields_and_partial_invalid_air_rejected(self):
        a=self.record(); del a['soil_pct']
        b=self.record(); b.update(air_valid=False, temperature_c=None)
        rows,_,report=self.run_rows([a,b])
        self.assertEqual(rows, [])
        self.assertEqual(len(report['rejected']), 2)

    def test_legacy_missing_time_is_not_fabricated(self):
        r=self.record(); del r['received_at']; del r['timestamp']
        rows,_,report=self.run_rows([r])
        self.assertNotIn('received_at', rows[0])
        self.assertEqual(report['missing']['timestamp'],1)
        self.assertEqual(report['missing']['received_at'],1)

    def test_equal_host_time_is_valid_for_batched_serial_read(self):
        a=self.record(); b=self.record(2); b['received_at']=a['received_at']
        _,_,report=self.run_rows([a,b])
        self.assertEqual(report['time_issues'],[])

    def test_duplicate_json_keys_rejected(self):
        raw=json.dumps(self.record()).replace('"sample_seq": 1', '"sample_seq": 1, "sample_seq": 2')
        rows,_,report=self.run_rows([raw])
        self.assertEqual(rows,[])
        self.assertIn('duplicate JSON key',report['rejected'][0]['reason'])

    def test_cross_file_dedup_and_csv_export(self):
        import csv
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a.log'; b=Path(tmp)/'b.log'
            a.write_text(json.dumps(self.record()))
            replay=self.record(); replay['received_at']='2026-11-06T06:00:00Z'
            b.write_text(json.dumps(replay))
            rows,columns,report=module.prepare([a,b])
            self.assertEqual(len(rows),1)
            self.assertEqual(report['duplicates_removed'],1)
            prefix=Path(tmp)/'clean'
            module.export(rows,columns,report,prefix)
            with prefix.with_suffix('.postgres.csv').open() as f:
                saved=list(csv.DictReader(f))
            self.assertEqual(json.loads(saved[0]['payload']),self.record())
            self.assertEqual(saved[0]['measured_at'],'')


if __name__ == '__main__':
    unittest.main()
