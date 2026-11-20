"""Colonist back pass (20 Nov 2026): re-fit a torso/head armour piece from its full-detail Meshy source without the
two steps that tore it up in the shipped export (tutorial_set_20261002/blender/fit_vest.py & co.):
  - fitlib.strip_inner deleted a third of the double-walled shell (10,052 of 30,402 vest faces), opening holes such
    as the notch under the back plate and leaving one-sided ragged rims at the armholes and hem;
  - fitlib.decimate (Blender COLLAPSE 40 %) ran on a mesh still split at every UV seam, so each seam collapsed on its
    own and tore into the flaky jagged borders seen along the straps.
Stage 'fit'   : scale/place exactly as the shipped recipe, merge the UV-seam splits, smooth push-out against the shipped
                body + suit (the polish blend), write work/<piece>_fit.obj (UVs kept).
Stage 'skin'  : import work/<piece>_dec.obj (texture-aware quadric decimation by decimate.py), material from the Meshy
                source, smooth normals, skin weights from the body as before, export out/<file>.glb on the player rig.
Usage: blender.sh fit_piece.py -- <vest|carrier|helmet> <fit|skin|full>   (full = skin from the undecimated fit)"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
import fitlib as F
import bpy, bmesh, math
from mathutils import Vector, Matrix
POLISH = '/home/teknetik/code/ao2/art/character_polish_20261005/player_polish.blend'
HERE = '/home/teknetik/code/ao2/art/colonist_back_20261120/'
args = sys.argv[sys.argv.index('--') + 1:]
PIECE, STAGE = args[0], args[1]
SPEC = {
    'vest':    dict(src=F.MESHY / 'chest' / 'model.glb', name='TS_FieldVest', file='TS_FieldVest.glb', fac=0.86, cut=0.0),
    'carrier': dict(src=F.AO2 / 'unity/AthenHill/Assets/AthenHill/Art/Armour/WardenPlateCarrier.glb', name='TS_WardenCarrier',
                    file='TS_WardenCarrier.glb', fac=0.86, cut=0.04),
    'helmet':  dict(src=F.MESHY / 'helmet' / 'model.glb', name='TS_Helmet', file='TS_Helmet.glb'),
}[PIECE]
# The shipped recipe also took LeftArm/RightArm weights from the body: in the idle pose (arms lowered from the A-pose
# rest) those dragged the vest's side panels and armhole rims down with the arms into long smeared flaps. Torso bones
# only; the left shoulder pad (a loose part above the left shoulder) follows the clavicle with some upper arm.
TORSO = ['Hips', 'Spine02', 'Spine01', 'Spine', 'neck', 'LeftShoulder', 'RightShoulder']

def load_body():
    bpy.ops.wm.open_mainfile(filepath=POLISH)
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['char1']
    if arm.animation_data:
        arm.animation_data.action = None
        for t in arm.animation_data.nla_tracks: t.mute = True
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update(); return arm, body

def torso_proxy(body):
    """Copy of the body + suit without the arms (faces whose vertices are mostly weighted to upper arm, forearm,
    hand or finger bones). Pushing the vest out against the full body let the nearest surface under the armpit be the
    inside of the upper arm, which shoved the side-panel vertices sideways into saw-tooth spikes."""
    p = body.copy(); p.data = body.data.copy(); p.name = 'torso_proxy'; bpy.context.collection.objects.link(p)
    names = {g.index: g.name.lower() for g in p.vertex_groups}
    def armw(v):
        return sum(g.weight for g in v.groups if ('arm' in names[g.group] or 'hand' in names[g.group] or
                   names[g.group].startswith(('thumb', 'index', 'middle', 'ring', 'pinky')) ) and 'shoulder' not in names[g.group])
    isarm = [armw(v) > 0.5 for v in p.data.vertices]
    bm = bmesh.new(); bm.from_mesh(p.data); bm.verts.ensure_lookup_table()
    kill = [f for f in bm.faces if sum(isarm[v.index] for v in f.verts) >= 2]
    bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(p.data); bm.free()
    for m in list(p.modifiers): p.modifiers.remove(m)
    p.parent = None; p.matrix_world = body.matrix_world.copy()
    print('PROXY removed arm faces', len(kill)); return p

def snug_flanks(piece, body, arm, gap=0.028, k=0.9, radius=0.06, x_min=0.125):
    """The source rig is sized by chest depth, so its side panels and cummerbund wings stand far off the narrower
    flanks; in the idle pose they read as loose flaps either side of the back plate. Pull only the flank vertices
    (|x| > x_min, below the armpits) in towards the torso (arm-less proxy), Gaussian-smoothed like fitlib.shrink_fit."""
    from mathutils.kdtree import KDTree
    zmax = min(F.bone_head(arm, 'LeftArm').z, F.bone_head(arm, 'RightArm').z) - 0.07
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); moved = 0
    for it in range(3):
        bvh, bm = F.body_bvh(body); ws = [mw @ v.co for v in me.vertices]; req = [Vector()] * len(ws)
        for i, w in enumerate(ws):
            if abs(w.x) < x_min or w.z > zmax: continue
            hit = bvh.find_nearest(w, 0.25)
            if hit[0] is None: continue
            side = (w - hit[0]).dot(hit[1])
            if side > gap: req[i] = -hit[1] * (side - gap) * k
        bm.free(); kd = KDTree(len(ws))
        for i, w in enumerate(ws): kd.insert(w, i)
        kd.balance(); s2 = (radius / 2) ** 2
        for i, w in enumerate(ws):
            acc = Vector(); wt = 0.0
            for co, j, dist in kd.find_range(w, radius):
                g = math.exp(-dist * dist / (2 * s2)); acc += req[j] * g; wt += g
            d = acc / wt if wt else Vector()
            if d.length > 1e-5: moved += 1; me.vertices[i].co = inv @ (w + d)
        me.update()
    return moved


METAL = str(F.MESHY / 'chest' / 'tex0_metallic.png')
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

def hem_cut(c):
    """Cut the crumpled canvas skirt off the source rig: one straight horizontal edge 1.5 cm under the lowest plate."""
    m = metal_per_vertex(c); ws = [c.matrix_world @ v.co for v in c.data.vertices]
    back = [w.z for w, mm in zip(ws, m) if mm > 0.5 and w.y > 0.04 and abs(w.x) < 0.12]
    front = [w.z for w, mm in zip(ws, m) if mm > 0.5 and w.y < -0.04 and abs(w.x) < 0.12]
    # a plane tilted front-to-back through 1.2 cm under each plate's lowest point (the back plate sits higher)
    yb = sum(w.y for w, mm in zip(ws, m) if mm > 0.5 and w.y > 0.04 and abs(w.x) < 0.12) / len(back)
    yf = sum(w.y for w, mm in zip(ws, m) if mm > 0.5 and w.y < -0.04 and abs(w.x) < 0.12) / len(front)
    zb, zf = min(back) + 0.010, min(front) + 0.010; slope = (zb - zf) / (yb - yf)   # through the plates: their own bottom edge was notched
    co = Vector((0, yf, zf)); no = Vector((0, -slope, 1)).normalized()
    bm = bmesh.new(); bm.from_mesh(c.data); n0 = len(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no, clear_inner=True)
    n1 = len(bm.faces); bm.to_mesh(c.data); bm.free(); c.data.update()
    print('HEM back plate bottom %.3f front %.3f cut back %.3f front %.3f faces %d -> %d' % (min(back), min(front), zb, zf, n0, n1)); return zb

def pad_set(c, arm):
    """Shoulder pad vertices (left shoulder, outboard of the strap) with a 0..1 falloff into the strap."""
    j = F.bone_head(arm, 'LeftArm'); out = {}
    for v in c.data.vertices:
        w = c.matrix_world @ v.co
        f = max(0.0, min(1.0, (w.x - (j.x - 0.035)) / 0.03)) * max(0.0, min(1.0, (w.z - (j.z - 0.13)) / 0.03))
        if f > 0: out[v.index] = f * f * (3 - 2 * f)
    return out

def pad_cap(c, arm, pad, share=0.4, scale=0.88):
    """The pad as a cap on the shoulder: a little smaller, drawn in towards the shoulder joint, riding the clavicle with
    some upper arm (it was on the spine only and stood off the arm as a big shard)."""
    j = F.bone_head(arm, 'LeftArm') + Vector((0, 0, 0.05))
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

def smooth_plates(c, iters=6):
    """Laplacian-smooth the interior of the steel plates (all neighbours steel) to take out the shading facets the
    push-out and decimation left on what should be flat sheet."""
    m = metal_per_vertex(c)
    bm = bmesh.new(); bm.from_mesh(c.data); bm.verts.ensure_lookup_table()
    sel = [v for v in bm.verts if m[v.index] > 0.3 and not v.is_boundary and all(m[e.other_vert(v).index] > 0.3 for e in v.link_edges)]
    # along the vertex normal only: a plain Laplacian also slides the vertices over the surface and smears the plate's
    # texture (seen in the first fix-round render)
    for _ in range(iters):
        bm.normal_update()
        moves = []
        for v in sel:
            avg = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
            moves.append(v.normal * (avg - v.co).dot(v.normal) * 0.5)
        for v, d in zip(sel, moves): v.co += d
    bm.to_mesh(c.data); bm.free(); c.data.update(); return len(sel)

def pad_mask(c, pad, res=2048):
    """UV-space mask of the pad faces (R) and an 'edge' weight (G: near the pad's 3D border) for clean_tex.py."""
    import numpy as np
    from mathutils.kdtree import KDTree
    ws = [c.matrix_world @ v.co for v in c.data.vertices]
    others = [i for i in range(len(ws)) if pad.get(i, 0) < 0.5]
    kd = KDTree(len(others))
    for k, i in enumerate(others): kd.insert(ws[i], k)
    kd.balance()
    mask = np.zeros((res, res, 2), np.float32); uv = c.data.uv_layers.active.data
    for p in c.data.polygons:
        if min(pad.get(i, 0) for i in p.vertices) < 0.5: continue
        edge = max(0.0, 1.0 - min(kd.find(ws[i])[2] for i in p.vertices) / 0.02)
        pts = [uv[li].uv for li in p.loop_indices]
        for t in range(1, len(pts) - 1):
            a, b, d = [np.array([q[0] * res, (1 - q[1]) * res]) for q in (pts[0], pts[t], pts[t + 1])]
            x0, y0 = np.floor(np.minimum(np.minimum(a, b), d)).astype(int) - 1; x1, y1 = np.ceil(np.maximum(np.maximum(a, b), d)).astype(int) + 1
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, res), min(y1, res)
            if x1 <= x0 or y1 <= y0: continue
            gx, gy = np.meshgrid(np.arange(x0, x1) + .5, np.arange(y0, y1) + .5)
            den = (b[1] - d[1]) * (a[0] - d[0]) + (d[0] - b[0]) * (a[1] - d[1])
            if abs(den) < 1e-9: continue
            l1 = ((b[1] - d[1]) * (gx - d[0]) + (d[0] - b[0]) * (gy - d[1])) / den
            l2 = ((d[1] - a[1]) * (gx - d[0]) + (a[0] - d[0]) * (gy - d[1])) / den
            ins = (l1 >= -0.02) & (l2 >= -0.02) & (1 - l1 - l2 >= -0.02)
            sub = mask[y0:y1, x0:x1]; sub[ins, 0] = 1.0; sub[ins, 1] = np.maximum(sub[ins, 1], edge)
    np.save(HERE + 'work/vest_padmask.npy', mask); return int((mask[..., 0] > 0).sum())

