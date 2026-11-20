"""Hero base armour re-fit (20 Nov 2026): shared Blender helpers.

Adapted copies of art/tutorial_set_20261002/blender/fitlib.py and art/colonist_back_20261120/blender/cblib.py, re-pointed
at the NEW player body (art/hero_base_20261120/build/hero.blend: mesh `char1` on armature `Armature`, 54 bones, Meshy
A-pose rest). Blender 5.2 headless through the shared slot only:
    ~/.local/state/ward-programme/showcase-phase2-20261120/blender.sh <script.py> -- <args>
Coordinates: Z up, the hero faces -Y, his left is +X; metres, soles at z = 0, 1.88 m tall in the file."""
import bpy, bmesh, json, math, os
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

AO2 = Path('/home/teknetik/code/ao2')
HERO = AO2 / 'art/hero_base_20261120/build/hero.blend'
HERO_GLB = AO2 / 'art/hero_base_20261120/build/out/colonist.glb'
HERE = AO2 / 'art/hero_base_20261120/armour'
WORK = HERE / 'work'; OUTD = HERE / 'out'; REND = HERE / 'renders'
MESHY = AO2 / 'meshy/tutorial-set-20261002'
# The pieces and body as SHIPPED for the old (MPFB) player = git HEAD 7b4f1889 (20 Nov back pass). The files in the Unity
# project were overwritten on 20 Nov 11:14-11:18 by the hero integration (new body, texture-less stand-in armour), so
# the references are read from copies taken from git: armour/ref_shipped/ (sha256.txt) and the back pass's own output.
TS_OLD = HERE / 'ref_shipped'
OLD_BODY = AO2 / 'art/colonist_back_20261120/out/colonist.glb'
CARRIER_SRC = AO2 / 'unity/AthenHill/Assets/AthenHill/Art/Armour/WardenPlateCarrier.glb'
FILES = {'helmet': 'TS_Helmet.glb', 'vest': 'TS_FieldVest.glb', 'carrier': 'TS_WardenCarrier.glb', 'arms': 'TS_ArmGuards.glb',
         'gloves': 'TS_Gloves.glb', 'legs': 'TS_LegArmour.glb', 'boots': 'TS_Boots.glb'}
TORSO = ['Hips', 'Spine02', 'Spine01', 'Spine', 'neck', 'LeftShoulder', 'RightShoulder']
for d in (WORK, OUTD, REND): d.mkdir(parents=True, exist_ok=True)


def log(*a): print('ARMOUR', *a, flush=True)


def import_glb(path, merge=False):
    """glTF import; the importer's bone-shape helper meshes (Icosphere) are removed."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=merge)
    new = [o for o in bpy.data.objects if o not in before]
    for o in list(new):
        if o.type == 'MESH' and o.name.startswith('Icosphere'): new.remove(o); bpy.data.objects.remove(o, do_unlink=True)
    return new


def rest(arm):
    """Rest pose, no action, NLA muted."""
    if arm.animation_data:
        arm.animation_data.action = None
        for t in arm.animation_data.nla_tracks: t.mute = True
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def load_hero():
    """The finished new body: armature `Armature` + mesh `char1`, in the rest pose with its clips muted."""
    bpy.ops.wm.open_mainfile(filepath=str(HERO))
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['char1']
    rest(arm)
    return arm, body


def bone_head(arm, name): return arm.matrix_world @ arm.data.bones[name].head_local
def bone_tail(arm, name): return arm.matrix_world @ arm.data.bones[name].tail_local
def world_verts(o): return [o.matrix_world @ v.co for v in o.data.vertices]
def tris(o): return sum(len(p.vertices) - 2 for p in o.data.polygons)


def bounds(o):
    ws = world_verts(o)
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])


def import_piece(path, name):
    """A Meshy source piece as one object, transforms applied, centred on the origin (as fitlib.import_piece)."""
    objs = import_glb(path)
    meshes = [o for o in objs if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    p = bpy.context.view_layer.objects.active
    mw = p.matrix_world.copy(); p.parent = None; p.matrix_world = mw
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in objs:
        if o.name in bpy.data.objects and o != p and o.type != 'MESH': bpy.data.objects.remove(o)
    p.name = name; p.data.name = name
    lo, hi = bounds(p); c = (lo + hi) / 2
    p.data.transform(Matrix.Translation(-c)); p.location = (0, 0, 0)
    return p


def apply(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def merge_splits(o, dist=1e-5):
    """Weld the vertices the glTF import split at every UV seam (UVs stay per loop), so decimation and smoothing
    treat the shell as one surface."""
    bm = bmesh.new(); bm.from_mesh(o.data)
    n0 = len(bm.verts); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    n1 = len(bm.verts); bm.to_mesh(o.data); bm.free(); o.data.update(); return n0 - n1


def body_bvh(body):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world)
    bm.normal_update()
    return BVHTree.FromBMesh(bm), bm


def signed_dist(piece, body, max_dist=0.3):
    """Per piece vertex: signed distance to the body's nearest surface point (negative = inside)."""
    bvh, bm = body_bvh(body); out = []
    for w in world_verts(piece):
        hit = bvh.find_nearest(w, max_dist)
        out.append(None if hit[0] is None else (w - hit[0]).dot(hit[1]))
    bm.free(); return out


