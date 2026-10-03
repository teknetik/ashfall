#!/usr/bin/env python3
"""Inspect a glb mesh: bounding box, longest axis, and vertex/triangle density along that axis in 10 % bins, plus the
cross-section extent per bin. Used to determine the muzzle end of the Meshy field rifle (the thin, sparse end)."""
import json,struct,sys
import numpy as np
path=sys.argv[1]
b=open(path,'rb').read()
assert b[:4]==b'glTF'
length=struct.unpack('<I',b[8:12])[0];off=12;chunks=[]
while off<length:
    clen,ctype=struct.unpack('<II',b[off:off+8]);chunks.append((ctype,b[off+8:off+8+clen]));off+=8+clen
gltf=json.loads(chunks[0][1]);bin_=chunks[1][1]
def accessor(i):
    a=gltf['accessors'][i];bv=gltf['bufferViews'][a['bufferView']]
    ctype={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}[a['componentType']]
    n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    start=bv.get('byteOffset',0)+a.get('byteOffset',0)
    stride=bv.get('byteStride',0)
    if stride and stride!=n*np.dtype(ctype).itemsize:
        raw=np.frombuffer(bin_,dtype=np.uint8,count=stride*a['count'],offset=start)
        return np.lib.stride_tricks.as_strided(raw.view(ctype),shape=(a['count'],n),strides=(stride,np.dtype(ctype).itemsize)).copy()
    return np.frombuffer(bin_,dtype=ctype,count=a['count']*n,offset=start).reshape(a['count'],n)
verts=[];tris=[]
# node transforms (meshes may be under scaled/rotated nodes)
def node_matrix(nd):
    if 'matrix' in nd:return np.array(nd['matrix'],dtype=np.float64).reshape(4,4).T
    T=np.eye(4);R=np.eye(4);S=np.eye(4)
    if 'translation' in nd:T[:3,3]=nd['translation']
    if 'rotation' in nd:
        x,y,z,w=nd['rotation'];R[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    if 'scale' in nd:S[:3,:3]=np.diag(nd['scale'])
    return T@R@S
def walk(ni,parent):
    nd=gltf['nodes'][ni];m=parent@node_matrix(nd)
    if 'mesh' in nd:
        for prim in gltf['meshes'][nd['mesh']]['primitives']:
            p=accessor(prim['attributes']['POSITION']).astype(np.float64)
            p=(m[:3,:3]@p.T).T+m[:3,3]
            base=sum(len(v) for v in verts)
            verts.append(p)
            if 'indices' in prim:tris.append(accessor(prim['indices']).reshape(-1,3).astype(np.int64)+base)
    for c in nd.get('children',[]):walk(c,m)
for s in gltf['scenes'][gltf.get('scene',0)]['nodes']:walk(s,np.eye(4))
V=np.vstack(verts);T=np.vstack(tris) if tris else None
mn=V.min(0);mx=V.max(0);size=mx-mn;axis=int(np.argmax(size))
print('nodes',len(gltf['nodes']),'meshes',[ (m.get('name'),len(m['primitives'])) for m in gltf['meshes']])
print('verts',len(V),'tris',0 if T is None else len(T),'min',mn.round(4),'max',mx.round(4),'size',size.round(4),'longest axis',axis,'XYZ'[axis])
cent=V[T].mean(1) if T is not None else V
bins=np.linspace(mn[axis],mx[axis],11)
print('bin  range            verts   tris   cross-section (other two axes extents)')
for i in range(10):
    lo,hi=bins[i],bins[i+1]
    sel=V[(V[:,axis]>=lo)&(V[:,axis]<=hi)]
    tsel=((cent[:,axis]>=lo)&(cent[:,axis]<=hi)).sum() if T is not None else 0
    others=[j for j in range(3) if j!=axis]
    cs=(sel[:,others].max(0)-sel[:,others].min(0)) if len(sel) else np.zeros(2)
    print(f'{i:2d} [{lo:+.3f},{hi:+.3f}] {len(sel):6d} {tsel:6d}   {cs.round(3)}')
# original installer heuristic: 12 % end sections
L=size[axis]
for high in (False,True):
    sel=V[V[:,axis]>mx[axis]-L*.12] if high else V[V[:,axis]<mn[axis]+L*.12]
    others=[j for j in range(3) if j!=axis];s=sel[:,others].max(0)-sel[:,others].min(0)
    print('end',('+' if high else '-'),'12% section extents',s.round(3),'magnitude',round(float(np.linalg.norm(s)),4),'verts',len(sel))
