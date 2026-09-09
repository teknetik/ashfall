"""Original deterministic canvas color variation; retains calibrated photo weave separately."""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image
O=Path('/home/teknetik/code/ao2/art/quality_20260909/basic-general/textures');O.mkdir(exist_ok=True)
r=np.random.default_rng(909402);size=2048;y,x=np.mgrid[:size,:size]/size
field=np.zeros((size,size),np.float32)
for f,a in [(1,.25),(2,.18),(4,.10),(11,.036),(33,.01)]:
 field+=a*np.sin(2*np.pi*(x*f+r.random()))*np.sin(2*np.pi*(y*(f+1)+r.random()))
field+=r.normal(0,.023,(size,size));weave=.020*np.sin(x*2*np.pi*350)*np.sin(y*2*np.pi*350)
rows=[]
for name,color in [('Canvas',[133,58,38]),('CanvasPatch',[153,128,86])]:
 rgb=np.clip(np.asarray(color)[None,None,:]*(1+field[:,:,None]*.20+weave[:,:,None]),0,255).astype(np.uint8);p=O/(name+'_BaseColor.png');Image.fromarray(rgb).save(p);rows.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'canvas-manifest.json').write_text(json.dumps({'author':'Original deterministic Ward canvas color field','seed':909402,'dimensions':[size,size],'physical_tile_metres':.4,'normal_source':'Poly Haven CC0 Fabric Pattern07 normal, unchanged','maps':rows},indent=2))
