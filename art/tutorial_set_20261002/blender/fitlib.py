"""Tutorial set (2 Oct 2026): shared Blender helpers to fit armour pieces to the main_char_OK rig and export them as
skinned GLBs on the same 24-bone armature. Blender 5.2 headless (run through ward-programme/blender.sh).
Coordinates: Blender Z up, the colonist faces -Y, his left is +X; metres, soles at z = 0."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

AO2 = Path('/home/teknetik/code/ao2')
RIG = AO2 / 'meshy/main-char-20261002/rigged.glb'
MESHY = AO2 / 'meshy/tutorial-set-20261002'
OUT = AO2 / 'art/tutorial_set_20261002/blender'

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o not in before]

def load_body():
    objs = import_glb(RIG)
    for o in objs:
        if o.type == 'MESH' and o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm)
    return arm, body

def bone_head(arm, name): return arm.matrix_world @ arm.data.bones[name].head_local
def bone_tail(arm, name): return arm.matrix_world @ arm.data.bones[name].tail_local

def world_verts(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]

def bounds(o):
    ws = world_verts(o)
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])

def import_piece(path, name):
    objs = import_glb(path)
    meshes = [o for o in objs if o.type == 'MESH']
    for o in objs:
        if o.type != 'MESH': o.select_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    p = bpy.context.view_layer.objects.active
    p.parent = None
    p.matrix_world = p.matrix_world.copy()
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

def body_bvh(body):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new(); bm.from_object(body, dg); bm.transform(body.matrix_world)
    bm.normal_update()
    return BVHTree.FromBMesh(bm), bm

def push_out(piece, body, offset=0.006, max_dist=0.08, smooth=4, verts_filter=None):
    """Moves piece vertices that sit inside the body (or closer than offset) to the body surface + offset, then
    relaxes the displacement over neighbours so plates stay smooth. Returns moved vertex count."""
    bvh, bm = body_bvh(body)
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted()
    disp = [Vector() for _ in me.vertices]; moved = 0
    for v in me.vertices:
        if verts_filter and not verts_filter(v): continue
        w = mw @ v.co
        hit = bvh.find_nearest(w, max_dist)
        if hit[0] is None: continue
        loc, nrm, idx, dist = hit
        side = (w - loc).dot(nrm)
        if side < offset:
            disp[v.index] = nrm * (offset - side); moved += 1
    # relax: spread displacement to neighbours (max of own vs neighbour average) so shells move as plates
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

def penetration(piece, body, tol=0.0):
    bvh, bm = body_bvh(body); n = 0; worst = 0
    for w in world_verts(piece):
        hit = bvh.find_nearest(w, 0.1)
        if hit[0] is None: continue
        side = (w - hit[0]).dot(hit[1])
        if side < tol: n += 1; worst = min(worst, side)
    bm.free(); return n, worst

def mirror_x(piece, name):
    c = piece.copy(); c.data = piece.data.copy(); c.name = name; c.data.name = name
    bpy.context.collection.objects.link(c)
    c.data.transform(Matrix.Scale(-1, 4, (1, 0, 0)))
    c.data.flip_normals(); c.data.update()
    return c

def clear_groups(o):
    o.vertex_groups.clear()

def skin_rigid(o, bone, verts=None):
    g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    g.add(verts if verts is not None else [v.index for v in o.data.vertices], 1.0, 'REPLACE')

def skin_transfer(o, body, bones=None, smooth_iter=0):
    """Nearest-face-interpolated weights from the body, optionally restricted to a bone list (others dropped and
    renormalised)."""
    for g in body.vertex_groups:
        if not o.vertex_groups.get(g.name): o.vertex_groups.new(name=g.name)
    m = o.modifiers.new('dt', 'DATA_TRANSFER'); m.object = body
    m.use_vert_data = True; m.data_types_verts = {'VGROUP_WEIGHTS'}; m.vert_mapping = 'POLYINTERP_NEAREST'
    m.layers_vgroup_select_src = 'ALL'; m.layers_vgroup_select_dst = 'NAME'
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=m.name)
    if bones is not None:
        for g in list(o.vertex_groups):
            if g.name not in bones: o.vertex_groups.remove(g)
    normalise(o)

def normalise(o, limit=4):
    names = {g.index: g.name for g in o.vertex_groups}
    for v in o.data.vertices:
        ws = sorted(((g.weight, g.group) for g in v.groups if g.weight > 1e-4), reverse=True)
        keep = ws[:limit]; tot = sum(w for w, _ in keep)
        for g in list(v.groups):
            o.vertex_groups[g.group].remove([v.index])
        if tot <= 0: continue
        for w, gi in keep: o.vertex_groups[gi].add([v.index], w / tot, 'REPLACE')

def rigidify_islands(o, min_share=0.0):
    """Each loose part follows the single bone with the largest summed weight (metal plates do not bend)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen = set(); islands = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; isl = []; seen.add(v.index)
        while stack:
            x = stack.pop(); isl.append(x.index)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); stack.append(y)
        islands.append(isl)
    bm.free()
    gname = {g.index: g.name for g in o.vertex_groups}
    for isl in islands:
        tot = {}
        for i in isl:
            for g in o.data.vertices[i].groups: tot[g.group] = tot.get(g.group, 0) + g.weight
        if not tot: continue
        best = max(tot, key=tot.get)
        for gi in tot: o.vertex_groups[gi].remove(isl)
        o.vertex_groups[best].add(isl, 1.0, 'REPLACE')
    return len(islands)

