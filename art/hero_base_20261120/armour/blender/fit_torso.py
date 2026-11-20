"""Hero armour: scrap chest rig (vest) and Warden plate carrier fitted to the new, broader torso.
Port of art/colonist_back_20261120/blender/fit_piece.py (20 Nov re-fit from the full Meshy sources: no strip_inner,
UV-seam splits merged, texture-aware decimation outside Blender, torso weights, vest hem cut at the plates, shoulder
pad as a cap). What had to change for the new body and rig:

  * FITTED IN THE NEUTRAL POSE, NOT THE REST POSE. The rest pose is Meshy's A-pose, but every clip in the game holds
    the collarbones about 20 degrees off it, and on this rig the collarbones own most of the upper chest and back
    (0.5-0.9 of the weight down to the armpits). A vest fitted to the A-pose torso is 3-8 cm inside the shoulders as
    soon as a clip plays. So the body is posed with the idle clip's collarbone and arm rotations (hlib 'neutral': spine
    upright), the piece is fitted to that shape, weighted, and then carried back to the rest pose by inverse skinning
    (H.unpose), so that in the game it sits exactly as fitted.
  * the uniform scale still comes from the chest depth, but the piece is hung from the SHOULDER LINE (the new rig's neck
    joint sits 6 cm below the top of the trapezius, so "top at the neck joint" buried the straps in the shoulders);
  * front/back are balanced on the real chest and back surfaces (the new torso is 5 cm deeper, mostly at the back);
  * weights: from the arm-less torso, torso bones only, smoothed. The shipped rule (collarbone weight faded out below
    the armpits) cannot be used: the body under the vest moves with the collarbones, so the canvas must too. Each steel
    plate gets ONE constant blend (the mean of its vertices' weights), which moves it as a rigid sheet that follows the
    average of the torso under it; the shoulder pad is a rigid cap on LeftShoulder 0.6 / LeftArm 0.4 as shipped.
Stage 'fit'  -> work/<piece>_fit.obj (neutral-pose space) + work/<piece>_fit.json;  stage 'skin' -> work/stage/<file>.glb
Usage: blender.sh fit_torso.py -- <vest|carrier> <fit|skin|full> [mult=1.0] [rise=0.012] [dy=0] [cut=..] [gap=0.007]"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh, math, json
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:]
PIECE, STAGE = args[0], args[1]; opt = dict(a.split('=', 1) for a in args[2:] if '=' in a)
SPEC = {
    'vest':    dict(src=H.MESHY / 'chest' / 'model.glb', name='TS_FieldVest', file='TS_FieldVest.glb', fac=0.86, cut=0.0),
    'carrier': dict(src=H.CARRIER_SRC, name='TS_WardenCarrier', file='TS_WardenCarrier.glb', fac=0.86, cut=0.04),
}[PIECE]
MULT = float(opt.get('mult', 1.0)); RISE = float(opt.get('rise', 0.012)); DY = float(opt.get('dy', 0.0))
CUT = float(opt.get('cut', SPEC['cut'])); GAP = float(opt.get('gap', 0.007)); SNUG = float(opt.get('snug', 0.016))
STRAP = float(opt.get('strap', 0.011)); PADGAP = float(opt.get('padgap', 0.010)); PADSHARE = float(opt.get('padshare', 0.4))
POSE = opt.get('pose', 'neutral')
TORSO = H.TORSO
METAL = str(H.MESHY / 'chest' / 'tex0_metallic.png')


def setup():
    """Hero in the neutral pose; a frozen copy of the posed body and its arm-less torso to fit against."""
    arm, body = H.load_hero(); H.set_pose(arm, body, POSE)
    posed = H.posed_copy(body, 'body_neutral'); tp = torso_proxy(posed)
    return arm, body, posed, tp, H.pose_mats(arm)


def torso_proxy(body):
    """Copy of the body without the arms (faces whose vertices are mostly weighted to upper arm, forearm, hand or
    finger bones): the nearest surface under an armpit must be the rib cage, not the inside of the upper arm."""
    p = body.copy(); p.data = body.data.copy(); p.name = 'torso_proxy'; bpy.context.collection.objects.link(p)
    names = {g.index: g.name.lower() for g in p.vertex_groups}
    def armw(v):
        return sum(g.weight for g in v.groups if ('arm' in names[g.group] or 'hand' in names[g.group] or
                   names[g.group].startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))) and 'shoulder' not in names[g.group])
    isarm = [armw(v) > 0.5 for v in p.data.vertices]
    bm = bmesh.new(); bm.from_mesh(p.data); bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if sum(isarm[v.index] for v in f.verts) >= 2]
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(p.data); bm.free()
    for m in list(p.modifiers): p.modifiers.remove(m)
    p.parent = None; p.matrix_world = body.matrix_world.copy(); p.hide_render = True
    H.log('PROXY removed arm faces', len(kill)); return p


def metal_per_vertex(o, path=METAL):
    """Meshy metallic map sampled at each vertex's UV (max over its loops): 1 on the steel plates and pad."""
    import numpy as np
    img = bpy.data.images.load(path); w, h = img.size
    px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(h, w, 4)[..., 0]
    uv = o.data.uv_layers.active.data; m = [0.0] * len(o.data.vertices)
    for poly in o.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            u, v = uv[li].uv; x = min(w - 1, max(0, int(u % 1.0 * w))); y = min(h - 1, max(0, int(v % 1.0 * h)))
            m[vi] = max(m[vi], float(px[y, x]))
    bpy.data.images.remove(img); return m


