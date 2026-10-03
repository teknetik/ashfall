"""Tutorial set: limb pieces (bracers, knee+shin plates, boot plates) fitted to the MPFB player and exported skinned.
Each piece is aligned to its bone segment, sized from the limb's measured cross-section (uniform scale), pushed clear
of the body, rigid-skinned per loose part (metal does not bend) and mirrored to the left side.
Usage: blender_mpfb.sh fit_limbs.py -- PIECE [scale_mult] [along_frac] [margin]   PIECE in bracer|kneeshin|bootplates"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import math
from mathutils import Vector, Matrix
from fitlib import *

args = sys.argv[sys.argv.index('--') + 1:]
PIECE = args[0]; MULT = float(args[1]) if len(args) > 1 else 1.0
# piece: local long axis (raw import frame), segment bones, where the piece centre sits along the segment, margin,
# which end of the long axis points to the segment end, output file, bones it may skin to
CFG = {
    'bracer': dict(axis=Vector((1, 0, 0)), seg=('RightForeArm', 'RightHand'), frac=0.58, margin=0.008, out='TS_ArmGuards.glb',
                   bones=['RightForeArm'], front=Vector((0, -1, 0))),
    'kneeshin': dict(axis=Vector((0, 0, -1)), seg=('RightLeg', 'RightFoot'), frac=0.40, margin=0.010, out='TS_LegArmour.glb',
                     bones=['RightLeg'], front=Vector((0, -1, 0))),
    'bootplates': dict(axis=Vector((-1, 0, 0)), seg=('RightFoot', 'RightToeBase'), frac=0.0, margin=0.006, out='TS_Boots.glb',
                       bones=['RightFoot', 'RightToeBase'], front=Vector((0, 0, 1))),
}[PIECE]
FRAC = float(args[2]) if len(args) > 2 else CFG['frac']
MARGIN = float(args[3]) if len(args) > 3 else CFG['margin']

arm, body = load_final()
a = bone_head(arm, CFG['seg'][0]); b = bone_head(arm, CFG['seg'][1])
seg = b - a; segn = seg.normalized()
p = import_piece(MESHY / PIECE / 'model.glb', 'TS_' + PIECE)

def radial(points, origin, axis):
    return [((q - origin) - axis * (q - origin).dot(axis)).length for q in points]

# ---- orientation: piece long axis -> segment direction; piece 'front' -> the body's front, made perpendicular
ax = CFG['axis'].normalized()
fr = CFG['front'] - ax * CFG['front'].dot(ax); fr.normalize()
body_front = Vector((0, -1, 0)) if PIECE != 'bootplates' else Vector((0, 0, 1))
tfr = body_front - segn * body_front.dot(segn); tfr.normalize()
src = Matrix((ax, fr, ax.cross(fr))).transposed()       # columns: axis, front, side
dst = Matrix((segn, tfr, segn.cross(tfr))).transposed()
R = dst @ src.inverted()
p.data.transform(R.to_4x4()); p.data.update()

# ---- scale: inner radius of the piece (median of the smaller half of radial distances near its middle) vs limb radius
ws = world_verts(p)
lo, hi = bounds(p); c = (lo + hi) / 2
mid = [w for w in ws if abs((w - c).dot(segn)) < 0.15 * (hi - lo).length]
rs = sorted(radial(mid or ws, c, segn)); inner = rs[len(rs) // 5]
bw = world_verts(body)
centre_pt = a + seg * max(FRAC, 0.0) if PIECE != 'bootplates' else a
near = [w for w in bw if abs((w - centre_pt).dot(segn)) < 0.03 and ((w - centre_pt) - segn * (w - centre_pt).dot(segn)).length < 0.16]
limb = sorted(radial(near, centre_pt, segn))
limb_r = limb[int(len(limb) * 0.9)] if limb else 0.05
s = (limb_r + MARGIN) / max(inner, 1e-4) * MULT
ext = (hi - lo).dot(segn) if False else max(abs((w - c).dot(segn)) for w in ws) * 2
if PIECE == 'kneeshin':
    s = 0.78 * seg.length / ext * MULT
elif PIECE == 'bootplates':
    foot = [w for w in bw if w.z < 0.16 and w.x < -0.04]     # right boot (his right is -X)
    flo = Vector([min(q[i] for q in foot) for i in range(3)]); fhi = Vector([max(q[i] for q in foot) for i in range(3)])
    s = 1.04 * (fhi.y - flo.y) / ext * MULT
    BOOT = ((flo + fhi) / 2, flo, fhi)
p.data.transform(Matrix.Scale(s, 4)); p.data.update()
lo, hi = bounds(p); c = (lo + hi) / 2
if PIECE == 'bootplates':
    # centred on the boot in plan, its lowest point just above the sole
    bc, flo, fhi = BOOT
    p.data.transform(Matrix.Translation(Vector((bc.x - c.x, bc.y - c.y, flo.z + 0.012 - lo.z))))
else:
    p.data.transform(Matrix.Translation(centre_pt - c))
p.data.update()
lo, hi = bounds(p)
print('FIT', PIECE, 'scale %.4f inner %.4f limb_r %.4f size %s' % (s, inner, limb_r, [round(v, 3) for v in hi - lo]))
print('STRIP', strip_inner(p, body, near=0.02))
n0 = penetration(p, body); mv = push_out_smooth(p, body, offset=0.004, radius=0.04, iters=10); n1 = penetration(p, body)
print('PEN', n0, 'moved', mv, 'after', n1)

# ---- skin: nearest-body weights restricted to the piece's bones, then one bone per loose part
clear_groups(p); skin_transfer(p, body, bones=CFG['bones']); print('ISLANDS', rigidify_islands(p)); print('UNWEIGHTED', ensure_weighted(p, CFG['bones'][0]))
bind(p, arm)
left = mirror_x(p, 'TS_' + PIECE + '_L')
for g in left.vertex_groups:
    g.name = g.name.replace('Right', 'Left')
bind(left, arm) if not any(m.type == 'ARMATURE' for m in left.modifiers) else None
# join both sides into one skinned object
bpy.ops.object.select_all(action='DESELECT'); p.select_set(True); left.select_set(True); bpy.context.view_layer.objects.active = p
bpy.ops.object.join(); p = bpy.context.view_layer.objects.active
export_skinned([p], arm, OUT / 'out' / CFG['out'])
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'fit' / f'{PIECE}.blend'))
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name not in (p.name, body.name): o.hide_render = True
m = a + seg * 0.5
render_views(str(OUT / 'fit' / PIECE), (m.x * 0 , m.y, m.z), 0.75 if PIECE != 'bracer' else 0.9, views=('front', 'side', 'back', 'quarter'), res=(500, 500))