def penetration(piece, body, tol=0.0):
    """(count of piece vertices inside the body, deepest signed distance): fitlib.penetration."""
    n = 0; worst = 0.0
    for s in signed_dist(piece, body, 0.1):
        if s is not None and s < tol: n += 1; worst = min(worst, s)
    return n, worst


def gap_stats(piece, body):
    ds = sorted(s for s in signed_dist(piece, body) if s is not None)
    if not ds: return {}
    q = lambda f: round(ds[min(len(ds) - 1, int(f * len(ds)))] * 1000, 1)
    return {'min_mm': round(ds[0] * 1000, 1), 'p01_mm': q(.01), 'p05_mm': q(.05), 'p25_mm': q(.25), 'p50_mm': q(.5),
            'p75_mm': q(.75), 'p95_mm': q(.95), 'max_mm': round(ds[-1] * 1000, 1),
            'inside': sum(1 for d in ds if d < 0), 'verts': len(ds)}


def push_out_smooth(piece, body, offset=0.007, radius=0.07, iters=8, gain=1.6, max_dist=0.12, sel=None):
    """Smooth penetration fix for thin shells (fitlib.push_out_smooth): each pass moves every vertex by a
    Gaussian-weighted average of the required outward moves around it, so the shell inflates as a smooth surface
    instead of creasing. `sel`: optional set of vertex indices allowed to request a move."""
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); total = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = [None] * len(ws); n = 0
        for i, w in enumerate(ws):
            if sel is not None and i not in sel: continue
            hit = bvh.find_nearest(w, max_dist)
            if hit[0] is None: continue
            side = (w - hit[0]).dot(hit[1])
            if side < offset: req[i] = hit[1] * (offset - side); n += 1
        bm.free()
        if n == 0: break
        total = n
        kd = KDTree(len(ws))
        for i, w in enumerate(ws): kd.insert(w, i)
        kd.balance()
        s2 = (radius / 2) ** 2
        for i, w in enumerate(ws):
            acc = Vector(); wt = 0.0
            for co, j, dist in kd.find_range(w, radius):
                g = math.exp(-dist * dist / (2 * s2)); wt += g
                if req[j] is not None: acc += req[j] * g
            if acc.length:
                d = acc / wt * gain
                if req[i] is not None and d.length < req[i].length: d = req[i]
                me.vertices[i].co = inv @ (w + d)
        me.update()
    return total


def push_out(piece, body, offset=0.006, max_dist=0.08, smooth=4):
    """fitlib.push_out: vertices inside the body (or closer than offset) go to surface + offset, the displacement is
    relaxed over neighbours so shells move as plates."""
    bvh, bm = body_bvh(body)
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted()
    disp = [Vector() for _ in me.vertices]; moved = 0
    for v in me.vertices:
        w = mw @ v.co
        hit = bvh.find_nearest(w, max_dist)
        if hit[0] is None: continue
        side = (w - hit[0]).dot(hit[1])
        if side < offset: disp[v.index] = hit[1] * (offset - side); moved += 1
    adj = [[] for _ in me.vertices]
    for e in me.edges: a, b = e.vertices; adj[a].append(b); adj[b].append(a)
    for _ in range(smooth):
        new = []
        for i, d in enumerate(disp):
            if not adj[i]: new.append(d); continue
            avg = sum((disp[j] for j in adj[i]), Vector()) / len(adj[i])
            new.append(d if d.length >= avg.length else avg)
        disp = new
    for v, d in zip(me.vertices, disp):
        if d.length: v.co = inv @ (mw @ v.co + d)
    bm.free(); me.update()
    return moved


def shrink_fit(piece, body, gap=0.022, k=0.9, radius=0.06, max_dist=0.25, iters=2, keep=None):
    """fitlib.shrink_fit: where the shell stands off more than `gap` it moves in by k*(standoff-gap) along the body
    normal, Gaussian-smoothed so folds and plates keep their relative shape. keep(world) -> True leaves a vertex."""
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); moved = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = [Vector()] * len(ws)
        for i, w in enumerate(ws):
            if keep is not None and keep(w): continue
            hit = bvh.find_nearest(w, max_dist)
            if hit[0] is None: continue
            side = (w - hit[0]).dot(hit[1])
            if side > gap: req[i] = -hit[1] * (side - gap) * k
        bm.free()
        kd = KDTree(len(ws))
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


def mirror_x(piece, name):
    c = piece.copy(); c.data = piece.data.copy(); c.name = name; c.data.name = name
    bpy.context.collection.objects.link(c)
    c.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    c.data.flip_normals(); c.data.update()
    return c


def clear_groups(o): o.vertex_groups.clear()


