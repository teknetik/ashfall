import sys, numpy as np
sys.path.insert(0,'../../../integration'); from glbgeom import Model, Surface
m=Model(sys.argv[1]); a,b=sys.argv[2],sys.argv[3]
mm=lambda t: np.stack([t[...,0],-t[...,2],t[...,1]],-1)*1000
B=Surface(mm(m.tris(b))); V=np.unique(np.round(mm(m.verts(a)),4),axis=0)
G0=np.array([80,0,-30.]); S=np.array([-0.42038,0,0.90736]); U=np.array([-0.90736,0,-0.42038])
n=0
for v in V:
    if not (B.lo.min(0)-1 <= v).all() or not (v <= B.hi.max(0)+1).all(): continue
    d=B.closest(v)[0]
    if d<0.6 and B.inside(v):
        n+=1; print(np.round(v,2), 'depth %.3f'%d, 's %.1f u %.1f'%((v-G0)@S,(v-G0)@U))
print('inside', n)
