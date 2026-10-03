"""First-person rifle arms (3 Oct 2026): the player's own arms and hands (upper arm to fingertips, suit sleeves and skin)
cut from char1 as a separate skinned mesh on the same armature. Shown only in first person with the rifle drawn, posed by
the same rifle hold as the body, so the hands sit on the held rifle. Export: out/TS_FPArms.glb.
Usage: blender_mpfb.sh fp_arms.py"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import bmesh
from fitlib import *

arm, body = load_final()
ARM = {f'{s}{b}' for s in ('Left', 'Right') for b in ('Arm', 'ForeArm', 'Hand')} | \
      {f'{d}_{j}_{s}' for d in ('index', 'middle', 'ring', 'pinky', 'thumb') for j in ('01', '02', '03') for s in 'lr'}
gname = {g.index: g.name for g in body.vertex_groups}
def dom(v):
    if not v.groups: return None
    g = max(v.groups, key=lambda g: g.weight); return gname[g.group]
keep = {v.index for v in body.data.vertices if dom(v) in ARM}
fa = body.copy(); fa.data = body.data.copy(); fa.name = 'TS_FPArms'; fa.data.name = 'TS_FPArms'
bpy.context.collection.objects.link(fa)
bm = bmesh.new(); bm.from_mesh(fa.data); bm.faces.ensure_lookup_table()
kill = [f for f in bm.faces if not all(v.index in keep for v in f.verts)]
bmesh.ops.delete(bm, geom=kill, context='FACES'); bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bm.to_mesh(fa.data); bm.free(); fa.data.update()
# drop material slots the arms no longer use (beard, hair, eyes ...)
used = {p.material_index for p in fa.data.polygons}
for i in sorted(range(len(fa.data.materials)), reverse=True):
    if i not in used:
        fa.active_material_index = i; bpy.context.view_layer.objects.active = fa
        bpy.ops.object.material_slot_remove()
print('FPARMS verts', len(fa.data.vertices), 'tris', sum(len(p.vertices) - 2 for p in fa.data.polygons), 'materials', [m.name for m in fa.data.materials])
export_skinned([fa], arm, OUT / 'out' / 'TS_FPArms.glb', ratio=1.0)
for o in bpy.data.objects:
    if o.type == 'MESH' and o != fa: o.hide_render = True
render_views(str(OUT / 'fit' / 'fparms'), (0, 0, 1.2), 1.3, views=('front', 'top'), res=(500, 500))