def skin_rigid(o, bone, verts=None):
    g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    g.add(verts if verts is not None else [v.index for v in o.data.vertices], 1.0, 'REPLACE')


def normalise(o, limit=4):
    for v in o.data.vertices:
        ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > 1e-4), reverse=True)
        keep = ws[:limit]; tot = sum(w for w, _ in keep)
        for g in list(v.groups): o.vertex_groups[g.group].remove([v.index])
        if tot <= 0: continue
        for w, gi in keep: o.vertex_groups[gi].add([v.index], w / tot, 'REPLACE')


def skin_transfer(o, body, bones=None):
    """Nearest-face-interpolated weights from the body, optionally restricted to a bone list (others dropped and
    renormalised): fitlib.skin_transfer."""
    for g in body.vertex_groups:
        if not o.vertex_groups.get(g.name): o.vertex_groups.new(name=g.name)
    m = o.modifiers.new('dt', 'DATA_TRANSFER'); m.object = body
    m.use_vert_data = True; m.data_types_verts = {'VGROUP_WEIGHTS'}; m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'; m.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    if bones is not None:
        for g in list(o.vertex_groups):
            if g.name not in bones: o.vertex_groups.remove(g)
    normalise(o)


def islands(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = set(); out = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; isl = []; seen.add(v.index)
        while stack:
            x = stack.pop(); isl.append(x.index)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); stack.append(y)
        out.append(isl)
    bm.free(); return out


def rigidify_islands(o):
    """Each loose part follows the single bone with the largest summed weight (metal plates do not bend)."""
    isls = islands(o)
    for isl in isls:
        tot = {}
        for i in isl:
            for g in o.data.vertices[i].groups: tot[g.group] = tot.get(g.group, 0) + g.weight
        if not tot: continue
        best = max(tot, key=tot.get)
        for gi in tot: o.vertex_groups[gi].remove(isl)
        o.vertex_groups[best].add(isl, 1.0, 'REPLACE')
    return len(isls)


def ensure_weighted(o, bone):
    """Vertices left without any weight follow `bone`; otherwise the glTF exporter binds them to an extra
    'neutral_bone' the player does not have."""
    g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    lone = [v.index for v in o.data.vertices if not any(x.weight > 1e-4 for x in v.groups)]
    if lone: g.add(lone, 1.0, 'REPLACE')
    return len(lone)


def bind(o, arm):
    mw = o.matrix_world.copy(); o.parent = arm; o.matrix_world = mw
    for m in list(o.modifiers):
        if m.type == 'ARMATURE': o.modifiers.remove(m)
    m = o.modifiers.new('Armature', 'ARMATURE'); m.object = arm


def smooth_shade(o, angle=50):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    for m in list(o.modifiers):
        if m.type != 'ARMATURE': bpy.ops.object.modifier_apply(modifier=m.name)


def export_skinned(o, arm, path):
    """One skinned mesh + the hero armature, rest pose, no animations: the skin gets the armature's 54 joints and
    inverse bind matrices exactly as build/out/colonist.glb (same armature object, same exporter settings)."""
    rest(arm); normalise(o)
    assert max(abs(x - 1) for x in arm.scale) < 1e-6 and arm.location.length < 1e-7
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB', export_skins=True,
                              export_animations=False, export_morph=False, export_apply=False,
                              export_image_format='AUTO', export_yup=True)
    log('EXPORT', o.name, 'tris', tris(o), 'verts', len(o.data.vertices), '->', path)


def export_obj(o, path):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True, export_uv=True, export_normals=False,
                          export_materials=False, export_triangulated_mesh=True, forward_axis='Y', up_axis='Z',
                          apply_modifiers=False)


def import_obj(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis='Y', up_axis='Z')
    c = next(o for o in bpy.data.objects if o not in before)
    c.name = name; c.data.name = name; return c


def old_material(key):
    """The piece's material with its textures exactly as in the CURRENT TS_*.glb (cleaned 20 Nov textures included)."""
    objs = import_glb(TS_OLD / FILES[key])
    mesh = next(o for o in objs if o.type == 'MESH'); mat = mesh.data.materials[0]; name = mesh.name; mat.use_fake_user = True
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
    return mat, name