def bind(o, arm):
    o.parent = arm; o.matrix_parent_inverse = arm.matrix_world.inverted()
    m = o.modifiers.new('Armature', 'ARMATURE'); m.object = arm

DECIMATE = 0.4   # runtime armour (3 Oct 2026): the full-detail Meshy pieces cost ~2.3 ms skinned at the gate view
def decimate(o, ratio):
    if ratio >= 0.999: return
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    m = o.modifiers.new('runtime_decimate', 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = ratio; m.use_collapse_triangulate = True
    bpy.ops.object.modifier_move_to_index(modifier=m.name, index=0)
    bpy.ops.object.modifier_apply(modifier=m.name)

def export_skinned(objs, arm, path, ratio=None):
    for o in objs:
        tris0 = sum(len(p.vertices) - 2 for p in o.data.polygons)
        decimate(o, DECIMATE if ratio is None else ratio); normalise(o)
        print('EXPORT', o.name, 'tris', tris0, '->', sum(len(p.vertices) - 2 for p in o.data.polygons))
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB', export_skins=True,
                              export_animations=False, export_morph=False, export_apply=False,
                              export_image_format='AUTO', export_yup=True)

def setup_render(res=(700, 1000)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = False
    w = bpy.data.worlds.get('W') or bpy.data.worlds.new('W'); sc.world = w
    w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.32, 0.32, 0.34, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.9
    if not bpy.data.objects.get('key'):
        for nm, rot, e in (('key', (50, 0, -35), 3.5), ('fill', (60, 0, 150), 1.5)):
            l = bpy.data.objects.new(nm, bpy.data.lights.new(nm, 'SUN')); l.data.energy = e
            l.rotation_euler = [math.radians(a) for a in rot]; bpy.context.collection.objects.link(l)
    cam = bpy.data.objects.get('cam') or bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    if cam.name not in bpy.context.collection.objects: bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam

def render_views(path_prefix, centre, size, views=('front', 'side', 'back', 'quarter'), lens=60, res=(700, 1000)):
    cam = setup_render(res); cam.data.lens = lens
    dirs = {'front': Vector((0, -1, 0)), 'back': Vector((0, 1, 0)), 'side': Vector((1, 0, 0)), 'rside': Vector((-1, 0, 0)),
            'quarter': Vector((0.7, -0.7, 0.15)).normalized(), 'rquarter': Vector((-0.7, -0.7, 0.15)).normalized(),
            'top': Vector((0, -0.2, 1)).normalized()}
    out = []
    fov = 2 * math.atan(18 / lens)
    for v in views:
        d = dirs[v]; dist = size / 2 / math.tan(fov / 2) * 1.15
        cam.location = Vector(centre) + d * dist
        cam.rotation_euler = (Vector(centre) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.scene.render.filepath = f'{path_prefix}_{v}.png'
        bpy.ops.render.render(write_still=True); out.append(f'{path_prefix}_{v}.png')
    return out

def push_out_field(piece, body, offset=0.007, radius=0.05, max_dist=0.12, iters=3):
    """Penetration fix that keeps double-walled shells intact: each vertex's required outward move is spread to every
    vertex within `radius` (linear falloff, weighted max), so inner and outer walls and nearby straps move together."""
    from mathutils.kdtree import KDTree
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); total = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = {}
        for i, w in enumerate(ws):
            hit = bvh.find_nearest(w, max_dist)
            if hit[0] is None: continue
            side = (w - hit[0]).dot(hit[1])
            if side < offset: req[i] = hit[1] * (offset - side)
        bm.free()
        if not req: break
        total += len(req)
        kd = KDTree(len(req)); keys = list(req)
        for k, i in enumerate(keys): kd.insert(ws[i], k)
        kd.balance()
        for i, w in enumerate(ws):
            best = None; bl = 0
            for co, k, dist in kd.find_range(w, radius):
                d = req[keys[k]] * min(1.0, 2 * (1 - dist / radius))
                if d.length > bl: bl = d.length; best = d
            if best is not None: me.vertices[i].co = inv @ (w + best)
        me.update()
    return total

def strip_inner(piece, body, near=0.035):
    """Deletes the inward-facing liner of a hollow garment shell: faces whose normal points towards the body and that
    sit inside it or within `near` of its surface. The body fills the garment, so the liner is never visible, and
    removing it lets the outer shell be pushed out without the liner crossing through it."""
    bvh, bmb = body_bvh(body)
    bm = bmesh.new(); bm.from_mesh(piece.data); bm.faces.ensure_lookup_table()
    mw = piece.matrix_world; n3 = mw.to_3x3()
    kill = []
    for f in bm.faces:
        c = mw @ f.calc_center_median(); nrm = (n3 @ f.normal).normalized()
        hit = bvh.find_nearest(c, near + 0.05)
        if hit[0] is None: continue
        side = (c - hit[0]).dot(hit[1])
        if side < near and nrm.dot(hit[1]) < -0.2: kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]; bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(piece.data); bm.free(); bmb.free(); piece.data.update()
    return len(kill)

