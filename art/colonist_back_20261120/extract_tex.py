"""Extract embedded glTF images to inspect/<glb>/ (read-only on the source)."""
import json,struct,sys,os
out=sys.argv[1]
for p in sys.argv[2:]:
    b=open(p,'rb').read()
    l=struct.unpack('<I',b[12:16])[0]
    j=json.loads(b[20:20+l]); binstart=20+l+8
    name=os.path.basename(p)[:-4]; d=os.path.join(out,name); os.makedirs(d,exist_ok=True)
    for i,im in enumerate(j.get('images',[])):
        bv=j['bufferViews'][im['bufferView']]
        data=b[binstart+bv.get('byteOffset',0):binstart+bv.get('byteOffset',0)+bv['byteLength']]
        ext='.png' if im['mimeType']=='image/png' else '.jpg'
        open(os.path.join(d,f"{i}_{im.get('name','img')}{ext}"),'wb').write(data)