# ---------------------------------------------------------------------------------------------------- review renders
def setup_render(res=(700, 900), samples=20):
    """CPU Cycles only (no GPU: the card is shared with the game)."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = int(os.environ.get('HB_SAMPLES', samples))
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 8; sc.cycles.max_bounces = 3
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.film_transparent = False
    try: sc.view_settings.view_transform = 'Standard'
    except Exception: pass
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.58, 0.62, 1); bg.inputs[1].default_value = 0.9
    for o in [o for o in bpy.data.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)
    for nm, rot, e in (('key', (55, 0, -35), 2.6), ('fill', (60, 0, 150), 1.4)):
        l = bpy.data.objects.new(nm, bpy.data.lights.new(nm, 'SUN')); l.data.energy = e; l.data.angle = math.radians(8)
        l.rotation_euler = [math.radians(a) for a in rot]; sc.collection.objects.link(l)
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    sc.camera = cam; cam.data.clip_start = 0.01
    return cam


DIRS = {'front': (0, -1, 0), 'back': (0, 1, 0), 'left': (1, 0, 0), 'right': (-1, 0, 0), 'q_fl': (0.7, -0.7, 0.15),
        'q_fr': (-0.7, -0.7, 0.15), 'q_bl': (0.7, 0.7, 0.2), 'q_br': (-0.7, 0.7, 0.2), 'top': (0, -0.25, 1),
        'under': (0, -0.4, -1), 'top_back': (0, 0.6, 0.8)}


def shot(cam, path, centre, size, view, lens=70, res=None):
    """Frame a box of `size` metres (height) around `centre` from a named direction and render it."""
    sc = bpy.context.scene
    if res: sc.render.resolution_x, sc.render.resolution_y = res
    cam.data.lens = lens; cam.data.sensor_fit = 'VERTICAL'; cam.data.sensor_height = 24
    d = Vector(DIRS[view] if isinstance(view, str) else view).normalized()
    dist = size / 2 / math.tan(math.atan(12 / lens)) * 1.08
    cam.location = Vector(centre) + d * dist
    cam.rotation_euler = (Vector(centre) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    return str(path)


def sheet(paths, out, cols=None, label=True):
    """Contact sheet with numpy (no PIL in Blender): tiles the PNGs left to right, top to bottom, as a JPEG."""
    import numpy as np
    ims = []
    for p in paths:
        im = bpy.data.images.load(str(p)); w, h = im.size
        a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a); ims.append(a.reshape(h, w, 4)); bpy.data.images.remove(im)
    cols = cols or len(ims); rows = (len(ims) + cols - 1) // cols
    h = max(i.shape[0] for i in ims); w = max(i.shape[1] for i in ims)
    canvas = np.ones((rows * h, cols * w, 4), np.float32) * 0.2; canvas[..., 3] = 1
    for k, i in enumerate(ims):
        r, c = divmod(k, cols); y0 = (rows - 1 - r) * h
        canvas[y0:y0 + i.shape[0], c * w:c * w + i.shape[1]] = i
    out_im = bpy.data.images.new('sheet', cols * w, rows * h); out_im.pixels.foreach_set(canvas.ravel())
    st = bpy.context.scene.render.image_settings; fmt, q = st.file_format, st.quality
    st.file_format = 'JPEG'; st.quality = 88
    out_im.save_render(str(out)); st.file_format = fmt; st.quality = q; bpy.data.images.remove(out_im)
    return str(out)


# ------------------------------------------------------------------------------------------- surface-following fit
def vert_normals_world(o):
    n3 = o.matrix_world.to_3x3()
    return [(n3 @ v.normal).normalized() for v in o.data.vertices]


def conform(piece, body, lo=0.005, hi=0.012, radius=0.04, iters=6, k=0.85, max_dist=0.2, sel=None, facing=-0.2,
            hard=0.002, bvh=None, log_tag=None, pull=True, weight=None):
    """Smooth surface-following fit (port of fitlib.shrink_fit + push_out_smooth in one field).
    Vertices of the piece's INNER wall (normal towards the body) that stand off more than `hi` ask to move in by
    k*(standoff-hi); any vertex closer than `lo` (or inside the body) asks to move out to `lo`; inner-wall vertices
    already between lo and hi ask to stay. The requests are averaged on a grid of control points (cell = radius/2) and
    every vertex moves by the Gaussian-weighted mean of the control points around it, so plates, straps and both walls
    of a shell move together instead of wrinkling. Finally any vertex still closer than `hard` gets its own move.
    sel: optional set of vertex indices that may move (others stay and do not vote). weight: optional per-vertex
    0..1 list; a vertex moves by weight x field and votes only above 0.5 (soft edge of a region). Returns stats."""
    import numpy as np
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted()
    own = bvh is None
    if own: bvh, bmb = body_bvh(body)
    n = len(me.vertices); idx = list(range(n)) if sel is None else sorted(sel)
    if weight is not None: idx = [i for i in idx if weight[i] > 1e-4]
    stats = {}
    for it in range(iters):
        me.update(); nrm = vert_normals_world(piece)
        ws = [mw @ me.vertices[i].co for i in idx]
        pts = []; reqs = []; own_req = {}
        nin = nout = 0
        for a, i in enumerate(idx):
            w = ws[a]; hit = bvh.find_nearest(w, max_dist)
            if hit[0] is None: continue
            if weight is not None and weight[i] < 0.5: continue
            side = (w - hit[0]).dot(hit[1])
            if side < lo:
                r = hit[1] * (lo - side); pts.append(w); reqs.append(r); nout += 1
                if side < hard: own_req[a] = hit[1] * (hard - side)
            elif nrm[i].dot(hit[1]) < facing:
                if side > hi and pull: pts.append(w); reqs.append(-hit[1] * (side - hi) * k); nin += 1
                else: pts.append(w); reqs.append(Vector())
        if it == 0: stats['first'] = (nout, nin)
        if not pts or (nout == 0 and nin == 0): break
        P = np.array(pts, np.float32); R = np.array(reqs, np.float32)
        cell = radius / 2.0; key = np.floor(P / cell).astype(np.int64)
        uniq, invk, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        invk = invk.ravel()
        C = np.zeros((len(uniq), 3), np.float32); D = np.zeros((len(uniq), 3), np.float32)
        np.add.at(C, invk, P); np.add.at(D, invk, R); C /= cnt[:, None]; D /= cnt[:, None]
        W = np.array(ws, np.float32); out = np.zeros_like(W); s2 = 2 * (radius / 2.0) ** 2
        for c0 in range(0, len(W), 4000):
            d2 = ((W[c0:c0 + 4000, None, :] - C[None, :, :]) ** 2).sum(-1)
            g = np.exp(-d2 / s2) * cnt[None, :]
            tot = g.sum(1); tot[tot < 1e-12] = 1e-12
            out[c0:c0 + 4000] = (g @ D) / tot[:, None]
            far = d2.min(1) > (radius * 1.5) ** 2                  # no control point near: follow the nearest one
            if far.any(): out[c0:c0 + 4000][far] = D[d2[far].argmin(1)]
        for a, i in enumerate(idx):
            d = Vector(out[a].tolist())
            if weight is not None: d *= weight[i]
            if d.length > 1e-6: me.vertices[i].co = inv @ (ws[a] + d)
        stats['last'] = (nout, nin)
    # hard guarantee: nothing closer than `hard`
    me.update(); fixed = 0
    for i in idx:
        w = mw @ me.vertices[i].co; hit = bvh.find_nearest(w, max_dist)
        if hit[0] is None: continue
        side = (w - hit[0]).dot(hit[1])
        if side < hard: me.vertices[i].co = inv @ (w + hit[1] * (hard - side)); fixed += 1
    me.update(); stats['hard_fixed'] = fixed
    if own: bmb.free()
    if log_tag: log('CONFORM', log_tag, stats)
    return stats


def relax_normal(o, sel, iters=4, factor=0.5):
    """Laplacian smoothing along the vertex normal only (keeps texture from sliding): takes out the small dents a
    push leaves in flat plate."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    vs = [bm.verts[i] for i in sel if not bm.verts[i].is_boundary]
    for _ in range(iters):
        bm.normal_update(); moves = []
        for v in vs:
            if not v.link_edges: moves.append(Vector()); continue
            avg = sum((e.other_vert(v).co for e in v.link_edges), Vector()) / len(v.link_edges)
            moves.append(v.normal * (avg - v.co).dot(v.normal) * factor)
        for v, d in zip(vs, moves): v.co += d
    bm.to_mesh(o.data); bm.free(); o.data.update(); return len(vs)


