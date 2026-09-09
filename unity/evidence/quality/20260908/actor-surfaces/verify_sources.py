#!/usr/bin/env python3
"""Recheck immutable source evidence without changing assets or frozen report."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
records=json.loads((HERE/'source-map-checks.json').read_text())
checks=[]
for row in records:
    if 'file' not in row:continue
    a=ROOT/row['file'];b=ROOT/row['source']
    ha=hashlib.sha256(a.read_bytes()).hexdigest();hb=hashlib.sha256(b.read_bytes()).hexdigest()
    checks.append(dict(file=row['file'],source=row['source'],sameAsFrozenSource=ha==row['sha256'] and hb==row['sourceSha256'],byteExact=ha==hb))
assert all(r['sameAsFrozenSource'] and r['byteExact'] for r in checks),checks
print(json.dumps(dict(checked=len(checks),allSourcePixelsUnchanged=True,checks=checks),indent=2))
