# integration's rule (hand_check.py) on a pistol.glb in P metres: per gyro mount point, new signed distance minus old,
# signs by ray parity. Usage: moved.py PISTOL_GLB
import sys, numpy as np, json
sys.path.insert(0,'../../../integration'); from glbgeom import Model, Surface
A='/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art'; S=0.136736
hm=lambda t: np.stack([t[...,0],-t[...,2],t[...,1]],-1)*S*1000
mm=lambda t: np.stack([t[...,0],-t[...,2],t[...,1]],-1)*1000
old=Model(A+'/OuterBerms/ScrapPistol.glb'); OS=Surface(hm(np.concatenate([old.tris(n) for n in old.mesh_nodes()])))
mods=Model(A+'/Weapons/PistolMods/PistolMods.glb')
new=Model(sys.argv[1]); NS=Surface(mm(np.concatenate([new.tris(n) for n in new.mesh_nodes() if n.startswith('pistol_') and 'card' not in n])))
for mod in [n for n in mods.mesh_nodes()]:
    v=np.unique(np.round(hm(mods.tris(mod).reshape(-1,3)),4),axis=0)
    mp=[p for p in v if OS.closest(p)[0]<=0.5]
    if not mp: continue
    out=[]
    for p in mp:
        so=-OS.closest(p)[0] if OS.inside(p) else OS.closest(p)[0]
        dn=NS.closest(p)[0]; sn=-dn if NS.inside(p) else dn
        out.append((sn-so, p))
    d=np.array([o[0] for o in out])
    print(mod, len(mp), 'max |moved| %.2f'%np.abs(d).max(), 'over 1:', int((np.abs(d)>1).sum()), [ (round(o[0],2), np.round(o[1],1).tolist()) for o in sorted(out,key=lambda o:-abs(o[0]))[:3]])
