"""Hero armour: limb pieces (bracers, knee + shin plates, boot plates) fitted to the new body and exported skinned.
Port of art/tutorial_set_20261002/blender/fit_limbs.py (right side fitted, mirrored to the left by name), with the
20 Nov quality recipe (no strip_inner, UV-seam splits merged, texture-aware decimation outside Blender).
What changed for the new body:
  * bracer: the new forearm is half as thick again as the old one but hardly longer, so the shipped rule (uniform
    scale from the limb radius) would run the bracer past the elbow. The uniform scale now comes from the forearm
    LENGTH (`cover`); the remaining difference in girth is taken up by the smooth surface-following fit (H.conform);
  * knee + shin: the new rig's ankle joint is higher (boot top), so the length rule is tied to knee-to-boot-top;
  * boot plates: the new rest pose stands flat (the old one was on tiptoe), so the plates are laid along the SOLE
    (direction of the boot in plan), not along the ankle-to-toe bone; weights Foot / ToeBase by position across the
    toe joint (cap rigid on ToeBase, collar rigid on Foot, the strap between them bends).
  * each side gets its own final fit after mirroring (the new mesh is not exactly symmetric).
Stage 'fit'  -> work/<piece>_fit.obj + work/<piece>_fit.json   (right side only)
Stage 'skin' -> work/stage/<file>.glb                          (decimated right side, mirrored, both sides joined)
Usage: blender.sh fit_limbs.py -- <bracer|kneeshin|bootplates> <fit|skin|full> [key=value ...]"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:]
PIECE, STAGE = args[0], args[1]; opt = dict(a.split('=', 1) for a in args[2:] if '=' in a)
f = lambda k, d: float(opt.get(k, d))
# axis: the piece's long axis in its raw import frame; front: the side of the piece that faces the body's front (boots: up)
CFG = {
    'bracer': dict(axis=Vector((1, 0, 0)), front=Vector((0, -1, 0)), seg=('RightForeArm', 'RightHand'), out='TS_ArmGuards.glb',
                   bones=['RightForeArm'], cover=f('cover', 0.80), frac=f('frac', 0.55), lo=f('lo', 0.006), hi=f('hi', 0.011),
                   radius=f('radius', 0.035), roll=f('roll', 0.0)),
    'kneeshin': dict(axis=Vector((0, 0, -1)), front=Vector((0, -1, 0)), seg=('RightLeg', 'RightFoot'), out='TS_LegArmour.glb',
                     bones=['RightLeg'], top=f('top', 0.035), bottom=f('bottom', 0.215), lo=f('lo', 0.007), hi=f('hi', 0.013),
                     radius=f('radius', 0.04), roll=f('roll', 0.0)),
    'bootplates': dict(axis=Vector((-1, 0, 0)), front=Vector((0, 0, 1)), seg=('RightFoot', 'RightToeBase'), out='TS_Boots.glb',
                       bones=['RightFoot', 'RightToeBase'], length=f('length', 1.04), lift=f('lift', 0.012), lo=f('lo', 0.006),
                       hi=f('hi', 0.012), radius=f('radius', 0.035), roll=f('roll', 0.0), back=f('back', 0.0)),
}[PIECE]
NAME = 'TS_' + PIECE


def limb_only(body, bones, name='limb_proxy'):
    """Copy of the body reduced to the faces weighted to `bones` (and their neighbours in the chain): the fit must not
    see the other leg, the torso or the hand."""
    p = body.copy(); p.data = body.data.copy(); p.name = name; bpy.context.collection.objects.link(p)
    gi = {g.index: g.name for g in p.vertex_groups}
    keep = [sum(g.weight for g in v.groups if gi[g.group] in bones) > 0.05 for v in p.data.vertices]
    bm = bmesh.new(); bm.from_mesh(p.data); bm.verts.ensure_lookup_table()
    kill = [fc for fc in bm.faces if not any(keep[v.index] for v in fc.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(p.data); bm.free()
    for m in list(p.modifiers): p.modifiers.remove(m)
    p.parent = None; p.matrix_world = body.matrix_world.copy(); p.hide_render = True
    return p


PROXY_BONES = {'bracer': ['RightArm', 'RightForeArm', 'RightHand'], 'kneeshin': ['RightUpLeg', 'RightLeg', 'RightFoot'],
               'bootplates': ['RightLeg', 'RightFoot', 'RightToeBase']}


def sole_direction(body):
    """Heel-to-toe direction of the right boot in plan (principal axis of the sole), and the boot's box in that frame."""
    import numpy as np
    ws = [w for w in H.world_verts(body) if w.z < 0.05 and w.x < -0.02]
    P = np.array([(w.x, w.y) for w in ws]); c = P.mean(0); u, s, vt = np.linalg.svd(P - c, full_matrices=False)
    d = Vector((float(vt[0][0]), float(vt[0][1]), 0.0)).normalized()
    if d.y > 0: d = -d                                                   # toes point to -Y
    return d


