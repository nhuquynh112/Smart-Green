"""Validate the prepared patch; apply only after collection has ended."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

folder=Path(__file__).resolve().parent
root=folder.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply',action='store_true')
parser.add_argument('--collection-ended',action='store_true')
args=parser.parse_args()
manifest=json.loads((folder/'source-manifest.json').read_text())
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
if digest(folder/'changes.patch')!=manifest['patch_sha256']:
    raise SystemExit('Patch checksum mismatch; stop for review.')
for name,entry in manifest['files'].items():
    if digest(root/name)!=entry['before']:
        raise SystemExit(f'{name} has changed since preparation; do not overwrite. Reconcile first.')
patch=str(folder/'changes.patch')
subprocess.run(['git','apply','--check',patch],cwd=root,check=True)
if not args.apply:
    print('PASS: source unchanged and patch applies. No files modified. W06 deployment remains deferred.')
elif not args.collection_ended:
    raise SystemExit('Collection must end first. Use --collection-ended only after confirming this.')
else:
    subprocess.run(['git','apply',patch],cwd=root,check=True)
    for name,entry in manifest['files'].items():
        if digest(root/name)!=entry['after']:
            raise SystemExit(f'Applied hash mismatch: {name}; inspect before deployment.')
    print('Source patch applied. No service restarted, firmware uploaded, or database modified.')
