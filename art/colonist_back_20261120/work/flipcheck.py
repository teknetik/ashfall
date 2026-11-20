import json,struct,sys,numpy as np
def load(p):
    b=open(p,'rb').read(); jl=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+jl]); return b,j,28+jl
def acc(b,j,b0,i):
    a=j['accessors'][i]; v=j['bufferViews'][a['bufferView']]; n={'SCALAR':1,'VEC3':3}[a['type']]
    dt={5126:np.float32,5125:np.uint32,5123:np.uint16}[a['componentType']]; off=b0+v.get('byteOffset',0)+a.get('byteOffset',0)
    return np.frombuffer(b[off:off+np.dtype(dt).itemsize*n*a['count']],dt).reshape(a['count'],n)
def tris(p):
    b,j,b0=load(p); mi=[m['name'] for m in j['materials']].index('PlayerJumpsuit')
    pr=next(x for x in j['meshes'][0]['primitives'] if x['material']==mi)
    P=acc(b,j,b0,pr['attributes']['POSITION']).astype(float); I=acc(b,j,b0,pr['indices']).reshape(-1,3).astype(int)
    return P,I
P0,I=tris(sys.argv[1])
n0=np.cross(P0[I[:,1]]-P0[I[:,0]],P0[I[:,2]]-P0[I[:,0]]); c=P0[I].mean(1)
neck=np.array([0,1.5467,0.0136]); sel=(np.linalg.norm(c-neck,axis=1)<0.2)
for p in sys.argv[2:]:
    P,_=tris(p); n=np.cross(P[I[:,1]]-P[I[:,0]],P[I[:,2]]-P[I[:,0]])
    a0=np.linalg.norm(n0,axis=1); a=np.linalg.norm(n,axis=1)
    flip=(np.sum(n*n0,1)<0)&(a0>1e-10); squash=(a<0.2*a0)&(a0>1e-10)
    print(p.split('/')[-1],'collar region flipped',int((flip&sel).sum()),'squashed',int((squash&sel).sum()),'of',int(sel.sum()))
