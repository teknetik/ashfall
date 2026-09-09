"""Original, deterministic small-scale PBR material maps, not image manipulation."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageFilter

ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/quality_20260908/lamps/textures'
OUT.mkdir(parents=True,exist_ok=True)
N=2048
rng=np.random.default_rng(908264)
def noise(size):
    a=(rng.random((size,size))*255).astype('uint8')
    return np.asarray(Image.fromarray(a).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255
n=0.48*noise(16)+.27*noise(79)+.17*noise(320)+.08*noise(2048)
fine=noise(1024)-.5
metal=np.clip((n-.7)*15,0,1)
recipes={
 'Paint': ((.155,.165,.155),.49,0.02,.018),
 'Base': ((.22,.195,.165),.8,.025,.07),
 'Steel': ((.32,.34,.34),.43,.93,.022),
 'Bronze': ((.37,.285,.16),.50,.88,.04),
 'Rubber': ((.047,.045,.041),.85,0,.022),
 'Enamel': ((.31,.34,.31),.39,.025,.027),
 'Dust': ((.30,.275,.235),.94,0,.035),
 'Oxide': ((.24,.145,.078),.85,0,.04),
}
manifest=[]
for key,(colour,rough,met,amplitude) in recipes.items():
    diff=np.clip(np.array(colour)[None,None,:]+(n[...,None]-.5)*amplitude*2+fine[...,None]*.014,0,1)
    # Tiny irregular corrosion freckles; the source geometry supplies structural wear.
    if key in ('Base','Bronze'):
        freckle=np.clip((noise(250)-.70)*9,0,1)[...,None]
        diff=diff*(1-freckle*.18)+np.array((.23,.15,.085))*freckle*.18
    smooth=np.clip(1-rough+(n-.5)*.16,0.03,.8)
    packed=np.zeros((N,N,4),dtype=np.uint8)
    packed[...,0]=(255*np.clip(met+(n-.5)*.035,0,1)).astype('uint8')
    packed[...,3]=(255*smooth).astype('uint8')
    # Submillimetre irregularity; tangent-space OpenGL normal, +Y.
    height=(noise(600)-.5)*.009+(noise(1800)-.5)*.002
    gy,gx=np.gradient(height)
    v=np.stack((-gx*14,-gy*14,np.ones_like(gx)),axis=-1)
    v/=np.linalg.norm(v,axis=-1,keepdims=True)
    colour=(diff*255).astype('uint8')
    if key=='Dust':
        yy,xx=np.mgrid[0:N,0:N].astype(np.float32)/N
        edge=np.clip((.48-np.sqrt((xx-.5)**2+(yy-.5)**2)+(n-.5)*.24)*6,0,1)
        grain=np.clip((noise(400)-.24)*1.5,0,1)
        alpha=(255*(edge**1.25)*.48*(.34+.66*grain)).astype('uint8')
        colour=np.dstack((colour,alpha))
    outputs={key+'_BaseColor.png':colour,key+'_MetalSmooth.png':packed,key+'_Normal.png':((v*.5+.5)*255).astype('uint8')}
    for name,arr in outputs.items():
        p=OUT/name;Image.fromarray(arr).save(p)
        manifest.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),width=N,height=N))
(OUT/'manifest.json').write_text(json.dumps(dict(author='Original deterministic Ward lamp material synthesis',licence='Project original',seed=908264,physicalTileMetres=.75,normal='OpenGL +Y tangent space',packed='R metallic; A smoothness; GB unused',maps=manifest),indent=2))
print('Authored',len(manifest),'original 2048px PBR maps')