def push_out_smooth(piece, body, offset=0.007, radius=0.07, iters=8, gain=1.6, max_dist=0.12):
    """Smooth penetration fix for thin shells: each pass moves every vertex by a Gaussian-weighted average of the
    required outward moves around it (zeros included), so the shell inflates as a smooth surface instead of creasing
    where neighbouring vertices need different moves. Repeats until (almost) nothing penetrates."""
    from mathutils.kdtree import KDTree
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); total = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = [None] * len(ws); n = 0
        for i, w in enumerate(ws):
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

def eval_verts(o):
    """World-space vertices with shape keys and modifiers applied (MPFB targets live in shape keys)."""
    dg = bpy.context.evaluated_depsgraph_get(); e = o.evaluated_get(dg); me = e.to_mesh()
    ws = [o.matrix_world @ v.co for v in me.vertices]; e.to_mesh_clear(); return ws

def eval_bounds(o):
    ws = eval_verts(o)
    return Vector([min(w[i] for w in ws) for i in range(3)]), Vector([max(w[i] for w in ws) for i in range(3)])

def push_out_smooth(piece, body, offset=0.007, radius=0.07, iters=8, gain=1.6, max_dist=0.12):
    """Smooth penetration fix for thin shells: each pass moves every vertex by a Gaussian-weighted average of the
    required outward moves around it (zeros included), so the shell inflates as a smooth surface instead of creasing
    where neighbouring vertices need different moves. Repeats until (almost) nothing penetrates."""
    from mathutils.kdtree import KDTree
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); total = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = [None] * len(ws); n = 0
        for i, w in enumerate(ws):
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

