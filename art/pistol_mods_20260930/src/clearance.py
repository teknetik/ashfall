# Hand clearance map on the pistol: colour each pistol vertex by the distance to the FP hands (metric frame).
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pm_common as C

OUT = C.ART + 'work/inspect/'
C.reset()
p = C.import_pistol()
hands = C.import_hands()
bm = bmesh.new()
for h in hands:
    tmp = bmesh.new(); tmp.from_mesh(h.data); tmp.transform(h.matrix_world)
    me = bpy.data.meshes.new('t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me)
hb = BVHTree.FromBMesh(bm)
M = p.matrix_world
V = np.array([M @ v.co for v in p.data.vertices])
d = np.array([hb.find_nearest(Vector(v))[3] for v in V])
np.save(C.ART + 'work/pistol_hand_dist.npy', d)
# hand vertex extents (metric)
H = np.array([v.co for v in bm.verts])
near = H[(H[:, 0] > -0.14) & (H[:, 0] < 0.14) & (H[:, 2] > -0.11)]
print('HAND verts near pistol', len(near), 'z min', near[:, 2].min())
for z0 in np.arange(-0.11, 0.07, 0.01):
    sl = near[(near[:, 2] >= z0) & (near[:, 2] < z0 + 0.01)]
    ps = V[(V[:, 2] >= z0) & (V[:, 2] < z0 + 0.01)]
    if len(sl) and len(ps):
        print('z %.2f hand x[%.3f %.3f] y[%.3f %.3f] | pistol x[%.3f %.3f] y[%.3f %.3f]' % (z0, sl[:, 0].min(), sl[:, 0].max(), sl[:, 1].min(), sl[:, 1].max(), ps[:, 0].min(), ps[:, 0].max(), ps[:, 1].min(), ps[:, 1].max()))
    elif len(ps):
        print('z %.2f no hand | pistol x[%.3f %.3f]' % (z0, ps[:, 0].min(), ps[:, 0].max()))
# vertex colours: red <2mm, orange <6mm, yellow <12mm, green beyond
col = p.data.color_attributes.new('clr', 'FLOAT_COLOR', 'POINT')
for i, dd in enumerate(d):
    c = (1, 0, 0, 1) if dd < .002 else (1, .45, 0, 1) if dd < .006 else (1, 1, 0, 1) if dd < .012 else (0, .7, .2, 1)
    col.data[i].color = c
m = bpy.data.materials.new('clr'); m.use_nodes = True
nt = m.node_tree; a = nt.nodes.new('ShaderNodeVertexColor'); a.layer_name = 'clr'
nt.links.new(a.outputs[0], nt.nodes['Principled BSDF'].inputs['Base Color'])
p.data.materials.clear(); p.data.materials.append(m)
for h in hands: h.hide_render = True
C.setup_render(res=(1000, 700), samples=16)
C.world_sky(strength=0.8)
C.sun_lamp(elev=50, azim=150, energy=2.5)
views = {
    'right': ((0, 0.6, 0), (0, -1, 0), (0, 0, 1)),
    'left': ((0, -0.6, 0), (0, 1, 0), (0, 0, 1)),
    'back': ((0.6, 0, 0), (-1, 0, 0), (0, 0, 1)),
    'bottom': ((0, 0, -0.6), (0, 0, 1), (-1, 0, 0)),
    'front': ((-0.6, 0, 0), (1, 0, 0), (0, 0, 1)),
}
for n, (loc, dd, u) in views.items():
    C.render(OUT + 'clear_%s.png' % n, C.camera('c' + n, loc, dd, u, ortho=0.3))