def hem_cut(c, cy):
    """Cut the crumpled canvas skirt off the source rig: a plane tilted front-to-back 1 cm up into each plate's lowest
    point, so the vest ends in the plates' own straight bottom edges."""
    m = metal_per_vertex(c); ws = [c.matrix_world @ v.co for v in c.data.vertices]
    B = [(w, mm) for w, mm in zip(ws, m) if mm > 0.5 and w.y > cy + 0.04 and abs(w.x) < 0.13]
    F = [(w, mm) for w, mm in zip(ws, m) if mm > 0.5 and w.y < cy - 0.04 and abs(w.x) < 0.13]
    yb = sum(w.y for w, _ in B) / len(B); yf = sum(w.y for w, _ in F) / len(F)
    zb = min(w.z for w, _ in B) + 0.011; zf = min(w.z for w, _ in F) + 0.011; slope = (zb - zf) / (yb - yf)
    co = Vector((0, yf, zf)); no = Vector((0, -slope, 1)).normalized()
    bm = bmesh.new(); bm.from_mesh(c.data); n0 = len(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_inner=True)
    n1 = len(bm.faces); bm.to_mesh(c.data); bm.free(); c.data.update()
    H.log('HEM cut back %.3f front %.3f faces %d -> %d' % (zb, zf, n0, n1)); return zb, zf


def snug_flanks(piece, proxy, zmax, gap, x_min, k=0.9, radius=0.06):
    """The source rig is sized by chest depth, so its side panels and cummerbund wings stand off the flanks. Pull only
    the flank vertices (|x| > x_min, below the armpits) in towards the arm-less torso, Gaussian-smoothed."""
    return H.shrink_fit(piece, proxy, gap=gap, k=k, radius=radius, iters=3, keep=lambda w: abs(w.x) < x_min or w.z > zmax)


def smooth_plates(c, iters=6):
    """Laplacian smoothing along the normal of the interior of the steel plates: takes out the shading facets the
    push-out and decimation leave on what should be flat sheet (texture does not slide)."""
    m = metal_per_vertex(c)
    bm = bmesh.new(); bm.from_mesh(c.data); bm.verts.ensure_lookup_table()
    sel = [v.index for v in bm.verts if m[v.index] > 0.3 and not v.is_boundary and all(m[e.other_vert(v).index] > 0.3 for e in v.link_edges)]
    bm.free(); return H.relax_normal(c, sel, iters=iters)