# ---------------------------------------------------------------------------------------------------------- poses
def eval_world_verts(o):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); me = ev.to_mesh()
    ws = [o.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return ws


def eval_bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for w in eval_world_verts(o):
            for i in range(3): lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi


def rot_world(arm, bone, axis, deg):
    """Rotate a pose bone about a WORLD axis through its head (on top of its current pose)."""
    pb = arm.pose.bones[bone]; bpy.context.view_layer.update()
    m = arm.matrix_world @ pb.matrix; head = m.translation.copy()
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis)) @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ (R @ m); bpy.context.view_layer.update()


def aim_bone(arm, bone, target):
    """Swing a pose bone (shortest rotation about its head) so it points along a WORLD direction."""
    pb = arm.pose.bones[bone]; bpy.context.view_layer.update()
    m = arm.matrix_world @ pb.matrix; head = m.translation.copy()
    cur = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
    q = cur.rotation_difference(Vector(target).normalized())
    R = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ (R @ m); bpy.context.view_layer.update()


def curl(arm, deg01, deg02, deg03, thumb=0.4, sides='lr'):
    for s in sides:
        for d in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            for j, a in (('01', deg01), ('02', deg02), ('03', deg03)):
                pb = arm.pose.bones[f'{d}_{j}_{s}']; pb.rotation_mode = 'XYZ'
                pb.rotation_euler = (math.radians(a * (thumb if d == 'thumb' else 1.0)), 0, 0)
    bpy.context.view_layer.update()


def floor_body(arm, body):
    z = min(w.z for w in eval_world_verts(body))
    pb = arm.pose.bones['Hips']; m = arm.matrix_world @ pb.matrix; m.translation.z -= z
    pb.matrix = arm.matrix_world.inverted() @ m; bpy.context.view_layer.update()


MESHY_FINGER = {f'{d}_0{j}_{s}': f'{"Left" if s == "l" else "Right"}Hand{d.capitalize()}{j}'
                for d in ('thumb', 'index', 'middle', 'ring', 'pinky') for j in (1, 2, 3) for s in 'lr'}


