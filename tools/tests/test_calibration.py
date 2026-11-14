import copy
import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('calibration',ROOT/'tools/calibration.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class CalibrationTest(unittest.TestCase):
    def setUp(self):self.profile=json.loads((ROOT/'tests/fixtures/calibration_synthetic.json').read_text())
    def test_computes_from_measurements_without_enabling(self):
        r=m.analyze(self.profile)
        self.assertEqual((r['dry_raw'],r['wet_raw']),(2800,1500))
        self.assertEqual(r['pump']['weighted_ml_per_s'],10)
        self.assertEqual(r['target_volume_estimate']['nominal_ms'],1000)
        self.assertFalse(r['hardware_approved'])
        self.assertEqual(len(r['unconfirmed_checks']),4)
    def test_unequal_durations_weight_flow_by_time(self):
        self.profile['pump']['trials']=[dict(duration_s=1,volume_ml=5),dict(duration_s=2,volume_ml=20),dict(duration_s=1,volume_ml=5)]
        self.assertEqual(m.analyze(self.profile)['pump']['weighted_ml_per_s'],7.5)
    def test_reject_invalid_measurements(self):
        for value in (0,-1,float('nan'),True):
            with self.subTest(value=value):
                p=copy.deepcopy(self.profile);p['pump']['trials'][0]['duration_s']=value
                with self.assertRaises(ValueError):m.analyze(p)
        self.profile['wet_raw_samples']=[2795]*5
        with self.assertRaises(ValueError):m.analyze(self.profile)
    def test_checkboxes_do_not_approve_hardware(self):
        self.profile['checks']={k:True for k in self.profile['checks']}
        self.assertFalse(m.analyze(self.profile)['hardware_approved'])