def merge_splits(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    n0 = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    n1 = len(bm.verts); bm.to_mesh(o.data); bm.free(); o.data.update(); return n0 - n1

def fit():
    arm, body = load_body()
    if PIECE == 'helmet':
        ws = F.world_verts(body); top = max(w.z for w in ws)
        cap = [w for w in ws if w.z > top - 0.13]
        xs = [w.x for w in cap]; ys = [w.y for w in cap]
        hd = max(ys) - min(ys); cx = (max(xs) + min(xs)) / 2; cy = (max(ys) + min(ys)) / 2
        h = F.import_piece(SPEC['src'], SPEC['name']); print('MERGED', merge_splits(h))
        lo, hi = F.bounds(h); MARGIN = 0.016
        s = (hd + 2 * MARGIN) / ((hi - lo).y * 0.93); h.scale = (s, s, s); F.apply(h); lo, hi = F.bounds(h)
        h.location = (cx - (lo.x + hi.x) / 2, cy - (lo.y + hi.y) / 2 + 0.006, top + MARGIN * 0.9 - hi.z); F.apply(h)
        moved = F.push_out(h, body, offset=0.004, max_dist=0.05, smooth=6)
        print('FIT helmet scale %.4f moved %d pen %s' % (s, moved, F.penetration(h, body)))
        c = h
    else:
        NECKZ = F.bone_head(arm, 'neck').z; HIPZ = F.bone_head(arm, 'Hips').z
        ws = F.world_verts(body)
        band = [w for w in ws if NECKZ - 0.25 < w.z < NECKZ - 0.17 and abs(w.x) < 0.09]
        ys = [w.y for w in band]; cd = max(ys) - min(ys); cy = (max(ys) + min(ys)) / 2
        c = F.import_piece(SPEC['src'], SPEC['name']); print('MERGED', merge_splits(c))
        lo, hi = F.bounds(c); s = cd / ((hi - lo).y * SPEC['fac'])
        c.scale = (s, s, s); F.apply(c); lo, hi = F.bounds(c)
        c.location = (-(lo.x + hi.x) / 2, cy - (lo.y + hi.y) / 2, NECKZ - hi.z); F.apply(c)
        if SPEC['cut']:
            bm = bmesh.new(); bm.from_mesh(c.data)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, HIPZ + SPEC['cut']),
                                   plane_no=(0, 0, 1), clear_inner=True)
            bm.to_mesh(c.data); bm.free(); c.data.update()
        if PIECE == 'vest': hem_cut(c)
        tp = torso_proxy(body)
        print('SNUG flank verts moved', snug_flanks(c, tp, arm))
        n0 = F.penetration(c, tp); moved = F.push_out_smooth(c, tp, offset=0.007, radius=0.07)
        if PIECE == 'vest': print('PLATE smoothed (full)', smooth_plates(c))
        print('FIT %s scale %.4f pen before %s moved %d after %s' % (PIECE, s, n0, moved, F.penetration(c, tp)))
    bpy.ops.object.select_all(action='DESELECT'); c.select_set(True); bpy.context.view_layer.objects.active = c
    bpy.ops.wm.obj_export(filepath=HERE + f'work/{PIECE}_fit.obj', export_selected_objects=True, export_uv=True,
                          export_normals=False, export_materials=False, export_triangulated_mesh=True,
                          forward_axis='Y', up_axis='Z', apply_modifiers=False)
    print('TRIS', sum(len(p.vertices) - 2 for p in c.data.polygons))

