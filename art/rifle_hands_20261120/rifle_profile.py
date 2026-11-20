"""Side profile of the field rifle mesh (glTF frame) to locate the pistol grip, magazine and handguard.
Usage: python3 rifle_profile.py path/to/FieldRifle.glb"""
import json,struct,sys
import numpy as np
p=sys.argv[1];d=open(p,'rb').read()
n=struct.unpack_from('<I',d,12)[0];g=json.loads(d[20:20+n]);binoff=20+n+8
def acc(i):
    a=g['accessors'][i];bv=g['bufferViews'][a['bufferView']]
    off=binoff+bv.get('byteOffset',0)+a.get('byteOffset',0);cnt=a['count']
    return np.frombuffer(d,dtype=np.float32,count=cnt*3,offset=off).reshape(cnt,3) if bv.get('byteStride',12)==12 else None
pts=[]
for m in g['meshes']:
    for pr in m['primitives']:pts.append(acc(pr['attributes']['POSITION']))
print('nodes',[ (nd.get('name'),nd.get('mesh'),nd.get('translation'),nd.get('rotation'),nd.get('scale')) for nd in g['nodes']])
P=np.concatenate(pts);mn=P.min(0);mx=P.max(0);print('bounds',mn,mx,'size',mx-mn)
ax=int(np.argmax(mx-mn));up=1 if ax!=1 else 2;lat=3-ax-up
L=mx[ax]-mn[ax];N=40
print('axis',ax,'up',up,'lat',lat,'(t from glTF -X end = muzzle; 0..1)')
for i in range(N):
    t0=mn[ax]+L*i/N;t1=t0+L/N;s=P[(P[:,ax]>=t0)&(P[:,ax]<t1)]
    if len(s)==0:print(i,'-');continue
    lo=s[:,up].min();hi=s[:,up].max();w=s[:,lat].max()-s[:,lat].min()
    bar='#'*int((hi-lo)/(mx[up]-mn[up])*40)
    print(f"{i/N:.3f} low {(lo-mn[up])/(mx[up]-mn[up]):.2f} high {(hi-mn[up])/(mx[up]-mn[up]):.2f} width {w:.3f} n {len(s):5d} {bar}")

# pistol grip: points in the rear lower region (from-muzzle 0.74..0.86, below 60 % height), centre per height band
print('--- grip region (fraction from muzzle along length, by height band) ---')
f=(P[:,ax]-mn[ax])/L;h=(P[:,up]-mn[up])/(mx[up]-mn[up])
for b in np.arange(0.05,0.70,0.05):
    s=P[(f>0.70)&(f<0.86)&(h>=b)&(h<b+0.05)]
    if len(s)==0:print(f"h {b:.2f} -");continue
    ff=(s[:,ax]-mn[ax])/L
    print(f"h {b:.2f}-{b+.05:.2f} n {len(s):4d} along {ff.min():.3f}..{ff.max():.3f} mid {(ff.min()+ff.max())/2:.3f} lat {s[:,lat].min():.3f}..{s[:,lat].max():.3f}")
print('--- under the barrel ahead of the magazine (handguard), from-muzzle 0.15..0.55 ---')
for a in np.arange(0.15,0.55,0.05):
    s=P[(f>=a)&(f<a+0.05)]
    if len(s):print(f"{a:.2f} low {((s[:,up].min()-mn[up])/(mx[up]-mn[up])):.2f} high {((s[:,up].max()-mn[up])/(mx[up]-mn[up])):.2f} width {s[:,lat].max()-s[:,lat].min():.3f}")