def clip_pose(arm, name, pct):
    """Pose the hero from one of the clips Meshy made on this rig (art/hero_base_20261120/rig/<name>.glb) at pct % of
    its length. Each bone takes the clip bone's world pose times its own rest offset, so re-rolled fingers follow."""
    objs = import_glb(AO2 / 'art/hero_base_20261120/rig' / f'{name}.glb')
    src = next(o for o in objs if o.type == 'ARMATURE')
    act = src.animation_data.action; f0, f1 = act.frame_range
    bpy.context.scene.frame_set(int(round(f0 + (f1 - f0) * pct / 100.0))); bpy.context.view_layer.update()
    rows = {}
    for b in arm.data.bones:
        sn = b.name if b.name in src.pose.bones else MESHY_FINGER.get(b.name)
        if sn not in src.pose.bones: continue
        rows[b.name] = (src.matrix_world @ src.pose.bones[sn].matrix) @ (src.matrix_world @ src.data.bones[sn].matrix_local).inverted()
    for o in objs: bpy.data.objects.remove(o, do_unlink=True)
    rest(arm); rinv = arm.matrix_world.inverted()
    def walk(b):
        if b.name in rows:
            arm.pose.bones[b.name].matrix = rinv @ (rows[b.name] @ (arm.matrix_world @ b.matrix_local)); bpy.context.view_layer.update()
        for c in b.children: walk(c)
    for b in arm.data.bones:
        if b.parent is None: walk(b)


def set_pose(arm, body, spec):
    """rest | idle:P | walk:P | run:P (the actions in hero.blend at P % of the clip) | clip:<name>:P (rig/<name>.glb) |
    rifle (both arms raised forward to shoulder height, elbows bent, hands closed) | kneel (deep knee bend) |
    fist | armsup."""
    rest(arm); kind, _, fr = spec.partition(':')
    if kind in ('idle', 'walk', 'run'):
        act = next(a for a in bpy.data.actions if a.name.lower().startswith(kind))
        ad = arm.animation_data or arm.animation_data_create(); ad.action = act
        try:
            if act.slots: ad.action_slot = act.slots[0]
        except Exception: pass
        f0, f1 = act.frame_range
        bpy.context.scene.frame_set(int(round(f0 + (f1 - f0) * float(fr or 0) / 100.0)))
    elif kind == 'clip':
        nm, _, p = fr.partition(':'); clip_pose(arm, nm, float(p or 50))
    elif kind == 'rifle':
        # his right is -X, forward is -Y. Shooting arm: upper arm forward and down, forearm up and across to the grip;
        # support arm: reaching forward under the handguard.
        rot_world(arm, 'RightShoulder', (0, 0, 1), -8); rot_world(arm, 'LeftShoulder', (0, 0, 1), 10)
        aim_bone(arm, 'RightArm', (-0.25, -0.80, -0.55)); aim_bone(arm, 'RightForeArm', (0.62, -0.70, 0.36))
        aim_bone(arm, 'LeftArm', (0.10, -0.92, -0.38)); aim_bone(arm, 'LeftForeArm', (-0.45, -0.85, 0.28))
        curl(arm, 50, 60, 35)
    elif kind == 'kneel':
        for s, sx in (('Left', 1), ('Right', -1)):
            foot_rest = arm.matrix_world @ arm.data.bones[s + 'Foot'].matrix_local
            aim_bone(arm, s + 'UpLeg', (sx * 0.28, -0.90, -0.33)); aim_bone(arm, s + 'Leg', (sx * 0.05, 0.50, -0.86))
            pb = arm.pose.bones[s + 'Foot']; bpy.context.view_layer.update()
            m = foot_rest.copy(); m.translation = (arm.matrix_world @ pb.matrix).translation
            pb.matrix = arm.matrix_world.inverted() @ m; bpy.context.view_layer.update()
        rot_world(arm, 'Spine02', (1, 0, 0), 18)
        floor_body(arm, body)
    elif kind == 'fist':
        curl(arm, 60, 75, 45)
    elif kind == 'neutral':
        # The shoulders as the game always has them: the rest pose is Meshy's A-pose, but every clip holds the
        # collarbones about 20 degrees off it and the arms down. Rest pose plus the idle clip's local rotations of
        # the collarbones, upper arms and forearms; the spine stays upright.
        act = next(a for a in bpy.data.actions if a.name.lower().startswith('idle'))
        ad = arm.animation_data or arm.animation_data_create(); ad.action = act
        try:
            if act.slots: ad.action_slot = act.slots[0]
        except Exception: pass
        bpy.context.scene.frame_set(int(act.frame_range[0])); bpy.context.view_layer.update()
        NB = [s_ + b for s_ in ('Left', 'Right') for b in ('Shoulder', 'Arm', 'ForeArm')]
        keep = {n: arm.pose.bones[n].matrix_basis.copy() for n in NB}
        rest(arm)
        for n in NB: arm.pose.bones[n].matrix_basis = keep[n]
    elif kind in ('tpose', 'tfist'):                                 # arms straight out: hands clear of the body
        for S, sx in (('Left', 1), ('Right', -1)):
            aim_bone(arm, S + 'Arm', (sx, 0, 0)); aim_bone(arm, S + 'ForeArm', (sx, 0, 0)); aim_bone(arm, S + 'Hand', (sx, 0, 0))
        if kind == 'tfist': curl(arm, 60, 75, 45)
    elif kind == 'armsup':
        aim_bone(arm, 'RightArm', (-0.75, 0, 0.66)); aim_bone(arm, 'LeftArm', (0.75, 0, 0.66))
    bpy.context.view_layer.update()


