import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import bpy, bmesh
from mathutils import Vector
import geo as G, check as CK, pgeom as PG
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, '..', 'export', 'pistol.blend'))
for o in bpy.data.objects:
    if o.type == 'MESH' and 'sh' in o:
        b, nm = G.solid_check(o)
        if b or nm: print('OPEN', o.name, 'boundary', b, 'nonmanifold', nm, flush=True)
h = bpy.data.objects['pistol_housing']; f = bpy.data.objects['pistol_frame']
gh = CK.Geo(h); gf = CK.Geo(f)
th = gh.bvh(h.matrix_world); tf = gf.bvh(f.matrix_world)
for nm, (u, s, y) in {'T-head centre s20': (-17, 20, 0), 'T-head s20 y5': (-17, 20, 5), 'channel s10': (-23, 10, 0), 'window': (-29, -3, 0), 'back wall s-20': (-29, -20, 0),
                       'flange s20 y8': (-17, 20, 8), 'ear s37 y12': (-18, 37, 12), 'web s20': (-5, 20, 0), 'pin': (-16, 37, 10), 'groove': (-23, 39, 4)}.items():
    p = PG.GP(u, s, y)
    print('%-22s housing inside %s   frame inside %s' % (nm, CK.inside(th, p), CK.inside(tf, p)), flush=True)
# what of the family is near X 88, Z 21
for o in bpy.data.objects:
    if o.type == 'MESH' and 'sh' in o:
        n = sum(1 for v in o.data.vertices if 0.082 < (o.matrix_world @ v.co).x < 0.095 and 0.0165 < (o.matrix_world @ v.co).z < 0.026)
        if n: print('NEAR', o.name, n, flush=True)
