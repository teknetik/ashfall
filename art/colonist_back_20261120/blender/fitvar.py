"""Vest fitting variants (diagnosis): which step makes the ragged borders and holes? Renders only, no export.
Variants: A = shipped recipe (strip_inner + push + Blender collapse 40 %), B = no strip, C = strip, no decimation,
D = no strip, no decimation."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
import fitlib as F
import cblib as C
import bpy, bmesh
from mathutils import Vector, Matrix
POLISH = '/home/teknetik/code/ao2/art/character_polish_20261005/player_polish.blend'
out = C.HERE + '/renders/diag/'
def load_body():
    bpy.ops.wm.open_mainfile(filepath=POLISH)
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['char1']
    if arm.animation_data:
        arm.animation_data.action = None
        for t in arm.animation_data.nla_tracks: t.mute = True
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update(); return arm, body
def fit_vest(strip, dec):
    arm, body = load_body()
    NECKZ = F.bone_head(arm, 'neck').z
    ws = F.world_verts(body)
    band = [w for w in ws if NECKZ-0.25 < w.z < NECKZ-0.17 and abs(w.x) < 0.09]
    ys = [w.y for w in band]; cd = max(ys)-min(ys); cy = (max(ys)+min(ys))/2
    c = F.import_piece(F.MESHY/'chest'/'model.glb', 'TS_FieldVest')
    lo, hi = F.bounds(c); s = (cd + 0)/((hi-lo).y*0.86)
    c.scale = (s, s, s); F.apply(c); lo, hi = F.bounds(c)
    c.location = (-(lo.x+hi.x)/2, cy-(lo.y+hi.y)/2, NECKZ-hi.z); F.apply(c)
    ns = F.strip_inner(c, body) if strip else 0
    F.push_out_smooth(c, body, offset=0.007, radius=0.07)
    if dec: F.decimate(c, 0.4)
    print('VAR strip', strip, 'dec', dec, 'stripped', ns, 'tris', sum(len(p.vertices)-2 for p in c.data.polygons))
    return arm, body, c
for tag, strip, dec in (('A', 1, 1), ('B', 0, 1), ('C', 1, 0), ('D', 0, 0)):
    arm, body, c = fit_vest(strip, dec)
    suit = next(m for m in body.data.materials if 'Jumpsuit' in m.name)
    b = suit.node_tree.nodes['Principled BSDF']
    for l in list(b.inputs['Base Color'].links): suit.node_tree.links.remove(l)
    b.inputs['Base Color'].default_value = (1, 0, 1, 1)
    for m in c.data.materials:
        vb = m.node_tree.nodes['Principled BSDF']
        for inp in ('Base Color', 'Metallic', 'Roughness'):
            for l in list(vb.inputs[inp].links): m.node_tree.links.remove(l)
        vb.inputs['Base Color'].default_value = (0.6, 0.55, 0.45, 1); vb.inputs['Metallic'].default_value = 0
    cam = C.setup(res=(900, 900), light='sun')
    h = arm.matrix_world @ arm.data.bones['Head'].head_local
    C.render(out + f'var{tag}_back.png', cam, h + Vector((0.25, 0.85, -0.2)), h + Vector((0, 0, -0.4)), 40)
    C.render(out + f'var{tag}_top.png', cam, h + Vector((-0.3, 0.55, 0.35)), h + Vector((0, 0, -0.3)), 40)