def pad_weights(c, arm, share=0.4):
    """Loose parts whose centre sits outboard of a shoulder joint and above the armpit (the shoulder pad) get
    `share` of that side's upper-arm bone so the pad rides the deltoid instead of the arm swinging out under it."""
    bm = bmesh.new(); bm.from_mesh(c.data); bm.verts.ensure_lookup_table()
    seen = set(); done = 0
    for side, sb, ab in ((1, 'LeftShoulder', 'LeftArm'), (-1, 'RightShoulder', 'RightArm')):
        jx = F.bone_head(arm, ab)
        for v in bm.verts:
            if v.index in seen: continue
            stack = [v]; isl = []; seen.add(v.index)
            while stack:
                x = stack.pop(); isl.append(x.index)
                for e in x.link_edges:
                    y = e.other_vert(x)
                    if y.index not in seen: seen.add(y.index); stack.append(y)
            cen = sum((bm.verts[i].co for i in isl), Vector()) / len(isl)
            if side * cen.x > side * jx.x - 0.03 and cen.z > jx.z - 0.06 and len(isl) > 30:
                gs = c.vertex_groups.get(sb) or c.vertex_groups.new(name=sb)
                ga = c.vertex_groups.get(ab) or c.vertex_groups.new(name=ab)
                for g in list(c.vertex_groups):
                    g.remove(isl)
                gs.add(isl, 1 - share, 'REPLACE'); ga.add(isl, share, 'REPLACE'); done += len(isl)
        seen = set()
    bm.free(); return done

