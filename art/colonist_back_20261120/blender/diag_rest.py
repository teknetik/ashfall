import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
from mathutils import Matrix
out = HERE + '/renders/diag/'
reset()
arm, body, P = load(('vest',), piece_paths={'vest': HERE + '/out/TS_FieldVest.glb'})
cam = setup(res=(900, 900), light='sun'); V = views(arm)
render(out + 'rest_vs_idle_idle.png', cam, *V['back15'])
ad = arm.animation_data; ad.action = None
for t in ad.nla_tracks: t.mute = True
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
render(out + 'rest_vs_idle_rest.png', cam, *V['back15'])
# which bones weight the flank verts?
o = P['vest']; names = {g.index: g.name for g in o.vertex_groups}
from collections import Counter
c = Counter()
for v in o.data.vertices:
    w = o.matrix_world @ v.co
    if abs(w.x) > 0.17 and 1.0 < w.z < 1.3:
        for g in v.groups:
            if g.weight > 0.3: c[names[g.group]] += 1
print('FLANK', c.most_common())