def posed_copy(body, name='body_posed'):
    """The body frozen in its current pose as a plain mesh (same vertex order and vertex groups, no armature)."""
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.matrix_world = body.matrix_world.copy()
    for g in body.vertex_groups: o.vertex_groups.new(name=g.name)
    o.hide_render = True; return o


def pose_mats(arm):
    """Per bone: the matrix that carries a rest-pose point to the current pose (armature space)."""
    return {b.name: arm.pose.bones[b.name].matrix @ b.matrix_local.inverted() for b in arm.data.bones}


def pose_head(arm, name): return arm.matrix_world @ arm.pose.bones[name].head


def unpose(o, mats):
    """Inverse linear-blend skinning: the object's vertices are where they should be in the pose described by `mats`;
    move each back to the rest position that its own weights carry to that place."""
    names = {g.index: g.name for g in o.vertex_groups}; mw = o.matrix_world; inv = mw.inverted(); worst = 0.0
    for v in o.data.vertices:
        acc = Matrix(((0, 0, 0, 0),) * 4); tot = 0.0
        for g in v.groups:
            if g.weight > 0: acc = acc + mats[names[g.group]] * g.weight; tot += g.weight
        if tot <= 0: continue
        acc = acc * (1.0 / tot); p = mw @ v.co; r = acc.inverted() @ p
        worst = max(worst, (r - p).length); v.co = inv @ r
    o.data.update(); return worst


def smooth_weights(o, iters=3, factor=0.5):
    """Laplacian smoothing of the skin weights over the mesh (garment weights transferred from a body are noisy
    where the nearest skin point jumps)."""
    n = len(o.data.vertices); adj = [[] for _ in range(n)]
    for e in o.data.edges: a, b = e.vertices; adj[a].append(b); adj[b].append(a)
    W = [{g.group: g.weight for g in v.groups} for v in o.data.vertices]
    for _ in range(iters):
        new = []
        for i in range(n):
            if not adj[i]: new.append(W[i]); continue
            acc = {k: w * (1 - factor) for k, w in W[i].items()}; f = factor / len(adj[i])
            for j in adj[i]:
                for k, w in W[j].items(): acc[k] = acc.get(k, 0.0) + w * f
            new.append(acc)
        W = new
    for g in o.vertex_groups: g.remove(list(range(n)))
    for i, ws in enumerate(W):
        for k, w in ws.items():
            if w > 1e-4: o.vertex_groups[k].add([i], w, 'REPLACE')
    normalise(o)


def load_pieces(arm, keys, src_dir=None, files=None):
    """Import exported armour GLBs and bind them to `arm` (their own armature copies are dropped)."""
    got = {}
    for k in keys:
        path = (files or {}).get(k) or Path(src_dir or OUTD) / FILES[k]
        po = import_glb(path)
        for o in po:
            if o.type == 'MESH':
                for m in o.modifiers:
                    if m.type == 'ARMATURE': m.object = arm
                mw = o.matrix_world.copy(); o.parent = arm; o.matrix_world = mw; got[k] = o
        for o in po:
            if o.type == 'ARMATURE': bpy.data.objects.remove(o, do_unlink=True)
    return got


def posed_penetration(piece, body, deep=0.003):
    """In the current pose: piece vertices inside the deformed body (count, count deeper than `deep`, worst mm)."""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world); bm.normal_update(); bvh = BVHTree.FromBMesh(bm)
    n = nd = 0; worst = 0.0
    for w in eval_world_verts(piece):
        hit = bvh.find_nearest(w, 0.1)
        if hit[0] is None: continue
        side = (w - hit[0]).dot(hit[1])
        if side < 0: n += 1; worst = min(worst, side)
        if side < -deep: nd += 1
    bm.free(); return {'inside': n, 'deeper_3mm': nd, 'worst_mm': round(worst * 1000, 1)}


