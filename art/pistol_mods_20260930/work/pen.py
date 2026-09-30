import bpy, bmesh
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath='/home/teknetik/code/ao2/art/pistol_mods_20260930/source/pistol_mods_v1.blend')
hs=[o for o in bpy.data.objects if o.name.startswith('PlayerFPHands')]
bm=bmesh.new()
for h in hs:
    t=bmesh.new(); t.from_mesh(h.data); t.transform(h.matrix_world); me=bpy.data.meshes.new('t'); t.to_mesh(me); bm.from_mesh(me)
tr=BVHTree.FromBMesh(bm)
o=bpy.data.objects['grip_stabilised_pistol']
for v in o.data.vertices:
    p=o.matrix_world@v.co; n=tr.find_nearest(p,0.02)
    if n[0] is not None and (p-n[0]).dot(n[1])<0:
        print('PEN depth_mm %.3f at %s'%(n[3]*1000, tuple(round(x,4) for x in p)))
