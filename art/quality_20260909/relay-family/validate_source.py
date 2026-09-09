import json,math,hashlib
from pathlib import Path
import numpy as np
root=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family/revision-01')
path=root/'relay-meshes.json';rows=json.loads(path.read_text());checks=[]
assert len({r['name']for r in rows})==len(rows)
for r in rows:
 v=np.asarray(r['positions'],dtype=np.float64);n=np.asarray(r['normals'],dtype=np.float64);uv=np.asarray(r['uv']);tri=np.asarray(r['indices'],dtype=np.int64).reshape(-1,3)
 assert len(v)==len(n)==len(uv) and np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all(),r['name']
 assert tri.min()>=0 and tri.max()<len(v),r['name']
 length=np.linalg.norm(n,axis=1);assert np.max(np.abs(length-1))<.00001,(r['name'],length.min(),length.max())
 e1=v[tri[:,1]]-v[tri[:,0]];e2=v[tri[:,2]]-v[tri[:,0]];cross=np.cross(e1,e2);area=np.linalg.norm(cross,axis=1)*.5;dots=np.einsum('ij,ij->i',cross,n[tri].mean(axis=1));normdot=np.einsum('ij,ij->i',cross/np.maximum(1e-20,2*area)[:,None],n[tri[:,0]])
 checks.append(dict(name=r['name'],triangles=len(tri),vertices=len(v),nondegenerateTriangles=int((area>1e-12).sum()),degenerateTriangles=int((area<=1e-12).sum()),triangleCrossNormalDotRange=[float(normdot[area>1e-12].min()),float(normdot[area>1e-12].max())],triangleCrossNormalPositive=int((dots>1e-12).sum()),triangleCrossNormalNegative=int((dots< -1e-12).sum()),uvPhysicalRange=[uv.min(axis=0).tolist(),uv.max(axis=0).tolist()],finite=True,normalsUnit=True))
record=dict(sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),parts=len(rows),triangles=sum(c['triangles']for c in checks),vertices=sum(c['vertices']for c in checks),checks=checks,qualification='Source-buffer validation only. Requires Unity import/renderer winding check, source and native visual review, temporal and frame-time measurement.')
(root/'buffer-validation.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items()if k!='checks'}))