def fade_shoulders(c, arm, band=0.05):
    """Clavicle weights only on the shoulder straps: below the armpits the idle clip's clavicle swing threw the
    side panels out as wings. Weight of Left/RightShoulder fades to zero from (arm joint z - 0.03) down over `band`,
    the rest renormalised onto the spine bones."""
    ztop = min(F.bone_head(arm, 'LeftArm').z, F.bone_head(arm, 'RightArm').z) - 0.03
    sh = {c.vertex_groups[n].index for n in ('LeftShoulder', 'RightShoulder') if c.vertex_groups.get(n)}
    names = {g.index: g.name for g in c.vertex_groups}; n = 0
    for v in c.data.vertices:
        z = (c.matrix_world @ v.co).z
        f = max(0.0, min(1.0, (z - (ztop - band)) / band)); f = f * f * (3 - 2 * f)
        if f >= 1: continue
        ws = {g.group: g.weight for g in v.groups}
        if not any(k in sh and w > 0 for k, w in ws.items()): continue
        new = {k: (w * f if k in sh else w) for k, w in ws.items()}
        tot = sum(new.values())
        if tot < 1e-6: new = {c.vertex_groups['Spine'].index: 1.0}; tot = 1.0
        for k in ws: c.vertex_groups[k].remove([v.index])
        for k, w in new.items():
            if w / tot > 1e-4: c.vertex_groups[k].add([v.index], w / tot, 'REPLACE')
        n += 1
    return n

