import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pm_common as C
C.reset()
p = C.import_pistol()
bm = bmesh.new(); bm.from_mesh(p.data); bm.transform(p.matrix_world)
pb = BVHTree.FromBMesh(bm)
# inside test by ray parity along +x and -y
def inside(pt):
    votes=0
    for d in ((0.013,1,0.021),(0.017,-0.011,1),(1,0.02,0.013)):
        d=Vector(d).normalized(); q=Vector(pt); hits=0
        for _ in range(40):
            h=pb.ray_cast(q,d,1.0)
            if h[0] is None: break
            hits+=1; q=h[0]+d*1e-5
        votes+=hits%2
    return votes>=2
xs=[float(a) for a in sys.argv[sys.argv.index('--')+1:]]
for x in xs:
    print('--- x=%.3f rows z 0.09..0.0, cols y -0.03..0.03 (1mm)'%x)
    for z in np.arange(0.09,-0.001,-0.001):
        row=''
        for y in np.arange(-0.03,0.0301,0.001):
            d=pb.find_nearest(Vector((x,y,z)),0.01)
            near=d[0] is not None and d[3]<0.0006
            row+= '#' if near else ('o' if inside((x,y,z)) else '.')
        print('%.3f %s'%(z,row))
