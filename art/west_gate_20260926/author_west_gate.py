"""West Gate / Warden outpost authored structures (26 Sep 2026), Blender 5.2 headless.

Run:  blender -b --python-exit-code 1 -P author_west_gate.py [-- AssetName ...]

Coordinates are written in Unity metres (X east, Y up, Z north) and converted by U();
the glTF export (+Y up) and glTFast import map Blender (x, y, z) to Unity (-x, z, -y).
UVs are box-projected in metres (1 UV unit = 1 m), so Unity material tiling = 1 / texture size.
Sign faces use 0..1 UVs. Materials are named WG_* and rebuilt as URP Lit in Unity.
Objects named COL_* are collision proxies (renderer disabled in Unity); LIGHT_* and MOUNT_*
empties mark practical-light and prop positions. Every asset writes <Name>.glb and a JSON record.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix, Euler, noise

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Structures"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = {}


# ---------------------------------------------------------------- basics
def U(x, y, z):
    return Vector((-x, -z, y))


MATS = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        MATS[name] = m
    return MATS[name]


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_obj(name, bm, material):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if material:
        for m in (material if isinstance(material, (list, tuple)) else [material]):
            me.materials.append(mat(m))
    return ob


def box_uv(ob, offset=None, scale=1.0):
    """Metre box projection in object space (after transforms are applied)."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    off = offset if offset is not None else Vector((random.random() * 7, random.random() * 7))
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = (co.y if n.x > 0 else -co.y), co.z
            elif ax == 1:
                u, v = (-co.x if n.y > 0 else co.x), co.z
            else:
                u, v = co.x, (co.y if n.z > 0 else -co.y)
            uv[li].uv = ((u * scale) + off.x, (v * scale) + off.y)


def finish(ob, bevel=0.0, segs=2, uv=True, smooth_angle=35):
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel > 0:
        m = ob.modifiers.new("bev", "BEVEL"); m.width = bevel; m.segments = segs; m.limit_method = "ANGLE"
        m.angle_limit = math.radians(40); m.harden_normals = True; m.miter_outer = "MITER_ARC"
        bpy.ops.object.modifier_apply(modifier="bev")
    if uv:
        box_uv(ob)
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(smooth_angle))
    except Exception:
        for p in ob.data.polygons:
            p.use_smooth = False
    return ob


C_UB = Matrix(((-1, 0, 0), (0, 0, -1), (0, 1, 0)))  # Unity -> Blender (a reflection)


def urot(rx=0, ry=0, rz=0):
    """Unity Quaternion.Euler(rx, ry, rz) as a 3x3 matrix in Unity coordinates (Z, then X, then Y)."""
    return Matrix.Rotation(math.radians(ry), 3, "Y") @ Matrix.Rotation(math.radians(rx), 3, "X") @ Matrix.Rotation(math.radians(rz), 3, "Z")


