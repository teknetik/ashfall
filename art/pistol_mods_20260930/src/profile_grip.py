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
def hit(o, d):
    r = pb.ray_cast(Vector(o), Vector(d), 1.0); return r[0], r[1]
print('--- backstrap (ray from +x) and frontstrap (ray from -x toward +x, starting at x=0.03) per z, y in (-0.012,-0.006,0,0.006,0.012)')
for z in np.arange(0.03, -0.09, -0.005):
    row=[]
    for y in (-0.012,-0.006,0,0.006,0.012):
        b,n = hit((0.3,y,z),(-1,0,0))
        row.append('%.4f(%+.2f,%+.2f)'%(b.x,n.x,n.z) if b else '   -   ')
    f,_=hit((0.03,0,z),(1,0,0))
    print('z %.3f back '%z+' '.join(row)+'  front %.4f'%(f.x if f else 0))
print('--- base (ray from -z) per x, y')
for x in np.arange(0.06,0.135,0.005):
    row=[]
    for y in (-0.02,-0.015,-0.01,-0.005,0,0.005,0.01,0.015,0.02):
        b,n=hit((x,y,-0.3),(0,0,1))
        row.append('%.4f'%b.z if b else '  -   ')
    print('x %.3f '%x+' '.join(row))
print('--- grip side y+ / y- at z,x')
for z in (-0.01,-0.03,-0.05,-0.07,-0.08):
    for x in np.arange(0.06,0.135,0.01):
        r,_=hit((x,0.3,z),(0,-1,0)); l,_=hit((x,-0.3,z),(0,1,0))
        print('z %.3f x %.3f  y+ %s y- %s'%(z,x,'%.4f'%r.y if r else '-','%.4f'%l.y if l else '-'))
