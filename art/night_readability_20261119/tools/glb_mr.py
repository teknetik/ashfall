"""Read-only: metallic (B) and roughness (G) statistics of each glTF material's metallicRoughness texture in .glb files."""
import json,struct,sys,io
from PIL import Image
import numpy as np
for path in sys.argv[1:]:
    b=open(path,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n]); bin_=b[20+n+8:]
    def img(i):
        im=j['images'][j['textures'][i]['source']]; v=j['bufferViews'][im['bufferView']]; o=v.get('byteOffset',0)
        return Image.open(io.BytesIO(bin_[o:o+v['byteLength']]))
    for m in j.get('materials',[]):
        pbr=m.get('pbrMetallicRoughness',{}); t=pbr.get('metallicRoughnessTexture')
        s=''
        if t:
            a=np.asarray(img(t['index']).convert('RGB'),dtype=float)/255; met=a[...,2]; rou=a[...,1]
            s='metal mean %.2f p50 %.2f p90 %.2f >0.5 %.0f%% | rough mean %.2f p10 %.2f'%(met.mean(),np.median(met),np.percentile(met,90),100*(met>.5).mean(),rou.mean(),np.percentile(rou,10))
        print('%-50s %-20s mF=%s rF=%s %s'%(path[-50:],m.get('name','')[:20],pbr.get('metallicFactor',1),pbr.get('roughnessFactor',1),s))