def shoulder_top(bvh, x, ztop, y0=-0.12, y1=0.18):
    """Top of the trapezius at |x| (rays start under the jaw so they find the shoulders, not the head)."""
    best = None
    for yi in range(int(y0 * 100), int(y1 * 100) + 1):
        for sx in (1, -1):
            hit = bvh.ray_cast(Vector((sx * x, yi * 0.01, ztop)), Vector((0, 0, -1)), 0.6)
            if hit[0] is not None and (best is None or hit[0].z > best): best = hit[0].z
    return best


def median(xs):
    xs = sorted(xs); return xs[len(xs) // 2] if xs else None


def place(c, posed, arm, tp):
    """Uniform scale from the chest depth (shipped recipe), then: centred in x, front and back gaps balanced in y,
    hung so the shoulder straps rest `RISE` above the trapezius."""
    NECKZ = H.pose_head(arm, 'neck').z
    ws = H.world_verts(posed)
    band = [w for w in ws if NECKZ - 0.25 < w.z < NECKZ - 0.17 and abs(w.x) < 0.09]
    ys = [w.y for w in band]; cd = max(ys) - min(ys); cy = (max(ys) + min(ys)) / 2
    lo, hi = H.bounds(c); s = cd / ((hi - lo).y * SPEC['fac']) * MULT
    c.scale = (s, s, s); H.apply(c); lo, hi = H.bounds(c)
    bvh, bm = H.body_bvh(tp)
    strap_x = 0.115 * MULT * 1.128                  # the straps' middle: beside the neck, clear of the head
    zs = shoulder_top(bvh, strap_x, NECKZ + 0.11)
    c.location = (0.0, cy - (lo.y + hi.y) / 2 + DY, zs + 0.03 - hi.z); H.apply(c)
    if PIECE == 'vest':                       # centre on the plates, not on the bounding box (the pad is on one side)
        m = metal_per_vertex(c); xs = [(c.matrix_world @ v.co).x for v in c.data.vertices if m[v.index] > 0.5 and abs((c.matrix_world @ v.co).x) < 0.2 and (c.matrix_world @ v.co).z < zs - 0.12]
        cxp = (max(xs) + min(xs)) / 2; c.location = (-cxp, 0, 0); H.apply(c)
    nrm = H.vert_normals_world(c)
    def sds(pred, up=False):
        out = []
        for v in c.data.vertices:
            w = c.matrix_world @ v.co
            if not pred(w): continue
            hit = bvh.find_nearest(w, 0.3)
            if hit[0] is None or (up and hit[1].z < 0.6): continue
            if nrm[v.index].dot(hit[1]) < -0.2: out.append((w - hit[0]).dot(hit[1]))
        return out
    lo, hi = H.bounds(c)
    # 1. hang from the shoulders: the lowest 10 % of the strap undersides sit RISE above the trapezius
    for _ in range(4):
        d = sds(lambda w: w.z > hi.z - 0.09 and 0.06 < abs(w.x) < 0.22, up=True)
        if not d: break
        d.sort(); cur = d[len(d) // 10]
        c.location = (0, 0, RISE - cur); H.apply(c); lo, hi = H.bounds(c)
    # 2. balance front and back over the plates' height
    zmid0 = lo.z + 0.25 * (hi.z - lo.z); zmid1 = lo.z + 0.75 * (hi.z - lo.z)
    fb = lambda: (median(sds(lambda w: w.y < cy - 0.05 and abs(w.x) < 0.11 and zmid0 < w.z < zmid1)),
                  median(sds(lambda w: w.y > cy + 0.05 and abs(w.x) < 0.11 and zmid0 < w.z < zmid1)))
    for _ in range(3):
        f, b = fb()
        if f is None or b is None: break
        c.location = (0, (f - b) / 2, 0); H.apply(c)
    f, b = fb(); bm.free(); lo, hi = H.bounds(c)
    return dict(scale=round(s, 5), chest_depth=round(cd, 4), cy=round(cy, 4), shoulder_z=round(zs, 4), strap_x=round(strap_x, 4),
                front_gap_mm=round(f * 1000, 1) if f is not None else None, back_gap_mm=round(b * 1000, 1) if b is not None else None,
                lo=[round(v, 4) for v in lo], hi=[round(v, 4) for v in hi]), cy


def pad_set(c, arm, metal=None, solid=0.025, reach=0.02):
    """Shoulder pad vertices with a 0..1 falloff into the strap it hangs from. The pad is the steel cap outboard of
    the left strap: its steel (metallic in the Meshy map) plus everything within `solid` of that steel is the pad
    proper (painted and rusted patches inside the cap are not metallic in the map; with a per-vertex test they got
    part weights and the cap broke into shards), then a falloff of `reach` into the strap.
    The shipped rule (a box outboard of the shoulder joint) also caught the edge of the back panel on the wider vest,
    which then swung with the arm."""
    if metal is None: metal = metal_per_vertex(c)
    j = H.pose_head(arm, 'LeftArm'); ws = [c.matrix_world @ v.co for v in c.data.vertices]
    core = [i for i, w in enumerate(ws) if metal[i] > 0.5 and w.x > j.x - 0.045 and w.z > j.z - 0.10]
    if not core: return {}
    kd = KDTree(len(core))
    for k, i in enumerate(core): kd.insert(ws[i], k)
    kd.balance(); out = {}
    for i, w in enumerate(ws):
        if w.x < j.x - 0.075: continue
        d = kd.find(w)[2]
        if d < solid: out[i] = 1.0
        elif d < solid + reach:
            f = 1.0 - (d - solid) / reach; out[i] = f * f * (3 - 2 * f)
    return out


def pad_cap(c, arm, pad, share=0.4, scale=0.92):
    """The pad as a cap on the shoulder: a little smaller, drawn in towards the shoulder joint, riding the clavicle
    with some upper arm (shipped recipe: LeftShoulder 0.6 / LeftArm 0.4)."""
    j = H.pose_head(arm, 'LeftArm') + Vector((0, 0, 0.05))
    inv = c.matrix_world.inverted()
    gs = c.vertex_groups.get('LeftShoulder') or c.vertex_groups.new(name='LeftShoulder')
    ga = c.vertex_groups.get('LeftArm') or c.vertex_groups.new(name='LeftArm')
    for i, f in pad.items():
        v = c.data.vertices[i]; w = c.matrix_world @ v.co
        v.co = inv @ (w + (j + (w - j) * scale - w) * f)
        old = {g.group: g.weight * (1 - f) for g in v.groups}
        for k in list(old): c.vertex_groups[k].remove([i])
        old[gs.index] = old.get(gs.index, 0) + f * (1 - share); old[ga.index] = old.get(ga.index, 0) + f * share
        for k, wt in old.items():
            if wt > 1e-4: c.vertex_groups[k].add([i], wt, 'REPLACE')
    return len(pad)


def rigid_plates(c, metal, cy, pad, ztop, reach=0.035):
    """Steel does not bend: every vertex of a plate gets the SAME weights, the mean of what the body gave the plate's
    vertices. A constant blend moves the plate as one rigid sheet that follows the average of the torso under it
    (chest, belly and what the collarbones do to the upper chest), so it neither bends at the waist joint nor shears
    with one shoulder. Canvas within `reach` of a plate blends towards it."""
    names = {g.index: g.name for g in c.vertex_groups}; out = {}
    ws = [c.matrix_world @ v.co for v in c.data.vertices]
    for tag, pred in (('front', lambda w: w.y < cy), ('back', lambda w: w.y >= cy)):
        idx = [i for i, w in enumerate(ws) if metal[i] > 0.5 and pred(w) and pad.get(i, 0) < 0.05 and abs(w.x) < 0.17 and w.z < ztop]   # plates, not strap buckles
        if len(idx) < 20: continue
        tot = {}
        for i in idx:
            for g in c.data.vertices[i].groups: tot[names[g.group]] = tot.get(names[g.group], 0) + g.weight
        # the two collarbones pull a centred plate equally: give them the same share
        cl = (tot.get('LeftShoulder', 0) + tot.get('RightShoulder', 0)) / 2
        if cl > 0: tot['LeftShoulder'] = tot['RightShoulder'] = cl
        tsum = sum(tot.values()); rank = sorted(((v / tsum, k) for k, v in tot.items()), reverse=True)
        if cl / tsum > 0.05:                  # four influences at most: both collarbones plus the two strongest others
            mean = [(cl / tsum, 'LeftShoulder'), (cl / tsum, 'RightShoulder')] + [r for r in rank if 'Shoulder' not in r[1]][:2]
        else: mean = [r for r in rank if 'Shoulder' not in r[1]][:4]
        tsum = sum(v for v, _ in mean); mean = {(c.vertex_groups.get(k) or c.vertex_groups.new(name=k)).index: v / tsum for v, k in mean}
        kd = KDTree(len(idx))
        for k, i in enumerate(idx): kd.insert(ws[i], k)
        kd.balance(); n = 0; isplate = set(idx); zbot = min(ws[i].z for i in idx)
        for v in c.data.vertices:
            if pad.get(v.index, 0) > 0.5: continue
            if (ws[v.index].y < cy) != (tag == 'front'): continue          # the other side of the body is the other plate's
            d = kd.find(ws[v.index])[2]
            if ws[v.index].z < zbot + 0.02 and abs(ws[v.index].x) < 0.20:
                # the canvas hem under a plate hangs from that plate: on its own (hip) weights it flared out as a
                # ragged fringe whenever the waist bent
                if d > 0.11: continue
                f = 1.0 if d < 0.07 else 1.0 - (d - 0.07) / 0.04
            else:
                if d > reach: continue
                f = 1.0 - d / reach
            f = f * f * (3 - 2 * f)
            if v.index in isplate: f = 1.0
            old = {g.group: g.weight * (1 - f) for g in v.groups}
            for k in list(old): c.vertex_groups[k].remove([v.index])
            for k, wt in mean.items(): old[k] = old.get(k, 0) + f * wt
            for k, wt in old.items():
                if wt > 1e-4: c.vertex_groups[k].add([v.index], wt, 'REPLACE')
            n += 1
        out[tag] = dict(weights={c.vertex_groups[k].name: round(v, 3) for k, v in mean.items()}, plate_verts=len(idx), touched=n,
                        top_z=round(max(ws[i].z for i in idx), 4), bottom_z=round(min(ws[i].z for i in idx), 4))
    return out


def fit():
    arm, body, posed, tp, mats = setup()
    c = H.import_piece(SPEC['src'], SPEC['name']); H.log('MERGED', H.merge_splits(c))
    rec, cy = place(c, posed, arm, tp); rec['pose'] = POSE
    HIPZ = H.pose_head(arm, 'Hips').z
    if CUT:
        bm = bmesh.new(); bm.from_mesh(c.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, HIPZ + CUT),
                               plane_no=(0, 0, 1), clear_inner=True)
        bm.to_mesh(c.data); bm.free(); c.data.update(); rec['cut_z'] = round(HIPZ + CUT, 4)
    if PIECE == 'vest': rec['hem'] = [round(v, 4) for v in hem_cut(c, cy)]
    armz = min(H.pose_head(arm, 'LeftArm').z, H.pose_head(arm, 'RightArm').z); rec['arm_joint_z'] = round(armz, 4)
    rec['snug_moved'] = snug_flanks(c, tp, armz - 0.07, SNUG, x_min=0.15)
    # shoulder straps: follow the trapezius and upper chest/back (they arched over the shoulder with daylight under
    # them); soft lower edge at the armpit line, the pad is left for pad_cap
    zs = armz - 0.02
    pad = pad_set(c, arm) if PIECE == 'vest' else {}; rec['pad_verts'] = len(pad)
    wt = []
    for v in c.data.vertices:
        z = (c.matrix_world @ v.co).z; f = max(0.0, min(1.0, (z - (zs - 0.05)) / 0.05)); f = f * f * (3 - 2 * f)
        wt.append(f * (1.0 - pad.get(v.index, 0.0)))
    rec['straps'] = H.conform(c, tp, lo=GAP, hi=STRAP, radius=0.045, iters=6, weight=wt)
    n0 = H.penetration(c, tp); moved = H.push_out_smooth(c, tp, offset=GAP, radius=0.07)
    if PIECE == 'vest': rec['plates_smoothed'] = smooth_plates(c)
    rec.update(pen_before=n0, pushed=moved, pen_after=H.penetration(c, tp), pen_full_body=H.penetration(c, posed),
               gap=H.gap_stats(c, tp), tris=H.tris(c), mult=MULT, rise=RISE, dy=DY, cut=CUT, gap_offset=GAP, snug=SNUG)
    lo, hi = H.bounds(c); rec['lo'] = [round(v, 4) for v in lo]; rec['hi'] = [round(v, 4) for v in hi]
    H.log('FIT', PIECE, json.dumps(rec)); (H.WORK / f'{PIECE}_fit.json').write_text(json.dumps(rec, indent=1))
    H.export_obj(c, H.WORK / f'{PIECE}_fit.obj')


def skin(objname):
    arm, body, posed, tp, mats = setup()
    rec = json.loads((H.WORK / f'{PIECE}_fit.json').read_text()); cy = rec['cy']
    assert rec.get('pose') == POSE, 'the fit stage was run in another pose: run fit again'
    c = H.import_obj(H.WORK / f'{objname}.obj', SPEC['name'])
    H.log('MERGED', H.merge_splits(c))
    # decimation moves vertices: clear the torso again on the final mesh, then flatten the plates
    H.log('TOUCH-UP', H.push_out_smooth(c, tp, offset=GAP - 0.002, radius=0.04, iters=4), 'pen', H.penetration(c, tp))
    if PIECE == 'vest': H.log('PLATE smoothed', smooth_plates(c))
    H.smooth_shade(c, 50)
    # weights from the arm-less torso in the pose the piece was fitted in
    H.clear_groups(c)
    H.skin_transfer(c, tp, bones=TORSO); H.log('UNWEIGHTED', H.ensure_weighted(c, 'Spine01'))
    H.smooth_weights(c, iters=3)
    metal = metal_per_vertex(c) if PIECE == 'vest' else None
    pad = pad_set(c, arm, metal) if PIECE == 'vest' else {}
    if PIECE == 'vest':
        H.log('PLATES', json.dumps(rigid_plates(c, metal, cy, pad, rec['shoulder_z'] - 0.075)))
        H.log('PAD cap', pad_cap(c, arm, pad, share=PADSHARE))
        # the cap sits on the new, bigger deltoid: clear it (full body, arms included) by PADGAP, smoothly
        wt = [pad.get(v.index, 0.0) for v in c.data.vertices]
        H.conform(c, posed, lo=PADGAP, hi=PADGAP + 0.006, radius=0.05, iters=8, weight=wt, hard=PADGAP * 0.6, log_tag='pad')
    H.normalise(c)
    H.log('FITTED POSE', POSE, 'pen torso', H.penetration(c, tp), 'pen full body', H.penetration(c, posed), 'gap', json.dumps(H.gap_stats(c, tp)))
    # back to the rest pose: each vertex to the rest position its own weights carry to where it is now
    H.log('UNPOSE max move %.1f mm' % (H.unpose(c, mats) * 1000))
    for o in (posed, tp): bpy.data.objects.remove(o, do_unlink=True)
    H.rest(arm); H.log('REST POSE pen full body', H.penetration(c, body))
    H.bind(c, arm); (H.WORK / 'stage').mkdir(exist_ok=True)
    H.export_skinned(c, arm, H.WORK / 'stage' / SPEC['file'])


if STAGE == 'fit': fit()
elif STAGE == 'skin': skin(f'{PIECE}_dec')
elif STAGE == 'full': skin(f'{PIECE}_fit')
