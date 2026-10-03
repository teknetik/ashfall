import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from mpfblib import *
bm = new_human(); rig = add_rig(bm)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print('MESHES', [(o.name, len(o.data.vertices), [m.type for m in o.modifiers]) for o in meshes])
for o in meshes: bake_mesh(o)
strip_helpers(bm)
lo, hi = eval_bounds(bm); print('RAWH %.3f verts %d' % ((hi - lo).z, len(bm.data.vertices)))
print('SCALE', scale_to(rig, meshes, 1.80))
rename_rig(rig, meshes)
lo, hi = eval_bounds(bm); print('HEIGHT %.3f' % (hi - lo).z)
print('BONES', [(b.name, b.parent.name if b.parent else None) for b in rig.data.bones][:60])
print('GROUPS', [g.name for g in bm.vertex_groups][:80])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'mpfb' / 'rigtest.blend'))