def hide_covered(body, cover, reach=0.06, keep_groups=()):
    """Deletes body faces whose vertices are all covered by `cover`: a ray along the vertex normal hits the cover within
    `reach`. Vertices weighted to keep_groups are never deleted."""
    dg = bpy.context.evaluated_depsgraph_get()
    bmc = bmesh.new(); bmc.from_object(cover, dg); bmc.transform(cover.matrix_world)
    bvh = BVHTree.FromBMesh(bmc)
    me = body.data; mw = body.matrix_world; n3 = mw.to_3x3()
    keep_idx = {body.vertex_groups[g].index for g in keep_groups if g in body.vertex_groups}
    covered = set()
    for v in me.vertices:
        if any(g.group in keep_idx and g.weight > 0.3 for g in v.groups): continue
        w = mw @ v.co; nrm = (n3 @ v.normal).normalized()
        hit = bvh.ray_cast(w + nrm * 0.0005, nrm, reach)
        if hit[0] is not None: covered.add(v.index)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    kill = [f for f in bm.faces if all(v.index in covered for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); bmc.free(); me.update()
    return len(kill)

def hide_near(body, cover, near=0.03, drop_groups=(), keep_groups=()):
    """Deletes body faces whose vertices all lie inside `cover` or within `near` of it, plus faces whose vertices are
    all dominated by drop_groups (e.g. feet inside boots). keep_groups vertices are never removed."""
    dg = bpy.context.evaluated_depsgraph_get()
    bmc = bmesh.new(); bmc.from_object(cover, dg); bmc.transform(cover.matrix_world); bmc.normal_update()
    bvh = BVHTree.FromBMesh(bmc)
    me = body.data; mw = body.matrix_world
    gidx = {g.index: g.name for g in body.vertex_groups}
    gone = set()
    for v in me.vertices:
        ws = {gidx[g.group]: g.weight for g in v.groups}
        if any(ws.get(k, 0) > 0.3 for k in keep_groups): continue
        if ws and max(ws, key=ws.get) in drop_groups: gone.add(v.index); continue
        w = mw @ v.co; hit = bvh.find_nearest(w, near + 0.2)
        if hit[0] is None: continue
        side = (w - hit[0]).dot(hit[1])
        if side < near: gone.add(v.index)
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    kill = [f for f in bm.faces if all(v.index in gone for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); bmc.free(); me.update()
    return len(kill)

def shrink_fit(piece, body, gap=0.022, k=0.9, radius=0.06, max_dist=0.25, iters=2, z_max=None):
    """Snugs a baggy garment towards the body: where the shell stands off more than `gap`, it moves inwards by
    k*(standoff-gap) along the body normal, smoothed with a Gaussian field so folds keep their relative shape.
    Vertices above z_max (e.g. a collar) are left alone."""
    from mathutils.kdtree import KDTree
    me = piece.data; mw = piece.matrix_world; inv = mw.inverted(); moved = 0
    for it in range(iters):
        bvh, bm = body_bvh(body)
        ws = [mw @ v.co for v in me.vertices]
        req = [Vector()] * len(ws)
        for i, w in enumerate(ws):
            if z_max is not None and w.z > z_max: continue
            hit = bvh.find_nearest(w, max_dist)
            if hit[0] is None: continue
            side = (w - hit[0]).dot(hit[1])
            if side > gap: req[i] = -hit[1] * (side - gap) * k
        bm.free()
        kd = KDTree(len(ws))
        for i, w in enumerate(ws): kd.insert(w, i)
        kd.balance(); s2 = (radius / 2) ** 2
        new = []
        for i, w in enumerate(ws):
            acc = Vector(); wt = 0.0
            for co, j, dist in kd.find_range(w, radius):
                g = math.exp(-dist * dist / (2 * s2)); acc += req[j] * g; wt += g
            new.append(w + (acc / wt if wt else Vector()))
        for i, p in enumerate(new):
            if (p - ws[i]).length > 1e-5: moved += 1
            me.vertices[i].co = inv @ p
        me.update()
    return moved

BODY_TAG = 'm0.25'
def load_final(tag=None):
    """The finished MPFB player (finish_body.py): armature 'Armature' + joined skinned mesh 'char1', clips muted."""
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'mpfb' / f'final_{tag or BODY_TAG}.blend'))
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['char1']
    if arm.animation_data:
        arm.animation_data.action = None
        for t in arm.animation_data.nla_tracks: t.mute = True
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return arm, body

def ensure_weighted(o, bone):
    """Vertices left without any weight (loose straps far from the body) follow `bone`; otherwise the glTF exporter
    binds them to an extra 'neutral_bone' the player does not have."""
    g = o.vertex_groups.get(bone) or o.vertex_groups.new(name=bone)
    lone = [v.index for v in o.data.vertices if not any(x.weight > 1e-4 for x in v.groups)]
    if lone: g.add(lone, 1.0, 'REPLACE')
    return len(lone)
