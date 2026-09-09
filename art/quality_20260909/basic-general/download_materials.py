from pathlib import Path
import json,urllib.request,hashlib,concurrent.futures
O=Path('/home/teknetik/code/ao2/art/quality_20260909/basic-general');R=Path('/home/teknetik/code/ao2/refs/quality_20260909/basic-general/materials');R.mkdir(parents=True,exist_ok=True)
jobs=json.loads((O/'material-downloads.json').read_text())
# The checked cotton color is not the awning design; its calibrated weave normals remain useful.
jobs=[j for j in jobs if j['asset']!='fabric_pattern_07' or j['channel']!='col_1']
def fetch(j):
 p=R/j['asset']/Path(j['url']).name;p.parent.mkdir(exist_ok=True)
 if not p.exists():
  with urllib.request.urlopen(j['url'],timeout=90) as q: p.write_bytes(q.read())
 data=p.read_bytes();assert hashlib.md5(data).hexdigest()==j['md5']
 return {**j,'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'license':'CC0','license_url':'https://polyhaven.com/license','source_url':'https://polyhaven.com/a/'+j['asset']}
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex: rows=list(ex.map(fetch,jobs))
(R/'download-manifest.json').write_text(json.dumps(rows,indent=2));print('Verified',len(rows),'original 4K texture maps')
