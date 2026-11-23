"""Verify the published dataset without rewriting measurements."""
import hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
for name,expected in json.loads((p/'manifest.json').read_text()).items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==expected,name
print('PASS: published dataset hashes')
