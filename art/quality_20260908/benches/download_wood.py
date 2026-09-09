"""Download retained original CC0 timber PBR maps from the official Poly Haven API."""
import json,urllib.request,hashlib
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2');OUT=ROOT/'refs/quality_20260908/benches/rough_wood'
OUT.mkdir(parents=True,exist_ok=True)
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'WardAssetAudit/1.0 (local 3D asset production)'})
 with urllib.request.urlopen(req,timeout=90)as r:return r.read()
meta=json.loads(get('https://api.polyhaven.com/info/rough_wood'));files=json.loads(get('https://api.polyhaven.com/files/rough_wood'))
(OUT/'info.json').write_text(json.dumps(meta,indent=2));(OUT/'files.json').write_text(json.dumps(files,indent=2))
manifest=[]
for mapname in ['Diffuse','nor_gl','Rough','Displacement']:
 row=files[mapname]['4k']['png'];url=row['url'];assert url.startswith('https://dl.polyhaven.org/')
 p=OUT/url.split('/')[-1]
 if not p.exists():p.write_bytes(get(url))
 blob=p.read_bytes();assert hashlib.md5(blob).hexdigest()==row['md5']
 manifest.append(dict(map=mapname,url=url,file=p.name,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),sourceMd5=row['md5']))
(OUT/'download-manifest.json').write_text(json.dumps(dict(asset='rough_wood',source='https://polyhaven.com/a/rough_wood',license='CC0',authors=meta.get('authors'),maps=manifest),indent=2))
print(json.dumps(manifest,indent=2))