def skin(objname):
    arm, body = load_body()
    src = F.import_piece(SPEC['src'], '_src')    # only for its material
    mat = src.data.materials[0]
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=HERE + f'work/{objname}.obj', forward_axis='Y', up_axis='Z')
    c = next(o for o in bpy.data.objects if o not in before)
    bpy.data.objects.remove(src)
    c.name = SPEC['name']; c.data.name = SPEC['name']
    c.data.materials.clear(); c.data.materials.append(mat)
    print('MERGED', merge_splits(c))
    if PIECE == 'vest': print('PLATE smoothed', smooth_plates(c))
    bpy.ops.object.select_all(action='DESELECT'); c.select_set(True); bpy.context.view_layer.objects.active = c
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50))
    for m in list(c.modifiers):    # bake the smooth-by-angle result into the mesh data
        bpy.ops.object.modifier_apply(modifier=m.name)
    F.clear_groups(c)
    if PIECE == 'helmet':
        F.skin_rigid(c, 'Head'); print('UNWEIGHTED', F.ensure_weighted(c, 'Head'))
    else:
        F.skin_transfer(c, body, bones=TORSO); print('UNWEIGHTED', F.ensure_weighted(c, 'Spine'))
        print('SHOULDER fade', fade_shoulders(c, arm))
        if PIECE == 'vest':
            pad = pad_set(c, arm); print('PAD cap', pad_cap(c, arm, pad), 'mask texels', pad_mask(c, pad))
    F.bind(c, arm)
    F.export_skinned([c], arm, HERE + 'out/' + SPEC['file'], ratio=1.0)
    bpy.ops.wm.save_as_mainfile(filepath=HERE + f'work/{PIECE}_skinned.blend')

if STAGE == 'fit': fit()
elif STAGE == 'skin': skin(f'{PIECE}_dec')
elif STAGE == 'full': skin(f'{PIECE}_fit')
