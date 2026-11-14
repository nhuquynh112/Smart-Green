"""Exercise logger validation without opening a physical serial port."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from capture_serial import decode_sample
import test_prepare_telemetry as fixtures


class CaptureTest(unittest.TestCase):
    def test_host_time_preserves_device_time(self):
        record = fixtures.PrepareTest().record()
        measured = '2026-11-06T05:00:00Z'
        record['timestamp'] = measured
        received = '2026-11-06T05:00:01+00:00'
        saved = decode_sample(json.dumps(record).encode(), received)
        self.assertEqual(saved['timestamp'], measured)
        self.assertEqual(saved['received_at'], received)

    def test_invalid_serial_is_rejected(self):
        for raw in (b'booting...', b'[]', b'{"soil_raw":100}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_sample(raw, '2026-11-06T05:00:00Z')

    def test_parser_runs_outside_repo_and_keeps_legacy_time_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'sample.log'
            record = fixtures.PrepareTest().record()
            del record['received_at']
            source.write_text(json.dumps(record) + '\nnoise\n' + json.dumps(record))
            output = Path(tmp) / 'clean.csv'
            result = subprocess.run([sys.executable, str(ROOT/'firmware/tool/parse_logs.py'),
                                     str(source), '--output', str(output)], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            quality = json.loads(output.with_suffix('.quality.json').read_text())
            self.assertEqual(quality['accepted'], 1)
            self.assertEqual(quality['duplicates_removed'], 1)
            self.assertEqual(quality['missing']['received_at'], 1)