def to_blender(bm):
    for v in bm.verts:
        v.co = U(*v.co)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def box(name, center, size, material, bevel=0.01, rot=(0, 0, 0), segs=2):
    """center/size in Unity metres (size = X width, Y height, Z depth); rot = Unity euler degrees."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    R = urot(*rot); c = Vector(center)
    for v in bm.verts:
        v.co = R @ Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + c
    to_blender(bm)
    ob = mesh_obj(name, bm, material)
    finish(ob, bevel, segs)
    return ob


def hinge(objs, pivot, yaw):
    """Rotate finished objects about a vertical Unity axis through pivot by a Unity yaw (degrees)."""
    M = (C_UB @ urot(0, yaw, 0) @ C_UB.inverted()).to_4x4()
    P = U(*pivot)
    T = Matrix.Translation(P) @ M @ Matrix.Translation(-P)
    for ob in (objs if isinstance(objs, (list, tuple)) else [objs]):
        ob.data.transform(T @ ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        ob.data.update()


def cyl(name, a, b, r, material, sides=16, bevel=0.0, cap=True):
    a, b = U(*a), U(*b); d = b - a; L = d.length
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=sides, radius1=r, radius2=r, depth=L)
    ob = mesh_obj(name, bm, material)
    ob.location = (a + b) / 2
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    finish(ob, bevel, 1, smooth_angle=50)
    return ob


def tube(name, pts, r, material, sides=10):
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = max(1, sides // 4 - 1)
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts):
        v = U(*q); p.co = (v.x, v.y, v.z, 1)
    ob = link(bpy.data.objects.new(name, cu))
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects: o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob = bpy.context.view_layer.objects.active
    ob.data.materials.clear(); ob.data.materials.append(mat(material))
    finish(ob, 0, uv=True, smooth_angle=60)
    return ob


def sag(a, b, drop, n=10):
    return [tuple(Vector(a).lerp(Vector(b), t) - Vector((0, drop * 4 * t * (1 - t), 0))) for t in [i / n for i in range(n + 1)]]


def quad(name, center, w, h, material, facing=(0, 0, -1), up=(0, 1, 0), uv_rect=(0, 0, 1, 1), double=False):
    """Sign face: w x h in metres, front normal = facing (Unity), UV 0..1."""
    f = Vector(facing).normalized(); upv = Vector(up).normalized(); right = upv.cross(f).normalized()
    c = Vector(center)
    corners = [c - right * w / 2 - upv * h / 2, c + right * w / 2 - upv * h / 2, c + right * w / 2 + upv * h / 2, c - right * w / 2 + upv * h / 2]
    bm = bmesh.new(); vs = [bm.verts.new(U(*p)) for p in corners]
    face = bm.faces.new(vs)
    # Unity mirror flips winding; normal must end up along facing after import
    bm.normal_update()
    want = U(*(c + f)) - U(*c)
    if face.normal.dot(want) < 0:
        face.normal_flip()
    uvl = bm.loops.layers.uv.new("UVMap")
    u0, v0, u1, v1 = uv_rect
    order = [(u1, v0), (u0, v0), (u0, v1), (u1, v1)]  # U mirrored: the Unity import flips X
    for loop in face.loops:
        i = vs.index(loop.vert); loop[uvl].uv = order[i]
    if double:
        bmesh.ops.duplicate(bm, geom=[face])
    ob = mesh_obj(name, bm, material)
    return ob


def empty(name, pos, rot=(0, 0, 0)):
    e = link(bpy.data.objects.new(name, None)); e.location = U(*pos)
    e.rotation_euler = Euler((math.radians(-rot[0]), math.radians(-rot[2]), math.radians(-rot[1])), "YXZ")
    return e


def join(name, objs):
    objs = [o for o in objs if o and o.type == "MESH"]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = name; ob.data.name = name
    return ob


def decimate_copy(ob, ratio, name):
    c = ob.copy(); c.data = ob.data.copy(); link(c); c.name = name
    m = c.modifiers.new("dec", "DECIMATE"); m.ratio = ratio
    bpy.context.view_layer.objects.active = c
    for o in bpy.context.selected_objects: o.select_set(False)
    c.select_set(True)
    bpy.ops.object.modifier_apply(modifier="dec")
    return c


def export(name, note=""):
    objs = [o for o in bpy.context.scene.objects]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_apply=True, export_extras=False)
    tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs if o.type == "MESH")
    mats = sorted({m.name for o in objs if o.type == "MESH" for m in o.data.materials if m})
    REPORT[name] = {"triangles": tri, "objects": len(objs), "materials": mats, "note": note}
    print("exported", name, tri, "tris", mats, flush=True)


# ---------------------------------------------------------------- shared parts
def ibeam(name, a, b, h, w, tw, tf, material, up=(0, 1, 0)):
    """I-beam between Unity points a->b; h depth along 'up', w flange width."""
    a, b = Vector(a), Vector(b); d = (b - a); L = d.length; dn = d.normalized(); upv = Vector(up).normalized()
    side = dn.cross(upv).normalized(); upv = side.cross(dn).normalized()
    parts = []
    for off, size in [(upv * (h / 2 - tf / 2), (w, tf)), (-upv * (h / 2 - tf / 2), (w, tf)), (Vector(), (tw, h - 2 * tf))]:
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        # local axes: X=length, Y=side, Z=up
        m = Matrix.Identity(4)
        bmesh.ops.scale(bm, vec=(L, size[0], size[1]), verts=bm.verts)
        basis = Matrix((U(*dn) - U(0, 0, 0), U(*side) - U(0, 0, 0), U(*upv) - U(0, 0, 0))).transposed()
        bmesh.ops.transform(bm, matrix=basis.to_4x4(), verts=bm.verts)
        bmesh.ops.translate(bm, vec=U(*((a + b) / 2 + off)), verts=bm.verts)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ob = mesh_obj(name, bm, material); finish(ob, 0.004, 1); parts.append(ob)
    return join(name, parts)


def bolt_row(name, start, step, count, r, material, facing):
    objs = []
    f = Vector(facing)
    for i in range(count):
        p = Vector(start) + Vector(step) * i
        objs.append(cyl(name, tuple(p), tuple(p + f * 0.018), r, material, sides=8))
    return join(name, objs)


# ---------------------------------------------------------------- sandbags
def sandbag(seed, L=.5, W=.33, H=.19):
    """Filled sandbag: superellipsoid pillow (boxy in plan, plump in section), settled flat bottom,
    folded flap at one end, lumpy fill. Local X = length, Y = width, Z = up (Blender local)."""
    rnd = random.Random(seed)
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
    flap = 1 if rnd.random() < .5 else -1
    for v in bm.verts:
        d = v.co.normalized()
        # superellipsoid radius along direction d: |x|^p + |y|^p + |z|^q = 1
        p, q = 5.0, 2.4
        f = (abs(d.x) ** p + abs(d.y) ** p + abs(d.z) ** q) ** (-1 / 1.0)
        # solve r: (r|dx|)^p + (r|dy|)^p + (r|dz|)^q = 1 by bisection
        lo, hi = 0.0, 2.0
        for _ in range(22):
            m = (lo + hi) / 2
            if (m * abs(d.x)) ** p + (m * abs(d.y)) ** p + (m * abs(d.z)) ** q > 1: hi = m
            else: lo = m
        x, y, z = d * lo
        if z < -.35: z = -.35 - (z + .35) * .25              # settled flat bottom
        z -= .12 * (1 - x * x) * (1 - y * y) * (1 if z > 0 else 0)  # slight top sag
        if x * flap > .82:                                     # folded flap: thinner, tucked under
            k = (x * flap - .82) / .18; z = z * (1 - .55 * k) - .1 * k; y *= 1 - .08 * k
        n = noise.noise(Vector((x * 2.1 + seed * 3.7, y * 2.1, z * 2.1)))
        v.co = Vector((x * L / 2, y * W / 2 * (1 + .04 * n), z * H / 2 * (1 + .12 * n) + H * .13))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


BAG_CACHE = {}


def bag_bm(i):
    key = i % 6
    if key not in BAG_CACHE:
        BAG_CACHE[key] = sandbag(40 + key)
    return BAG_CACHE[key].copy()


def bag_wall(name, path, courses, rows_low=2, low_courses=4, seed=1, batter=.03, material="WG_Hessian", jitter=1.0):
    """path: Unity (x,z) polyline at ground level. Stretcher bond: 2 rows below low_courses, then 1,
    each course staggered half a bag and stepped back (batter) on the outer face."""
    rnd = random.Random(seed); bm_all = bmesh.new(); i = 0
    pts = [Vector((p[0], 0, p[1])) for p in path]
    segs = [(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
    total = sum((b - a).length for a, b in segs)
    step = .46
    for c in range(courses):
        rows = rows_low if c < low_courses else 1
        y = c * .112
        s = (step / 2 if c % 2 else 0) + .24
        while s < total - .2:
            acc = 0
            for a, b in segs:
                L = (b - a).length
                if s <= acc + L + 1e-6:
                    t = (s - acc) / L; p = a.lerp(b, t); d = (b - a).normalized(); break
                acc += L
            side = Vector((-d.z, 0, d.x))
            for r in range(rows):
                off = (r - (rows - 1) / 2) * .31 - (0 if rows > 1 else batter * (c - low_courses + 1))
                bm = bag_bm(i); i += 1
                yaw = math.atan2(d.z, d.x)
                R = Matrix.Rotation(rnd.uniform(-.05, .05) * jitter, 3, "X") @ Matrix.Rotation(rnd.uniform(-.035, .035) * jitter, 3, "Y")
                bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=R)
                # bag local X (length) must follow d: Blender local X maps to Unity -X, so rotate by the Unity yaw mirrored
                bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-yaw + math.pi + rnd.uniform(-.05, .05) * jitter, 3, "Z"))
                sc = rnd.uniform(.95, 1.05)
                bmesh.ops.scale(bm, vec=(sc, sc, rnd.uniform(.93, 1.07)), verts=bm.verts)
                pos = p + side * off + Vector((rnd.uniform(-.015, .015), y + rnd.uniform(-.008, .01), rnd.uniform(-.015, .015))) * jitter
                bmesh.ops.translate(bm, vec=U(pos.x, pos.y, pos.z), verts=bm.verts)
                tmp = bpy.data.meshes.new("tmp"); bm.to_mesh(tmp); bm.free(); bm_all.from_mesh(tmp); bpy.data.meshes.remove(tmp)
            s += step
    ob = mesh_obj(name, bm_all, material)
    box_uv(ob)
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def bag_pile(name, center, count, seed=3):
    rnd = random.Random(seed); bm_all = bmesh.new()
    layer = [(0, 0), (.6, .05), (-.55, .1), (.05, .36), (.62, .4), (-.5, .45)]
    k = 0
    for i in range(count):
        if i < len(layer): px, pz = layer[i]; y = 0
        else: px, pz = rnd.uniform(-.4, .4), rnd.uniform(0, .4); y = .12 + .1 * (i - len(layer))
        bm = bag_bm(i)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rnd.uniform(-.25, .25), 3, "X") @ Matrix.Rotation(rnd.uniform(-3.1, 3.1), 3, "Z"))
        bmesh.ops.translate(bm, vec=U(center[0] + px, y, center[1] + pz), verts=bm.verts)
        tmp = bpy.data.meshes.new("tmp"); bm.to_mesh(tmp); bm.free(); bm_all.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    ob = mesh_obj(name, bm_all, "WG_Hessian"); box_uv(ob)
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def with_lod(ob, ratios=(.3,)):
    base = ob.name; ob.name = ob.data.name = base + "_LOD0"
    for i, r in enumerate(ratios, 1):
        decimate_copy(ob, r, f"{base}_LOD{i}")


# ================================================================ assets
def sandbag_modules():
    reset()
    with_lod(bag_wall("WG_SandbagWall2mHigh", [(-1.0, 0), (1.0, 0)], 9, rows_low=2, low_courses=5, seed=11))
    export("WG_SandbagWall2mHigh", "2 m straight, 9 courses (~1.05 m), double thickness below 5")
    reset()
    with_lod(bag_wall("WG_SandbagWall2mLow", [(-1.0, 0), (1.0, 0)], 4, rows_low=2, low_courses=2, seed=12))
    export("WG_SandbagWall2mLow", "2 m straight, 4 courses (~0.5 m)")
    reset()
    arc = [(1.6 * math.cos(a), 1.6 * math.sin(a)) for a in [math.radians(d) for d in range(0, 91, 10)]]
    with_lod(bag_wall("WG_SandbagCurveHigh", arc, 9, rows_low=2, low_courses=5, seed=13))
    export("WG_SandbagCurveHigh", "quarter arc r=1.6 m, 9 courses")
    reset()
    with_lod(bag_pile("WG_SandbagPile", (0, 0), 9, 7))
    export("WG_SandbagPile", "loose pile, 9 bags")
    reset()
    with_lod(bag_wall("WG_SandbagRoofRow", [(-1.2, 0), (1.2, 0)], 2, rows_low=1, low_courses=0, seed=14, jitter=1.4))
    export("WG_SandbagRoofRow", "2.4 m, two courses for roof edges")


def gate_portal():
    """Origin: centre of the wall gap at paving level. Wall occupies x -1..1, gap z -3.5..3.5 (local)."""
    reset(); parts = []
    H = 5.0
    for s in (-1, 1):
        zc = s * 3.5  # wall end face
        zin = zc - s * .25; zout = zc + s * .45
        zmid = (zin + zout) / 2; zw = abs(zout - zin)
        # concrete pier core, proud of both wall faces
        parts.append(box("Pier core", (0, H / 2, zmid), (2.3, H, zw), "WG_Concrete", .03))
        # footing plinth
        parts.append(box("Pier footing", (0, .12, zmid), (2.7, .24, zw + .3), "WG_Concrete", .02))
        # steel corner angles on the four vertical edges
        for x in (-1.15, 1.15):
            for z in (zin, zout):
                parts.append(box("Corner angle", (x, H / 2, z), (.14, H - .1, .14), "WG_RustSteel", .006))
        # impact armour on gap face: riveted plate with hazard band
        face_z = zin - s * .03
        parts.append(box("Pier armour plate", (0, 2.7, face_z), (2.34, 3.4, .05), "WG_PlateSteel", .008))
        parts.append(box("Pier hazard band", (0, .75, face_z - s * .005), (2.36, 1.3, .05), "WG_Hazard", .008))
        parts.append(bolt_row("Armour bolts", (-1.05, .2, face_z - s * .03), (0, .35, 0), 13, .018, "WG_RustSteel", (0, 0, -s)))
        parts.append(bolt_row("Armour bolts", (1.05, .2, face_z - s * .03), (0, .35, 0), 13, .018, "WG_RustSteel", (0, 0, -s)))
        # wall-face armour strips (outer and inner)
        for x in (-1.16, 1.16):
            parts.append(box("Pier face plate", (x, 2.7, zmid), (.04, 3.4, zw - .1), "WG_PlateSteel", .006))
        # cap
        parts.append(box("Pier cap", (0, H + .06, zmid), (2.5, .12, zw + .12), "WG_RustSteel", .01))
        # conduit + junction box on the inner face of the north pier
        if s > 0:
            parts.append(tube("Conduit", [(1.2, .9, zmid + .1), (1.22, 4.6, zmid + .1), (1.22, 5.2, zmid - .3), (.7, 5.3, zmid - .3)], .03, "WG_RustSteel"))
            parts.append(tube("Conduit", [(1.2, .9, zmid - .08), (1.22, 4.6, zmid - .08), (1.22, 5.15, zmid - .5)], .022, "WG_Rubber"))
            empty("MOUNT_junction_box", (1.3, 1.1, zmid), (0, 90, 0))
    # gantry: twin I-beam girders spanning pier tops
    top = H + .12
    for x in (-.62, .62):
        parts.append(ibeam("Gantry girder", (x, top + .25, -4.1), (x, top + .25, 4.1), .5, .28, .02, .03, "WG_RustSteel"))
    for z in (-3.3, -1.65, 0, 1.65, 3.3):
        parts.append(box("Gantry cross member", (0, top + .1, z), (1.24, .16, .12), "WG_RustSteel", .004))
    parts.append(box("Gantry deck", (0, top + .52, 0), (1.5, .04, 8.2), "WG_PlateSteel", .004))
    # railings both sides
    for x in (-.74, .74):
        for z in [-4.0 + i * 1.0 for i in range(9)]:
            parts.append(cyl("Rail post", (x, top + .54, z), (x, top + 1.6, z), .025, "WG_OlivePaint", 10))
        parts.append(cyl("Top rail", (x, top + 1.6, -4.02), (x, top + 1.6, 4.02), .03, "WG_OlivePaint", 12))
        parts.append(cyl("Mid rail", (x, top + 1.08, -4.02), (x, top + 1.08, 4.02), .022, "WG_OlivePaint", 10))
        parts.append(box("Toe board", (x, top + .62, 0), (.02, .14, 8.0), "WG_OlivePaint", .003))
    # lintel fascia plates carrying the stencilled signs (concept: sign on the beam face)
    for x, facing, m in ((.8, (1, 0, 0), "WG_SignGateInner"), (-.8, (-1, 0, 0), "WG_SignGateOuter")):
        parts.append(box("Lintel fascia", (x, top + .08, 0), (.05, 1.12, 8.2), "WG_OlivePaint", .008))
        parts.append(box("Fascia top angle", (x, top + .62, 0), (.1, .06, 8.2), "WG_RustSteel", .004))
        parts.append(box("Fascia bottom angle", (x, top - .47, 0), (.1, .06, 8.2), "WG_RustSteel", .004))
        for z in (-3.95, -1.3, 1.3, 3.95):
            parts.append(box("Fascia stiffener", (x + facing[0] * .03, top + .08, z), (.03, 1.06, .1), "WG_RustSteel", .003))
        parts.append(box("Sign plate", (x + facing[0] * .035, top + .08, 0), (.02, 1.0, 4.4), "WG_OlivePaint", .004))
        quad("Gate sign", (x + facing[0] * .047, top + .08, 0), 4.3, 1.02, m, facing=facing)
        parts.append(bolt_row("Sign bolts", (x + facing[0] * .045, top + .56, -2.1), (0, 0, .7), 7, .014, "WG_RustSteel", facing))
        parts.append(bolt_row("Sign bolts", (x + facing[0] * .045, top - .4, -2.1), (0, 0, .7), 7, .014, "WG_RustSteel", facing))
        # knee braces between piers and lintel (both faces)
        for s_ in (-1, 1):
            zp = s_ * 3.25
            parts.append(box("Knee gusset", (x * .9, top - .75, s_ * 2.95), (.04, .55, .6), "WG_RustSteel", .004))
            parts.append(ibeam("Knee brace", (x * .9, 3.75, zp), (x * .9, top - .45, s_ * 2.35), .18, .12, .012, .015, "WG_RustSteel", up=(1, 0, 0)))
    # hazard bands wrap the pier bases on the wall faces as well
    for s_ in (-1, 1):
        zmid = s_ * 3.6
        for x in (-1.19, 1.19):
            parts.append(box("Pier hazard wrap", (x, .75, zmid), (.03, 1.3, .66), "WG_Hazard", .004))
    # beacon and floodlight mounts
    parts.append(cyl("Beacon base", (0, top + 1.6, 3.9), (0, top + 1.72, 3.9), .09, "WG_RustSteel", 12))
    parts.append(cyl("Beacon lens", (0, top + 1.72, 3.9), (0, top + 1.92, 3.9), .075, "WG_AmberLens", 16))
    empty("LIGHT_beacon", (0, top + 1.82, 3.9))
    for x, yaw in ((-.95, -90), (.95, 90)):
        for z in (-2.9, 2.9):
            empty(f"MOUNT_floodlight", (x, top + 1.62, z), (0, yaw, 0))
    # steel threshold plate with sliding-gate rail across the opening (flush with paving)
    parts.append(box("Threshold plate", (-.6, -.02, 0), (1.4, .05, 7.0), "WG_PlateSteel", .004))
    parts.append(box("Gate rail (threshold)", (-1.35, .005, 0), (.07, .03, 7.6), "WG_RustSteel", .002))
    # collision proxies
    for s in (-1, 1):
        zc = s * 3.5; zin = zc - s * .25; zout = zc + s * .45
        box(f"COL_Pier", (0, H / 2, (zin + zout) / 2), (2.34, H, abs(zout - zin)), "WG_Collider", 0)
    box("COL_Gantry", (0, top + .9, 0), (1.6, 1.8, 8.2), "WG_Collider", 0)
    export("WG_GatePortal", "steel-armoured concrete piers, walk-on gantry with signs, banners, beacon, threshold rail")


def sliding_gate():
    """Leaf parked open. Origin: leaf centre-line at ground, local Z along travel. 7.6 m x 3.3 m x .22 m."""
    reset()
    L, Hh, T = 7.6, 3.3, .22
    y0 = .16  # wheel height
    # frame
    for z in (-L / 2 + .1, L / 2 - .1):
        box("Leaf stile", (0, y0 + Hh / 2, z), (T, Hh, .2), "WG_RustSteel", .01)
    for y in (y0 + .1, y0 + Hh / 2, y0 + Hh - .1):
        box("Leaf rail", (0, y, 0), (T, .2, L), "WG_RustSteel", .01)
    # olive plate infill both faces, patched
    for x in (-.075, .075):
        box("Leaf plate", (x, y0 + Hh * .27, 0), (.012, Hh * .5 - .22, L - .4), "WG_OlivePaint", .003)
        box("Leaf plate", (x, y0 + Hh * .76, 0), (.012, Hh * .5 - .22, L - .4), "WG_OlivePaint", .003)
    rnd = random.Random(7)
    for i in range(7):
        x = rnd.choice((-.085, .085)); w = rnd.uniform(.35, .9); h = rnd.uniform(.3, .7)
        box("Weld patch", (x, y0 + rnd.uniform(.4, Hh - .5), rnd.uniform(-3.2, 3.2)), (.012, h, w), "WG_PlateSteel", .004)
    # diagonal braces (visible on inner face)
    for z0, z1 in ((-3.6, 0), (0, 3.6)):
        cyl("Leaf brace", (.12, y0 + .25, z0), (.12, y0 + Hh - .25, z1), .045, "WG_RustSteel", 8)
    # hazard band at the leading edge and bottom
    box("Leaf hazard edge", (0, y0 + Hh / 2, -L / 2 + .02), (T + .02, Hh, .06), "WG_Hazard", .005)
    box("Leaf hazard foot", (-.09, y0 + .45, 0), (.02, .5, L - .4), "WG_Hazard", .003)
    # vision slot with shutter
    box("Vision slot frame", (-.1, y0 + 1.55, -2.6), (.05, .22, .8), "WG_RustSteel", .004)
    box("Vision slot shutter", (-.13, y0 + 1.62, -2.6), (.02, .16, .76), "WG_OlivePaint", .003)
    # wheel bogies
    for z in (-2.9, 2.9):
        box("Bogie housing", (0, .2, z), (.3, .22, .6), "WG_RustSteel", .01)
        for dz in (-.18, .18):
            cyl("Bogie wheel", (-.06, .09, z + dz), (.06, .09, z + dz), .09, "WG_RustSteel", 16)
    # top guide rollers are part of the wall brackets (see GateGuide)
    box("COL_Leaf", (0, y0 + Hh / 2, 0), (T + .05, Hh, L), "WG_Collider", 0)
    export("WG_SlidingGate", "parked-open sliding gate leaf on bogies")
    # rail plinth + guide brackets as a separate asset (wall mounted, 16 m)
    reset()
    box("Rail plinth", (0, -.12, 4.0), (.5, .36, 16.4), "WG_Concrete", .02)
    box("Rail", (0, .075, 4.0), (.07, .05, 16.4), "WG_RustSteel", .003)
    for z in (-3.6, 12.0):
        box("Rail end stop", (0, .16, z), (.2, .22, .12), "WG_Hazard", .005)
    for z in (5.6, 9.0, 12.2):
        # bracket from wall top (x=+.41 local wall face) over the leaf, with twin rollers
        box("Guide bracket arm", (.2, 3.02, z), (.62, .1, .12), "WG_RustSteel", .005)
        box("Guide bracket plate", (.47, 2.8, z), (.04, .5, .3), "WG_RustSteel", .005)
        for x in (-.16, .16):
            cyl("Guide roller", (x, 3.12, z), (x, 3.4, z), .045, "WG_Rubber", 12)
    export("WG_GateRail", "rail on concrete plinth with wall-top guide brackets")


def corrugated_wall(name, length, height, material, openings=(), pitch=.278, depth=.036, sign=1):
    """Wall in local X (length) / Y (height), corrugation out along Z*sign. openings: (x0,x1,y0,y1)."""
    prof = []
    x = 0.0
    seg = [(.105, 0), (.034, 1), (.105, 1), (.034, 0)]
    while x < length + 1e-4:
        for w, d_end in seg:
            prof.append((x, None)); x += w
    xs = [0.0]; ds = [0.0]; x = 0.0
    while x < length - 1e-6:
        for w, d_end in seg:
            x = min(length, x + w); xs.append(x); ds.append(depth * d_end)
            if x >= length: break
    bm = bmesh.new()
    ys_all = sorted({0.0, height} | {o[2] for o in openings} | {o[3] for o in openings})
    for i in range(len(xs) - 1):
        xa, xb = xs[i], xs[i + 1]
        for j in range(len(ys_all) - 1):
            ya, yb = ys_all[j], ys_all[j + 1]
            cx = (xa + xb) / 2; cy = (ya + yb) / 2
            if any(o[0] <= cx <= o[1] and o[2] <= cy <= o[3] for o in openings):
                continue
            vs = [bm.verts.new((xa, ya, ds[i] * sign)), bm.verts.new((xb, ya, ds[i + 1] * sign)), bm.verts.new((xb, yb, ds[i + 1] * sign)), bm.verts.new((xa, yb, ds[i] * sign))]
            f = bm.faces.new(vs if sign > 0 else vs[::-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return bm


def place_bm(bm, origin_u, x_axis_u, y_axis_u, z_axis_u):
    """Map local (x,y,z) of a bmesh into Unity coordinates, then Blender. Faces are re-oriented so their
    normals point along the local +Z axis (the outward direction for walls)."""
    o = Vector(origin_u); X, Y, Z = Vector(x_axis_u), Vector(y_axis_u), Vector(z_axis_u)
    for v in bm.verts:
        p = o + X * v.co.x + Y * v.co.y + Z * v.co.z
        v.co = U(*p)
    out = U(*Z) - U(0, 0, 0)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(out) < 0:
            f.normal_flip()
    bm.normal_update()


def guard_post():
    """20 ft ISO container converted to a Warden post. Origin: container floor-level centre of the
    underside (bottom of the base frame). Local X = length (east +), Z = width (north +). North long
    side faces the lane: issue window + locker bay; east end: cargo doors (north leaf open)."""
    reset()
    L, W, Hc = 6.058, 2.438, 2.591
    x0, x1, z0, z1 = -L / 2, L / 2, -W / 2, W / 2
    # --- base frame / corner posts / top rails
    for z in (z0 + .08, z1 - .08):
        box("Bottom side rail", (0, .08, z), (L, .16, .16), "WG_OlivePaint", .01)
        box("Top side rail", (0, Hc - .05, z), (L, .1, .1), "WG_OlivePaint", .01)
    for x in (x0 + .08, x1 - .08):
        box("Bottom end rail", (x, .1, 0), (.16, .2, W), "WG_OlivePaint", .01)
        box("Top end rail", (x, Hc - .12, 0), (.16, .24, W), "WG_OlivePaint", .01)
    for x in (x0 + .075, x1 - .075):
        for z in (z0 + .075, z1 - .075):
            box("Corner post", (x, Hc / 2, z), (.15, Hc - .24, .15), "WG_OlivePaint", .012)
            for y in (.06, Hc - .06):
                box("Corner casting", (x, y, z), (.178, .118, .162), "WG_RustSteel", .01)
    # --- long walls (corrugated), north wall with issue window opening
    win = (3.35, 4.95, 1.05, 2.0)   # along length from west end, height
    for side, zz, openings in ((1, z1 - .03, [win]), (-1, z0 + .03, [])):
        bm = corrugated_wall("Side wall", L - .3, Hc - .26, "WG_OlivePaint", openings=[(o[0] - .15, o[1] - .15, o[2] - .16, o[3] - .16) for o in openings], sign=1)
        place_bm(bm, (x0 + .15, .16, zz), (1, 0, 0), (0, 1, 0), (0, 0, side))
        ob = mesh_obj("Side wall", bm, "WG_OlivePaint"); finish(ob, 0, uv=True, smooth_angle=30)
    # west end wall corrugated (vertical)
    bm = corrugated_wall("End wall", W - .3, Hc - .36, "WG_OlivePaint", sign=1)
    place_bm(bm, (x0 + .03, .2, z0 + .15), (0, 0, 1), (0, 1, 0), (-1, 0, 0))
    ob = mesh_obj("End wall", bm, "WG_OlivePaint"); finish(ob, 0, uv=True, smooth_angle=30)
    # roof (die-stamped shallow panels) and floor
    box("Roof sheet", (0, Hc - .02, 0), (L - .1, .03, W - .1), "WG_OlivePaint", .005)
    for i in range(1, 12):
        box("Roof stamp", (x0 + i * L / 12, Hc + .005, 0), (.26, .02, W - .3), "WG_OlivePaint", .008)
    box("Floor", (0, .19, 0), (L - .2, .03, W - .2), "WG_Plywood", .003)
    # interior lining (dark) so the open door/window read as depth
    box("Interior lining", (0, Hc / 2, z0 + .09), (L - .3, Hc - .4, .01), "WG_InteriorDark", 0)
    box("Interior lining", (0, Hc - .1, 0), (L - .3, .01, W - .3), "WG_InteriorDark", 0)
    box("Interior lining", (x0 + .09, Hc / 2, 0), (.01, Hc - .4, W - .3), "WG_InteriorDark", 0)
    box("Interior lining", (0, Hc / 2, z1 - .09), (L - .3, Hc - .4, .01), "WG_InteriorDark", 0)
    # --- issue window: frame, bars, counter shelf, awning shutter propped open
    wx0, wx1, wy0, wy1 = x0 + win[0], x0 + win[1], win[2], win[3]
    wc = (wx0 + wx1) / 2
    for x in (wx0, wx1):
        box("Window jamb", (x, (wy0 + wy1) / 2, z1 - .03), (.08, wy1 - wy0 + .08, .12), "WG_RustSteel", .006)
    for y in (wy0, wy1):
        box("Window sill", (wc, y, z1 - .03), (wx1 - wx0 + .08, .08, .12), "WG_RustSteel", .006)
    for i in range(1, 7):
        x = wx0 + i * (wx1 - wx0) / 7
        cyl("Window bar", (x, wy0, z1 - .05), (x, wy1, z1 - .05), .012, "WG_RustSteel", 8)
    box("Issue counter", (wc, wy0 - .02, z1 + .2), (wx1 - wx0 + .3, .05, .42), "WG_PlateSteel", .006)
    for x in (wx0 + .05, wx1 - .05):
        box("Counter bracket", (x, wy0 - .2, z1 + .12), (.04, .32, .24), "WG_RustSteel", .004)
    # awning shutter hinged at the top, propped ~55 deg
    ang = math.radians(55); sh_w, sh_h = wx1 - wx0 + .16, wy1 - wy0 + .12
    cy = wy1 + .06 - math.cos(ang) * sh_h / 2; cz = z1 + math.sin(ang) * sh_h / 2 + .01
    box("Window shutter", (wc, cy, cz), (sh_w, sh_h, .035), "WG_OlivePaint", .006, rot=(-55, 0, 0))
    for x in (wx0 + .1, wx1 - .1):
        cyl("Shutter strut", (x, wy0 + .1, z1 + .03), (x, wy1 + .06 - math.cos(ang) * sh_h * .95, z1 + math.sin(ang) * sh_h * .95), .012, "WG_RustSteel", 8)
    # --- east end: cargo doors, north leaf open ~105 deg
    dw, dh = (W - .2) / 2, Hc - .42
    ex = x1 - .02
    box("Door frame header", (ex, Hc - .15, 0), (.12, .16, W), "WG_OlivePaint", .01)
    box("Door sill", (ex, .2, 0), (.12, .1, W), "WG_RustSteel", .008)
    # south leaf closed
    leaf_s = [box("Door leaf", (ex + .03, .25 + dh / 2, -dw / 2 - .02), (.05, dh, dw - .02), "WG_OlivePaint", .008)]
    for zz in (-dw + .18, -.2):
        leaf_s.append(cyl("Locking bar", (ex + .1, .3, zz), (ex + .1, .25 + dh, zz), .016, "WG_RustSteel", 8))
        leaf_s.append(box("Locking handle", (ex + .14, 1.25, zz + .12), (.03, .05, .26), "WG_RustSteel", .004))
        for y in (.32, .25 + dh - .05):
            leaf_s.append(box("Cam keeper", (ex + .09, y, zz), (.06, .07, .08), "WG_RustSteel", .004))
    # north leaf open: hinged at north edge, swung out ~105 deg toward +x
    hz = W / 2 - .02
    leaf_n = [box("Door leaf open", (ex + .03, .25 + dh / 2, dw / 2 + .02), (.05, dh, dw - .02), "WG_OlivePaint", .008)]
    for zz in (dw - .18, .2):
        leaf_n.append(cyl("Locking bar", (ex + .1, .3, zz), (ex + .1, .25 + dh, zz), .016, "WG_RustSteel", 8))
        leaf_n.append(box("Locking handle", (ex + .14, 1.25, zz - .12), (.03, .05, .26), "WG_RustSteel", .004))
    leaf_n.append(box("Leaf inner stiffener", (ex - .01, .25 + dh / 2, dw / 2), (.03, dh - .2, .08), "WG_RustSteel", .004))
    hinge(leaf_n, (ex + .06, 0, hz), -100)
    # interior visible behind open leaf: desk, shelf, lamp
    box("Desk top", (x1 - .9, .95, .55), (1.1, .04, .6), "WG_Plywood", .004)
    for dx in (-.5, .5):
        box("Desk leg", (x1 - .9 + dx, .57, .55), (.04, .74, .55), "WG_RustSteel", .003)
    box("Wall shelf", (x1 - 1.4, 1.75, -W / 2 + .35), (1.4, .03, .35), "WG_Plywood", .003)
    empty("LIGHT_interior", (x1 - 1.2, Hc - .35, 0))
    empty("MOUNT_desk", (x1 - .9, .97, .55), (0, 90, 0))
    # --- door steps (steel) at the east end
    for i, (dx, y) in enumerate(((.35, .04), (.62, -.13), (.89, -.3))):
        box("Step tread", (x1 + dx, y + .15, .6), (.26, .04, 1.0), "WG_PlateSteel", .004)
    for z in (.08, 1.12):
        box("Step stringer", (x1 + .6, -.05, z), (.85, .45, .04), "WG_RustSteel", .004, rot=(0, 0, -30))
    # --- roof kit: sandbag rows are separate modules; antenna, solar panel, cable tray
    cyl("Antenna mast", (x0 + .6, Hc, z0 + .35), (x0 + .6, Hc + 3.1, z0 + .35), .025, "WG_RustSteel", 8)
    cyl("Antenna whip", (x0 + .6, Hc + 3.1, z0 + .35), (x0 + .6, Hc + 4.4, z0 + .35), .008, "WG_Rubber", 6)
    for dz, dx in ((.9, .6), (-.4, 1.1)):
        tube("Antenna guy", [(x0 + .6, Hc + 2.6, z0 + .35), (x0 + .6 + dx, Hc + .02, z0 + .35 + dz)], .004, "WG_Rubber", 4)
    box("Solar frame", (x0 + 2.0, Hc + .35, -.2), (1.7, .05, 1.05), "WG_RustSteel", .004, rot=(22, 0, 0))
    box("Solar cells", (x0 + 2.0, Hc + .38, -.2), (1.62, .01, .98), "WG_Solar", 0, rot=(22, 0, 0))
    for dz in (-.6, .2):
        box("Solar leg", (x0 + 2.0, Hc + .18, dz), (1.5, .35, .04), "WG_RustSteel", .003)
    tube("Cable run", [(x0 + 2.0, Hc + .1, -.7), (x0 + 2.0, Hc + .04, z1 - .1), (x0 + 2.0, Hc - .3, z1 + .02), (x0 + 2.2, .5, z1 + .02)], .014, "WG_Rubber", 6)
    empty("MOUNT_searchlight", (x0 + 1.0, Hc + .02, z1 - .45), (0, 20, 0))
    empty("MOUNT_aircon", (-.8, 1.3, z0 - .2), (0, 180, 0))
    empty("MOUNT_walllamp_n", (wc, 2.35, z1 + .03), (0, 0, 0))
    empty("MOUNT_walllamp_e", (x1 + .03, 2.3, -.7), (0, 90, 0))
    empty("LIGHT_window", (wc, 1.6, z1 - .5))
    empty("MOUNT_locker", (x0 + 1.55 + 1.6, .0, z1 + .32))
    # footings: concrete blocks + timber sleepers under the corners (extend below grade)
    for x in (x0 + .35, x1 - .35):
        for z in (z0 + .3, z1 - .3):
            box("Footing block", (x, -.4, z), (.55, .8, .45), "WG_Concrete", .02)
        box("Sleeper", (x, .0, 0), (.22, .14, W + .5), "WG_RustSteel", .01)
    # collision
    box("COL_Container", (0, Hc / 2, 0), (L, Hc, W), "WG_Collider", 0)
    box("COL_Steps", (x1 + .6, -.1, .6), (1.0, .5, 1.0), "WG_Collider", 0)
    box("COL_Counter", (wc, wy0, z1 + .2), (wx1 - wx0 + .3, .3, .42), "WG_Collider", 0)
    export("WG_GuardPost", "20 ft ISO container Warden post: corrugated walls, issue window with awning shutter, open cargo door, roof antenna/solar")


def arms_locker():
    """Steel weapons cabinet 1.0 x 1.9 x .52, origin floor centre, front faces -Z (toward the lane after placement)."""
    reset()
    Wd, Hh, D = 1.0, 1.9, .52
    fz = -D / 2
    box("Locker body side", (-Wd / 2 + .02, Hh / 2 + .08, 0), (.04, Hh, D), "WG_OlivePaint", .008)
    box("Locker body side", (Wd / 2 - .02, Hh / 2 + .08, 0), (.04, Hh, D), "WG_OlivePaint", .008)
    box("Locker back", (0, Hh / 2 + .08, D / 2 - .02), (Wd, Hh, .04), "WG_OlivePaint", .008)
    box("Locker top", (0, Hh + .06, 0), (Wd + .02, .05, D + .02), "WG_OlivePaint", .01)
    box("Locker bottom", (0, .1, 0), (Wd, .04, D), "WG_OlivePaint", .006)
    box("Locker plinth", (0, .04, 0), (Wd - .06, .08, D - .06), "WG_RustSteel", .006)
    # interior: dark lining, rack bars with pistol cradles, lower shelf
    box("Locker interior", (0, Hh / 2 + .08, D / 2 - .05), (Wd - .1, Hh - .1, .01), "WG_InteriorDark", 0)
    for y in (.72, 1.34):
        box("Rack shelf", (0, y, .02), (Wd - .1, .025, D - .12), "WG_PlateSteel", .003)
    for y in (1.02, 1.62):
        box("Cradle bar", (0, y, .12), (Wd - .12, .05, .05), "WG_RustSteel", .004)
        for x in (-.3, 0, .3):
            box("Pistol cradle", (x, y + .04, .08), (.06, .08, .1), "WG_Rubber", .004)
    box("Charge strip", (0, 1.82, fz + .08), (Wd - .14, .02, .02), "WG_CyanGlow", 0)
    empty("MOUNT_pistol_1", (-.3, 1.1, .02)); empty("MOUNT_pistol_2", (.3, 1.1, .02)); empty("MOUNT_pistol_3", (0, 1.7, .02))
    empty("MOUNT_ammo", (-.2, .76, 0)); empty("LIGHT_locker", (0, 1.75, -.1))
    # right door closed with ARMS stencil plate; left door open 110 deg
    dw = Wd / 2 - .02
    box("Door right", (dw / 2 + .01, Hh / 2 + .08, fz - .01), (dw, Hh - .06, .03), "WG_OlivePaint", .006)
    quad("Arms plate", (dw / 2 + .01, 1.38, fz - .03), .44, .22, "WG_SignArms", facing=(0, 0, -1))
    box("Door handle", (.06, 1.0, fz - .05), (.03, .22, .03), "WG_RustSteel", .004)
    for y in (.3, 1.0, 1.7):
        box("Vent slot", (dw / 2 + .01, y + .45, fz - .026), (.3, .015, .005), "WG_InteriorDark", 0)
    left = [box("Door left open", (-dw / 2 - .01, Hh / 2 + .08, fz - .01), (dw, Hh - .06, .03), "WG_OlivePaint", .006),
            box("Door left stiffener", (-dw / 2 - .01, Hh / 2 + .08, fz + .01), (.06, Hh - .3, .02), "WG_RustSteel", .003),
            box("Door left handle", (-.06, 1.0, fz - .05), (.03, .22, .03), "WG_RustSteel", .004)]
    hinge(left, (-Wd / 2, 0, fz - .01), 110)
    for x in (-Wd / 2, Wd / 2):
        for y in (.25, Hh - .1):
            cyl("Hinge", (x, y, fz - .01), (x, y + .1, fz - .01), .012, "WG_RustSteel", 8)
    # status beacon on top
    cyl("Beacon housing", (.32, Hh + .085, -.1), (.32, Hh + .13, -.1), .06, "WG_RustSteel", 12)
    cyl("Beacon lens", (.32, Hh + .13, -.1), (.32, Hh + .25, -.1), .05, "WG_CyanGlow", 14)
    empty("LIGHT_beacon", (.32, Hh + .3, -.1))
    box("COL_Locker", (0, Hh / 2 + .05, 0), (Wd, Hh + .1, D), "WG_Collider", 0)
    export("WG_ArmsLocker", "Warden steel arms cabinet, left door open, pistol cradles, cyan charge strip + beacon")


def boom_barrier():
    reset()
    box("Boom footing", (0, -.15, 0), (.7, .4, .7), "WG_Concrete", .02)
    box("Boom cabinet", (0, .6, 0), (.42, 1.1, .42), "WG_OlivePaint", .012)
    box("Boom cabinet cap", (0, 1.18, 0), (.48, .05, .48), "WG_RustSteel", .008)
    box("Boom hazard", (0, .3, 0), (.44, .3, .44), "WG_Hazard", .006)
    cyl("Boom hub", (0, 1.0, -.27), (0, 1.0, .27), .09, "WG_RustSteel", 16)
    # arm raised ~82 degrees; pivot empty lets Unity lower it later
    piv = empty("Boom pivot", (0, 1.0, 0))
    ang = math.radians(82); L = 5.4
    tipx, tipy = math.cos(ang) * L, 1.0 + math.sin(ang) * L
    arm = cyl("Boom arm", (0, 1.0, .0), (tipx, tipy, 0), .055, "WG_Hazard", 16)
    cw = box("Boom counterweight", (-math.cos(ang) * .55, 1.0 - math.sin(ang) * .55, 0), (.42, .3, .24), "WG_RustSteel", .01, rot=(0, 0, 82))
    # rest fork at 5.6 m along the lane (Unity +X local)
    box("Rest post", (5.6, .5, 0), (.1, 1.0, .1), "WG_OlivePaint", .008)
    box("Rest fork", (5.6, 1.02, 0), (.1, .1, .22), "WG_RustSteel", .006)
    box("Rest footing", (5.6, -.1, 0), (.36, .3, .36), "WG_Concrete", .02)
    box("COL_Boom", (0, .55, 0), (.5, 1.2, .5), "WG_Collider", 0)
    box("COL_Rest", (5.6, .5, 0), (.2, 1.0, .2), "WG_Collider", 0)
    export("WG_BoomBarrier", "boom barrier, arm raised, rest fork 5.6 m along +X")


def shade_net():
    """Shade cloth: container roof edge (north, 2.55 m) to two poles at 2.25 m, 3.6 x 2.1 m, cloth-simulated sag."""
    reset()
    W, D = 3.6, 2.1
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=36, y_subdivisions=22, size=1)
    cloth = bpy.context.active_object; cloth.name = "Shade cloth"
    cloth.scale = (W, D, 1); bpy.ops.object.transform_apply(scale=True)
    # grid local: x along width (Unity -X), y along depth (Unity -Z). Place: far edge (pole) y=-D/2 -> Unity z=+D
    cloth.location = U(0, 2.5, D / 2)
    bpy.ops.object.transform_apply(location=True)
    # tilt: near edge (container, Unity z=0) higher
    for v in cloth.data.vertices:
        uz = -v.co.y
        v.co.z = 2.55 - (uz / D) * .3
    vg = cloth.vertex_groups.new(name="pin")
    pins = []
    for v in cloth.data.vertices:
        uz = -v.co.y; ux = -v.co.x
        if (abs(uz) < .02) or (abs(uz - D) < .02 and abs(abs(ux) - W / 2) < .15):
            pins.append(v.index)
    vg.add(pins, 1.0, "REPLACE")
    m = cloth.modifiers.new("Cloth", "CLOTH"); s = m.settings
    s.vertex_group_mass = "pin"; s.quality = 8; s.mass = .25; s.tension_stiffness = 12; s.compression_stiffness = 12; s.shear_stiffness = 6; s.bending_stiffness = .3
    bpy.context.scene.frame_start = 1; bpy.context.scene.frame_end = 48
    m.point_cache.frame_end = 48
    for f in range(1, 49):
        bpy.context.scene.frame_set(f)
    bpy.context.view_layer.objects.active = cloth
    bpy.ops.object.modifier_apply(modifier="Cloth")
    cloth.data.materials.append(mat("WG_ShadeCloth"))
    sol = cloth.modifiers.new("sol", "SOLIDIFY"); sol.thickness = .006
    bpy.ops.object.modifier_apply(modifier="sol")
    box_uv(cloth, scale=1.0)
    for p in cloth.data.polygons: p.use_smooth = True
    # poles, guy lines, edge batten along the container
    for s in (-1, 1):
        x = s * (W / 2 - .05)
        cyl("Shade pole", (x, -.1, D), (x, 2.28, D), .035, "WG_RustSteel", 10)
        box("Pole foot", (x, .02, D), (.24, .04, .24), "WG_RustSteel", .004)
        tube("Guy line", [(x, 2.25, D), (x + s * .5, 0, D + 1.4)], .004, "WG_Rubber", 4)
        cyl("Guy peg", (x + s * .5, -.2, D + 1.4), (x + s * .5, .08, D + 1.4), .012, "WG_RustSteel", 6)
    cyl("Edge batten", (-W / 2, 2.55, .02), (W / 2, 2.55, .02), .025, "WG_RustSteel", 8)
    export("WG_ShadeNet", "cloth-simulated shade canopy with poles and guy lines; origin = container wall foot")


def notice_board():
    reset()
    for x in (-.72, .72):
        box("Board post", (x, .95, 0), (.1, 2.3, .1), "WG_RustSteel", .008)
    box("Board", (0, 1.4, .0), (1.5, 1.0, .03), "WG_Plywood", .005)
    box("Board frame", (0, 1.92, 0), (1.56, .05, .06), "WG_OlivePaint", .005)
    box("Board frame", (0, .88, 0), (1.56, .05, .06), "WG_OlivePaint", .005)
    box("Drip cap", (0, 2.08, -.08), (1.7, .03, .3), "WG_OlivePaint", .004, rot=(-12, 0, 0))
    box("Header plate backing", (0, 2.28, .0), (1.2, .3, .03), "WG_OlivePaint", .004)
    quad("Header plate", (0, 2.28, -.017), 1.18, .29, "WG_SignBriefing", facing=(0, 0, -1))
    papers = [("WG_PaperMap", (-.33, 1.45), .62, .46, -2), ("WG_PaperNotice", (.4, 1.58), .3, .42, 3), ("WG_PaperRoster", (.42, 1.1), .32, .34, -4), ("WG_PaperNotice", (-.46, 1.02), .22, .3, 6)]
    for m, (x, y), w, h, ang in papers:
        q = quad("Pinned paper", (x, y, -.018), w, h, m, facing=(0, 0, -1), up=(math.sin(math.radians(ang)), math.cos(math.radians(ang)), 0))
    for x, y in ((-.6, 1.66), (-.06, 1.66), (.27, 1.78), (.53, 1.78), (.3, 1.26), (.55, 1.26), (-.55, 1.16)):
        cyl("Pin", (x, y, -.03), (x, y, -.012), .007, "WG_CyanGlow" if x > 0 else "WG_RustSteel", 6)
    box("COL_Board", (0, 1.2, 0), (1.6, 2.4, .12), "WG_Collider", 0)
    export("WG_NoticeBoard", "field briefing board with pinned map/notices")


def post_sign(name, material, w, h, post_h, note):
    reset()
    for x in (-w / 2 + .12, w / 2 - .12):
        box("Sign post", (x, (post_h + h) / 2 - .3, .06), (.08, post_h + h + .6, .08), "WG_RustSteel", .006)
    box("Sign backing", (0, post_h + h / 2, .025), (w, h, .03), "WG_OlivePaint", .005)
    quad("Sign face", (0, post_h + h / 2, .008), w - .02, h - .02, material, facing=(0, 0, -1))
    for x in (-w / 2 + .12, w / 2 - .12):
        for y in (post_h + .15, post_h + h - .15):
            box("Sign clamp", (x, y, .05), (.12, .06, .06), "WG_RustSteel", .003)
    box(f"COL_{name}", (0, (post_h + h) / 2, .04), (w, post_h + h, .12), "WG_Collider", 0)
    export(name, note)


def range_flag():
    reset()
    box("Flag footing", (0, -.1, 0), (.5, .3, .5), "WG_Concrete", .02)
    cyl("Flag pole", (0, 0, 0), (0, 4.6, 0), .035, "WG_RustSteel", 10)
    cyl("Flag finial", (0, 4.6, 0), (0, 4.68, 0), .045, "WG_RustSteel", 10)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=20, y_subdivisions=12, size=1)
    f = bpy.context.active_object; f.name = "Range flag"
    for v in f.data.vertices:
        u = v.co.x + .5; t = v.co.y + .5
        ux, uy, uz = .04 + u * 1.1, 4.5 - t * .7, .09 * math.sin(u * 7.5) * u
        v.co = U(ux, uy - u * u * .12, uz)
    f.data.materials.append(mat("WG_FlagRed"))
    sol = f.modifiers.new("s", "SOLIDIFY"); sol.thickness = .004
    bpy.context.view_layer.objects.active = f; bpy.ops.object.modifier_apply(modifier="s"); box_uv(f)
    for p in f.data.polygons: p.use_smooth = True
    for y in (4.48, 3.82):
        cyl("Flag clip", (0, y, 0), (.05, y, 0), .012, "WG_RustSteel", 6)
    box("COL_Flag", (0, 2.3, 0), (.12, 4.6, .12), "WG_Collider", 0)
    export("WG_RangeFlag", "range flag pole, red flag raised")


def firing_bench():
    """Plywood shooting bench on steel trestles, 2.4 m, origin floor centre, shooter side -Z."""
    reset()
    box("Bench top", (0, .92, 0), (2.4, .04, .62), "WG_Plywood", .004)
    box("Bench edge", (0, .9, -.31), (2.4, .07, .03), "WG_Hazard", .003)
    for x in (-1.0, 1.0):
        for z in (-.24, .24):
            cyl("Trestle leg", (x, 0, z), (x + .0, .9, z * .6), .025, "WG_RustSteel", 8)
        box("Trestle bar", (x, .45, 0), (.04, .04, .45), "WG_RustSteel", .003)
    quad("Firing line plate", (0, .82, -.332), 1.0, .25, "WG_SignFiringLine", facing=(0, 0, -1))
    box("COL_Bench", (0, .46, 0), (2.4, .92, .62), "WG_Collider", 0)
    export("WG_FiringBench", "range firing bench with FIRING LINE plate")


def light_tower():
    """Trailer-mounted light tower, mast up, four flood panels. Origin trailer centre on the ground, tow bar +X."""
    reset()
    box("Trailer chassis", (0, .55, 0), (2.4, .12, 1.2), "WG_RustSteel", .01)
    box("Trailer body", (-.1, 1.05, 0), (2.0, .9, 1.1), "WG_OlivePaint", .03)
    box("Trailer lid", (-.1, 1.52, 0), (2.04, .05, 1.14), "WG_OlivePaint", .015)
    for z in (-.556, .556):
        for i in range(6):
            box("Louvre", (-.8 + i * .12, 1.05, z), (.06, .5, .02), "WG_InteriorDark", .004)
    box("Tow bar", (1.55, .5, 0), (1.2, .08, .08), "WG_RustSteel", .006)
    box("Tow hitch", (2.1, .45, 0), (.14, .1, .14), "WG_RustSteel", .01)
    for z in (-.7, .7):
        cyl("Wheel", (-.2, .33, z - .05 * (1 if z > 0 else -1)), (-.2, .33, z + .12 * (1 if z > 0 else -1)), .33, "WG_Rubber", 20)
        cyl("Hub", (-.2, .33, z + .12 * (1 if z > 0 else -1)), (-.2, .33, z + .14 * (1 if z > 0 else -1)), .14, "WG_RustSteel", 12)
        box("Mudguard", (-.2, .72, z), (.8, .03, .2), "WG_OlivePaint", .006)
    for x, z in ((1.0, -.9), (1.0, .9), (-1.1, -.9), (-1.1, .9)):
        cyl("Outrigger", (x * .8, .5, z * .6), (x, .15, z), .035, "WG_RustSteel", 8)
        box("Outrigger pad", (x, .03, z), (.28, .05, .28), "WG_RustSteel", .004)
    for r, y0, y1 in ((.11, 1.55, 4.2), (.085, 4.2, 6.6), (.065, 6.6, 8.4)):
        cyl("Mast section", (-.7, y0, 0), (-.7, y1, 0), r, "WG_OlivePaint" if r > .1 else "WG_RustSteel", 16)
    tube("Mast cable", [(-.6, 1.6, .12), (-.6, 4.0, .12), (-.62, 6.5, .1), (-.66, 8.2, .08)], .012, "WG_Rubber", 6)
    box("Lamp bar", (-.7, 8.55, 0), (.1, .1, 1.7), "WG_RustSteel", .006)
    for z in (-.62, -.2, .2, .62):
        box("Flood housing", (-.55, 8.35 + (0 if abs(z) < .3 else .38), z * 1.0), (.14, .4, .36), "WG_RustSteel", .012, rot=(0, 0, -25))
        box("Flood lens", (-.47, 8.31 + (0 if abs(z) < .3 else .38), z * 1.0), (.02, .34, .3), "WG_LampLens", 0, rot=(0, 0, -25))
    empty("LIGHT_tower", (-.2, 8.3, 0), (35, 90, 0))
    box("COL_Trailer", (0, .8, 0), (2.4, 1.6, 1.3), "WG_Collider", 0)
    box("COL_Mast", (-.7, 5.0, 0), (.25, 7.0, .25), "WG_Collider", 0)
    export("WG_LightTower", "trailer light tower, mast raised, four flood panels aimed along +X")


ASSETS = {"WG_Sandbags": sandbag_modules, "WG_GatePortal": gate_portal, "WG_SlidingGate": sliding_gate, "WG_GuardPost": guard_post,
          "WG_ArmsLocker": arms_locker, "WG_BoomBarrier": boom_barrier, "WG_ShadeNet": shade_net, "WG_NoticeBoard": notice_board,
          "WG_RangeSign": lambda: post_sign("WG_RangeSign", "WG_SignRange", 2.0, 1.0, 1.1, "range sign on posts"),
          "WG_LiveFireSign": lambda: post_sign("WG_LiveFireSign", "WG_SignLiveFire", 1.0, .75, .95, "live fire warning sign"),
          "WG_RangeControlSign": lambda: post_sign("WG_RangeControlSign", "WG_SignRangeControl", .8, .4, 1.25, "range control label post"),
          "WG_RangeFlag": range_flag, "WG_FiringBench": firing_bench, "WG_LightTower": light_tower}

if __name__ == "__main__":
    random.seed(2609)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for k, fn in ASSETS.items():
        if only and k not in only:
            continue
        fn()
    rp = HERE / "authored-assets.json"
    old = json.loads(rp.read_text()) if rp.exists() else {}
    old.update(REPORT); rp.write_text(json.dumps(old, indent=1))