def fit():
    arm, body = H.load_hero()
    a = H.bone_head(arm, CFG['seg'][0]); b = H.bone_head(arm, CFG['seg'][1]); seg = b - a; segn = seg.normalized()
    proxy = limb_only(body, PROXY_BONES[PIECE])
    p = H.import_piece(H.MESHY / PIECE / 'model.glb', NAME); merged = H.merge_splits(p)
    rec = dict(piece=PIECE, merged=merged, seg_len=round(seg.length, 4))
    bw = H.world_verts(body)
    # ---- orientation: piece long axis -> limb direction; piece front -> the body's front (boots: up), made perpendicular
    if PIECE == 'bootplates':
        segn = sole_direction(body); body_front = Vector((0, 0, 1)); rec['sole_dir'] = [round(v, 4) for v in segn]
    else:
        body_front = Vector((0, -1, 0))
    ax = CFG['axis'].normalized(); fr = CFG['front'] - ax * CFG['front'].dot(ax); fr.normalize()
    tfr = body_front - segn * body_front.dot(segn); tfr.normalize()
    if CFG['roll']: tfr = Matrix.Rotation(math.radians(CFG['roll']), 3, segn) @ tfr
    src = Matrix((ax, fr, ax.cross(fr))).transposed(); dst = Matrix((segn, tfr, segn.cross(tfr))).transposed()
    R = dst @ src.inverted()
    p.data.transform(R.to_4x4()); p.data.update()
    ws = H.world_verts(p); lo, hi = H.bounds(p); c = (lo + hi) / 2
    along = [(w - c).dot(segn) for w in ws]; ext = max(along) - min(along); mid_al = (max(along) + min(along)) / 2
    # ---- uniform scale and place
    if PIECE == 'bracer':
        s = CFG['cover'] * seg.length / ext
        centre = a + seg * CFG['frac']
        # centre of the limb's cross-section there (the bone runs off-centre through the forearm)
        ring = [w for w in H.world_verts(proxy) if abs((w - centre).dot(segn)) < 0.02 and ((w - centre) - segn * (w - centre).dot(segn)).length < 0.12]
        rc = sum(ring, Vector()) / len(ring); rc = centre + ((rc - centre) - segn * (rc - centre).dot(segn))
        rec['axis_offset_mm'] = round((rc - centre).length * 1000, 1); centre = rc
    elif PIECE == 'kneeshin':
        ztop = a.z + CFG['top']; zbot = CFG['bottom']                    # just above the knee joint .. above the boot top
        s = (ztop - zbot) / (ext * abs(segn.z))
        t = ((ztop + zbot) / 2 - a.z) / seg.z; centre = a + seg * t
        ring = [w for w in H.world_verts(proxy) if abs((w - centre).dot(segn)) < 0.03 and ((w - centre) - segn * (w - centre).dot(segn)).length < 0.16]
        rc = sum(ring, Vector()) / len(ring); rc = centre + ((rc - centre) - segn * (rc - centre).dot(segn))
        rec['axis_offset_mm'] = round((rc - centre).length * 1000, 1); centre = rc
    else:
        side = segn.cross(Vector((0, 0, 1)))
        foot = [w for w in bw if w.z < 0.13 and w.x < -0.02]
        al = [w.dot(segn) for w in foot]; sd = [w.dot(side) for w in foot]
        blen = max(al) - min(al); s = CFG['length'] * blen / ext
        rec.update(boot_len=round(blen, 4), boot_width=round(max(sd) - min(sd), 4))
        zmin = min(w.z for w in foot)
        centre = segn * ((max(al) + min(al)) / 2 - CFG['back']) + side * ((max(sd) + min(sd)) / 2)
    p.data.transform(Matrix.Scale(s, 4)); p.data.update()
    lo, hi = H.bounds(p); c = (lo + hi) / 2
    if PIECE == 'bootplates':
        ws = H.world_verts(p); al = [w.dot(segn) for w in ws]; sd = [w.dot(side) for w in ws]
        cur = segn * ((max(al) + min(al)) / 2) + side * ((max(sd) + min(sd)) / 2)
        d = centre - cur; d.z = zmin + CFG['lift'] - lo.z
        p.data.transform(Matrix.Translation(d))
    else:
        ws = H.world_verts(p); al = [(w - c).dot(segn) for w in ws]
        cur = c + segn * ((max(al) + min(al)) / 2)
        p.data.transform(Matrix.Translation(centre - cur))
    p.data.update(); lo, hi = H.bounds(p)
    rec.update(scale=round(s, 5), size=[round(v, 4) for v in hi - lo], pen_placed=H.penetration(p, proxy), gap_placed=H.gap_stats(p, proxy))
    # ---- smooth surface-following fit to the limb
    rec['conform'] = H.conform(p, proxy, lo=CFG['lo'], hi=CFG['hi'], radius=CFG['radius'], iters=int(f('iters', 14)), hard=CFG['lo'] * 0.5)
    lo, hi = H.bounds(p)
    rec.update(size_fitted=[round(v, 4) for v in hi - lo], lo=[round(v, 4) for v in lo], hi=[round(v, 4) for v in hi],
               pen=H.penetration(p, proxy), pen_full_body=H.penetration(p, body), gap=H.gap_stats(p, proxy), tris=H.tris(p),
               cfg={k: v for k, v in CFG.items() if isinstance(v, (int, float, str))}, segn=[round(v, 5) for v in segn])
    H.log('FIT', PIECE, json.dumps(rec)); (H.WORK / f'{PIECE}_fit.json').write_text(json.dumps(rec, indent=1))
    H.export_obj(p, H.WORK / f'{PIECE}_fit.obj')