# ------------------------------------------------------------------------------------- radial fit (helmet on a head)
def radial_fit(piece, body, c0, clear=0.004, liner=0.002, radius=0.05, iters=8, gain=1.5, reach=0.03, log_tag=None):
    """Fit a double-walled shell round a blob (helmet on head + sculpted hair), working along rays from `c0` (a point
    in the middle of the head). OUTER-wall vertices must clear the body's outermost surface on their ray by `clear`;
    where they do not, the need is spread with a Gaussian of `radius`, so the whole shell (both walls) swells smoothly
    there instead of denting. Then the INNER wall (padding, hidden by the outer wall) is moved out to `liner` off the
    body, but never through the outer wall. Returns stats."""
    import numpy as np
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); c0 = Vector(c0)
    bvh_b, bmb = body_bvh(body)

    def body_r(d, limit):
        """Outermost body crossing on the ray from c0 along d, no farther than `limit`."""
        o = c0.copy(); r = None; travelled = 0.0
        for _ in range(8):
            hit = bvh_b.ray_cast(o, d, limit - travelled)
            if hit[0] is None: break
            travelled += (hit[0] - o).length; r = travelled; o = hit[0] + d * 1e-4; travelled += 1e-4
            if travelled >= limit: break
        return r

    def piece_state():
        bm = bmesh.new(); bm.from_mesh(me); bm.transform(mw); bvh_p = BVHTree.FromBMesh(bm)
        ws = [mw @ v.co for v in me.vertices]; dirs = []; rv = []; rout = []
        for w in ws:
            d = w - c0; r = d.length; d = d / r if r > 1e-9 else Vector((0, 0, 1))
            hit = bvh_p.ray_cast(c0 + d * (r + 1.0), -d, r + 1.0)
            dirs.append(d); rv.append(r); rout.append((hit[0] - c0).length if hit[0] is not None else r)
        bm.free(); return ws, dirs, rv, rout

    stats = {}
    for it in range(iters):
        ws, dirs, rv, rout = piece_state()
        pts = []; req = []; need_max = 0.0; nneed = 0
        for w, d, r, ro in zip(ws, dirs, rv, rout):
            if r < ro - 0.001: continue                               # not the outer wall on this ray
            rb = body_r(d, r + reach)
            if rb is None: continue
            need = rb + clear - r
            pts.append(w); req.append(max(need, 0.0))
            if need > 0: nneed += 1; need_max = max(need_max, need)
        if it == 0: stats['outer_need_first'] = (nneed, round(need_max * 1000, 1))
        stats['outer_need_last'] = (nneed, round(need_max * 1000, 1))
        if nneed == 0: break
        P = np.array(pts, np.float32); R = np.array(req, np.float32)
        W = np.array(ws, np.float32); out = np.zeros(len(W), np.float32); s2 = 2 * (radius / 2.0) ** 2
        for c in range(0, len(W), 2000):
            d2 = ((W[c:c + 2000, None, :] - P[None, :, :]) ** 2).sum(-1); g = np.exp(-d2 / s2)
            tot = g.sum(1); tot[tot < 1e-9] = 1e-9
            # a blend of the weighted mean (smooth) and the weighted max (so the worst spot is actually cleared)
            out[c:c + 2000] = np.maximum((g @ R) / tot * gain, (g * R[None, :]).max(1) * 0.6)
        for i, (w, d) in enumerate(zip(ws, dirs)):
            if out[i] > 1e-6: me.vertices[i].co = inv @ (w + d * float(out[i]))
        me.update()
    # inner wall: out to `liner` off the body, never through the outer wall
    ws, dirs, rv, rout = piece_state(); moved = 0; capped = 0
    for i, (w, d, r, ro) in enumerate(zip(ws, dirs, rv, rout)):
        if r >= ro - 0.001: continue
        rb = body_r(d, ro)
        if rb is None or r >= rb + liner: continue
        tgt = rb + liner
        if tgt > ro - 0.001: tgt = max(r, ro - 0.001); capped += 1
        if tgt > r: me.vertices[i].co = inv @ (c0 + d * tgt); moved += 1
    me.update(); bmb.free()
    stats['liner_moved'] = moved; stats['liner_capped_under_shell'] = capped
    if log_tag: log('RADIAL', log_tag, stats)
    return stats


def outer_clearance(piece, body, c0, reach=0.03):
    """Check for radial_fit: outer-wall vertices of the piece vs the body on rays from c0 -> (count below 0, below
    2 mm, worst mm)."""
    me = piece.data; mw = piece.matrix_world; c0 = Vector(c0); bvh_b, bmb = body_bvh(body)
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(mw); bvh_p = BVHTree.FromBMesh(bm)
    neg = lt2 = 0; worst = 1.0
    for v in me.vertices:
        w = mw @ v.co; d = w - c0; r = d.length; d = d / r
        hit = bvh_p.ray_cast(c0 + d * (r + 1.0), -d, r + 1.0)
        if hit[0] is not None and r < (hit[0] - c0).length - 0.001: continue
        o = c0.copy(); rb = None; tr = 0.0
        for _ in range(8):
            h = bvh_b.ray_cast(o, d, r + reach - tr)
            if h[0] is None: break
            tr += (h[0] - o).length; rb = tr; o = h[0] + d * 1e-4; tr += 1e-4
        if rb is None: continue
        cl = r - rb; worst = min(worst, cl)
        if cl < 0: neg += 1
        if cl < 0.002: lt2 += 1
    bm.free(); bmb.free(); return {'through': neg, 'under_2mm': lt2, 'worst_mm': round(worst * 1000, 1)}
