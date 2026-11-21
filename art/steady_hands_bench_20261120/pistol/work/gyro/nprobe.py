import sys, os, numpy as np
sys.path.insert(0, '../../../integration'); from glbgeom import Model, Surface
A='/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art'; S=0.136736
def mm_hand(t): return np.stack([t[...,0],-t[...,2],t[...,1]],-1)*S*1000
def mm_m(t): return np.stack([t[...,0],-t[...,2],t[...,1]],-1)*1000
old=Model(A+'/OuterBerms/ScrapPistol.glb'); OS=Surface(mm_hand(np.concatenate([old.tris(n) for n in old.mesh_nodes()])))
new=Model(sys.argv[1]); parts={n:Surface(mm_m(new.tris(n))) for n in new.mesh_nodes() if n.startswith('pistol_') and 'card' not in n}
def first(o,d):
    best=None
    for k,s in parts.items():
        t=s.ray(o,d)
        if t is not None and (best is None or t<best[0]): best=(t,k)
    return best
mode=sys.argv[2]
if mode=='side':
    for x in (52,54,56,58,60,62,64,66,68):
        row=[]
        for z in (20,21.5,23,24.5,26,27.5,29):
            ts=OS.ray((x,-40,z),(0,1,0)); b=first((x,-40,z),(0,1,0))
            row.append('%5.1f|%s %s'%(z, '%.2f'%(-40+ts) if ts else ' none', ('%.2f %s'%(-40+b[0],b[1][7:12])) if b else 'none'))
        print(x,' ; '.join(row))
else:
    for z in (-26,-28,-29,-30,-32,-36,-40,-44,-48,-52,-54,-56,-58,-60,-62,-64,-66,-68,-70):
        row=[]
        for y in (-6,0,6):
            ts=OS.ray((160,y,z),(-1,0,0)); b=first((160,y,z),(-1,0,0))
            row.append('y%3d skin %s new %s'%(y,'%.2f'%(160-ts) if ts else 'none',('%.2f %s'%(160-b[0],b[1][7:14])) if b else 'none'))
        print(z,' ; '.join(row))