def boot_weights(o, arm, side_name, segn):
    """Foot / ToeBase by position across the toe joint: 1.5 cm either side of the joint is the blend (the strap)."""
    j = H.bone_head(arm, side_name + 'ToeBase'); d = Vector(segn)
    if side_name == 'Left': d = Vector((-d.x, d.y, d.z))
    gf = o.vertex_groups.new(name=side_name + 'Foot'); gt = o.vertex_groups.new(name=side_name + 'ToeBase'); n = 0
    for v in o.data.vertices:
        t = ((o.matrix_world @ v.co) - j).dot(d); w = max(0.0, min(1.0, (t + 0.015) / 0.03)); w = w * w * (3 - 2 * w)
        if w > 1e-3: gt.add([v.index], w, 'REPLACE'); n += 1
        if w < 1 - 1e-3: gf.add([v.index], 1 - w, 'REPLACE')
    return n


def skin(objname):
    arm, body = H.load_hero()
    rec = json.loads((H.WORK / f'{PIECE}_fit.json').read_text())
    r = H.import_obj(H.WORK / f'{objname}.obj', NAME); H.log('MERGED', H.merge_splits(r))
    proxy_r = limb_only(body, PROXY_BONES[PIECE], 'proxy_r')
    proxy_l = limb_only(body, [b.replace('Right', 'Left') for b in PROXY_BONES[PIECE]], 'proxy_l')
    l = H.mirror_x(r, NAME + '_L')
    # final touch on each side against its own limb (decimation moved vertices; left and right limbs differ slightly)
    for o, px, tag in ((r, proxy_r, 'right'), (l, proxy_l, 'left')):
        st = H.conform(o, px, lo=CFG['lo'], hi=CFG['hi'], radius=CFG['radius'], iters=5, hard=CFG['lo'] * 0.5)
        H.log('TOUCH-UP', tag, st, 'pen', H.penetration(o, px), 'gap', H.gap_stats(o, px))
    for o, sn in ((r, 'Right'), (l, 'Left')):
        H.smooth_shade(o, 50); H.clear_groups(o)
        if PIECE == 'bootplates': H.log('TOE verts', sn, boot_weights(o, arm, sn, rec['segn']))
        else: H.skin_rigid(o, CFG['bones'][0].replace('Right', sn))
        H.log('UNWEIGHTED', H.ensure_weighted(o, CFG['bones'][0].replace('Right', sn)))
    bpy.ops.object.select_all(action='DESELECT'); r.select_set(True); l.select_set(True); bpy.context.view_layer.objects.active = r
    bpy.ops.object.join(); p = bpy.context.view_layer.objects.active; p.name = NAME; p.data.name = NAME
    H.bind(p, arm); (H.WORK / 'stage').mkdir(exist_ok=True)
    H.export_skinned(p, arm, H.WORK / 'stage' / CFG['out'])


if STAGE == 'fit': fit()
elif STAGE == 'skin': skin(f'{PIECE}_dec')
elif STAGE == 'full': skin(f'{PIECE}_fit')
