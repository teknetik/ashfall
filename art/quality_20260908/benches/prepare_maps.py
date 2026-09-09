"""Technical map packing and original end-grain synthesis for the authored bench."""
import json,hashlib,shutil
from pathlib import Path
import numpy as np
from PIL import Image
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/benches/textures';O.mkdir(parents=True,exist_ok=True)
wood=R/'refs/quality_20260908/benches/wooden_planks'
for a,b in [('wooden_planks_diff_4k.png','Wood_BaseColor.png'),('wooden_planks_nor_gl_4k.png','Wood_Normal.png')]:shutil.copy2(wood/a,O/b)
rough=np.asarray(Image.open(wood/'wooden_planks_rough_4k.png').convert('L'));packed=np.zeros((*rough.shape,4),dtype=np.uint8);packed[...,3]=255-rough
Image.fromarray(packed).save(O/'Wood_MetalSmooth.png')
for region in ['Paint','Steel','Bronze','Rubber','Dust']:
 for suffix in ['BaseColor','Normal','MetalSmooth']:shutil.copy2(R/'art/quality_20260908/lamps/textures'/(region+'_'+suffix+'.png'),O/(region+'_'+suffix+'.png'))
# Cut end grain is original procedural material, not a repeated photograph of a board's long face.
N=1024;rng=np.random.default_rng(908265);y,x=np.mgrid[0:N,0:N].astype(float)/N
radius=np.sqrt(((x-.42)*1.04)**2+((y-.56)*.8)**2)
ring=np.sin(radius*180+2*np.sin(x*19)*np.sin(y*12))
variation=rng.normal(0,.006,(N,N));shade=.018*ring+variation
base=np.array((.42,.39,.33))[None,None,:]+shade[...,None]
Image.fromarray((np.clip(base,0,1)*255).astype('uint8')).save(O/'EndGrain_BaseColor.png')
normal=np.zeros((N,N,3),dtype=np.uint8);normal[...,:2]=128;normal[...,2]=255;Image.fromarray(normal).save(O/'EndGrain_Normal.png')
packed=np.zeros((N,N,4),dtype=np.uint8);packed[...,3]=60;Image.fromarray(packed).save(O/'EndGrain_MetalSmooth.png')
rows=[]
for p in sorted(O.glob('*.png')):
 with Image.open(p)as im:size=im.size
 rows.append(dict(file=p.name,size=size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(O/'manifest.json').write_text(json.dumps(dict(wood=dict(asset='Poly Haven Wooden Planks',authors='Charlotte Baglioni (photography), Dario Barresi (processing)',license='CC0',url='https://polyhaven.com/a/wooden_planks',sourceMetres=2,processing='Albedo and GL normal copied unchanged; metallic=0 and smoothness=1-source roughness'),otherMaterials='Original Ward procedural metal/rubber and end-grain maps',maps=rows),indent=2))
print('Bench maps prepared with source dimensions retained.')
