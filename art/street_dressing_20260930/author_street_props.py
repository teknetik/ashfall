"""Ward street dressing: Blender-authored props, Blender 5.2 headless (30 September 2026).

The pieces no library has in the Ward's own terms, all original geometry with the kit's generated or CC0 tiling maps
(prepare_textures.py): tied refuse sacks (a sign that people keep the street, not that it is abandoned), a tarp
cloth-simulated over a stack of stock with rope tie-downs, the loose litter that wind and feet leave at wall bases
(notices and forms, a flattened carton, crushed tins, a rag) and an open steel scrap skip holding sorted salvage
(the scanned wheel rims and tyre, pipe offcuts and bent sheet) instead of scrap strewn across the paving.

Origins at the centre of the footprint on the ground; front faces Unity +Z (Blender -Y). Deterministic (seeded).
Run:  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P author_street_props.py [-- id ...]
Out:  unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props/<id>/<id>_LOD0..n.glb, Props/authored-props.json
"""
import bpy, bmesh, json, math, random, sys, zlib
from pathlib import Path
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def obj_from_bm(bm, name, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(mat(m))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def triangulate(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(ob.data); bm.free()


def ground(ob):
    """Footprint centre to the origin, base on the ground; returns the Unity-axis size."""
    vs = [v.co for v in ob.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    ob.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    ob.data.update()
    return [round(mx.x - mn.x, 4), round(mx.z - mn.z, 4), round(mx.y - mn.y, 4)]


def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    return ob


def export_lods(pid, ob, ratios, report, notes, collider=True):
    triangulate(ob)
    size = ground(ob)
    dst = OUT / pid
    dst.mkdir(parents=True, exist_ok=True)
    lods = [ob]
    for i, r in enumerate(ratios):
        c = bpy.data.objects.new(f"SD_{pid}_LOD{i + 1}", ob.data.copy())
        bpy.context.scene.collection.objects.link(c)
        for o in bpy.context.selected_objects:
            o.select_set(False)
        c.select_set(True); bpy.context.view_layer.objects.active = c
        d = c.modifiers.new("d", "DECIMATE"); d.ratio = r; d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="d")
        lods.append(c)
    counts = []
    for i, o in enumerate(lods):
        o.name = f"SD_{pid}_LOD{i}"
        for x in bpy.context.selected_objects:
            x.select_set(False)
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.export_scene.gltf(filepath=str(dst / f"{pid}_LOD{i}.glb"), export_format="GLB", use_selection=True, export_yup=True,
                                  export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                                  export_materials="EXPORT", export_vertex_color="NONE", export_extras=False)
        counts.append(tris(o))
    report[pid] = {"source": "art/street_dressing_20260930/author_street_props.py", "notes": notes, "size": size, "lods": counts,
                   "materials": {m.name: {"authored": True} for m in ob.data.materials}, "collider": collider}
    print(pid, size, counts, [m.name for m in ob.data.materials], flush=True)


def cyl_uv(bm, uv, tile, cx=0.0, cy=0.0):
    """Cylindrical UVs in metres/tile around the vertical axis (seam handled per face)."""
    for f in bm.faces:
        angs = [math.atan2(l.vert.co.y - cy, l.vert.co.x - cx) for l in f.loops]
        ref = angs[0]
        for l, a in zip(f.loops, angs):
            while a - ref > math.pi:
                a -= 2 * math.pi
            while a - ref < -math.pi:
                a += 2 * math.pi
            r = math.hypot(l.vert.co.x - cx, l.vert.co.y - cy)
            l[uv].uv = (a * max(r, 0.12) / tile, l.vert.co.z / tile)


def box_uv(bm, uv, tile):
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            p = l.vert.co
            u, v = [(p.y, p.z), (p.x, p.z), (p.x, p.y)][ax]
            l[uv].uv = (u / tile, v / tile)


# ====================================================================== tied refuse sacks
def sack(pid, seed, w, d, h, lean, slump, material, report):
    """A filled hessian sack tied at the neck: boxy cross-section (superellipse) with seam ears at the bottom corners,
    vertical creases above the belly where the cloth hangs, lumpy contents, shoulders drawn into a gathered neck under
    a rope tie, and a long frilled ear that flops to one side. Slumps and leans a little."""
    rng = random.Random(seed)
    bm = bmesh.new()
    ph1, ph2 = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    flop = rng.choice((-1, 1)) * rng.uniform(0.05, 0.09)
    # (t, radius factor) profile from the base centre to the top of the ear, resampled finely
    key = [(0.0, 0.0), (0.01, 0.6), (0.035, 0.86), (0.09, 0.97), (0.3, 1.0), (0.52, 0.98), (0.64, 0.9), (0.72, 0.72),
           (0.77, 0.46), (0.8, 0.24), (0.83, 0.15), (0.855, 0.19), (0.9, 0.3), (0.95, 0.38), (0.985, 0.3), (1.0, 0.0)]

    def prof(t):
        for (t0, r0), (t1, r1) in zip(key, key[1:]):
            if t <= t1:
                u = (t - t0) / (t1 - t0)
                return r0 + (r1 - r0) * (u * u * (3 - 2 * u))
        return 0.0
    ts = sorted({k[0] for k in key} | {i / 36 for i in range(37)})
    segs = 44
    rows = []
    for t in ts:
        rf = prof(t)
        row = []
        n_exp = 3.2 if t < 0.66 else 2.0 + 1.2 * max(0.0, (0.76 - t) / 0.1)      # boxy body, round neck
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ca, sa = math.cos(a), math.sin(a)
            sup = (abs(ca) ** n_exp + abs(sa) ** n_exp) ** (-1.0 / n_exp)
            gather = math.exp(-((t - 0.84) / 0.09) ** 2) + 0.7 * math.exp(-((t - 0.95) / 0.04) ** 2)
            pleat = 1 + 0.22 * gather * math.sin(a * 11 + ph1) + 0.08 * gather * math.sin(a * 23 + ph2)
            r = rf * sup * pleat
            p = Vector((ca * r * w / 2, sa * r * d / 2, t * h))
            nrm = Vector((ca, sa, 0))
            # seam ears at the two bottom corners (a = 0 and pi)
            if t < 0.16:
                ear = max(0.0, abs(ca) - 0.9) / 0.1 * (0.16 - t) / 0.16
                p += nrm * ear * 0.035
            # hanging creases (stretched vertically) and lumpy contents
            if 0.05 < t < 0.78:
                crease = noise.noise(Vector((ca * 3.0 + seed, sa * 3.0, t * 0.8))) * min(1.0, (t - 0.05) / 0.3)
                lump = noise.noise(Vector((p.x * 7 + seed, p.y * 7, p.z * 7))) + 0.5 * noise.noise(Vector((p.x * 17, p.y * 17 + seed, p.z * 17)))
                p += nrm * (crease * 0.03 * (0.4 + t) + lump * 0.014)
            # the ear above the tie flops to one side
            if t > 0.83:
                p.x += flop * ((t - 0.83) / 0.17) ** 1.5
                p.z -= abs(flop) * 0.4 * ((t - 0.83) / 0.17) ** 2
            sgt = max(0.0, t - 0.12) ** 1.6
            p.x += lean * sgt * h
            p.z -= slump * sgt * h * 0.35
            row.append(bm.verts.new(p))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(segs):
            a, b = rows[j][i], rows[j][(i + 1) % segs]
            c, e = rows[j + 1][(i + 1) % segs], rows[j + 1][i]
            bm.faces.new([a, b, c, e])
    # the base and ear-top rows are rings of coincident points: merging them turns those quads into fans
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    uv = bm.loops.layers.uv.new("UVMap")
    cyl_uv(bm, uv, 0.45)
    for f in bm.faces:
        f.material_index = 0
    body = obj_from_bm(bm, pid + "_body", [material])
    # the tie: a twisted rope ring round the neck
    neck_pts = [v.co for v in body.data.vertices if abs(v.co.z - (0.83 * h)) < 0.02 * h]
    cx = sum(p.x for p in neck_pts) / max(1, len(neck_pts)) if neck_pts else 0.0
    rr = max(0.03, (max((p - Vector((cx, 0, p.z))).length for p in neck_pts) if neck_pts else 0.05) * 1.02)
    bm = bmesh.new()
    rope_r = 0.009
    segs, sides = 36, 6
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        c = Vector((cx + rr * math.cos(a), rr * math.sin(a), 0.83 * h + 0.004 * math.sin(a * 3)))
        tang = Vector((-math.sin(a), math.cos(a), 0))
        nrm = Vector((math.cos(a), math.sin(a), 0))
        ring = []
        for j in range(sides):
            b = 2 * math.pi * j / sides + a * 4
            ring.append(bm.verts.new(c + nrm * math.cos(b) * rope_r + Vector((0, 0, 1)) * math.sin(b) * rope_r))
        rings.append(ring)
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(segs):
        for j in range(sides):
            f = bm.faces.new([rings[i][j], rings[(i + 1) % segs][j], rings[(i + 1) % segs][(j + 1) % sides], rings[i][(j + 1) % sides]])
            for k, l in enumerate(f.loops):
                l[uvl].uv = ((i + (k in (1, 2))) * 0.08, (j + (k in (2, 3))) * 0.06)
    # a loose tail of the tie
    tie = obj_from_bm(bm, pid + "_tie", ["SD_Rope"])
    ob = join([body, tie], "SD_" + pid)
    export_lods(pid, ob, (0.3, 0.08), report, f"tied refuse sack {w}x{d}x{h} m", collider=False)


# ====================================================================== litter
def paper(pid, seed, quadrant, crumple, curl, fold, report):
    rng = random.Random(seed)
    W, H = 0.21, 0.297
    bm = bmesh.new()
    nx, ny = 14, 20
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * W, (v - 0.5) * H
            z = 0.0
            z += crumple * (noise.noise(Vector((x * 18 + seed, y * 18, 0))) * 0.012 + noise.noise(Vector((x * 55, y * 55 + seed, 1))) * 0.004)
            z += curl * max(0.0, v - 0.7) ** 2 * 0.9                               # the top edge curls up
            z += fold * abs(u - 0.5) * 0.06                                        # opened along a fold (V)
            row.append((bm.verts.new((x, y, z)), (u, v)))
        verts.append(row)
    uv = bm.loops.layers.uv.new("UVMap")
    qx, qy = (quadrant % 2) * 0.5, (1 - quadrant // 2) * 0.5 - 0.5 + 0.5
    for j in range(ny):
        for i in range(nx):
            q = [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]]
            f = bm.faces.new([a for a, _ in q])
            for l, (_, (u, v)) in zip(f.loops, q):
                l[uv].uv = (qx + u * 0.5, (quadrant // 2 == 0) * 0.5 + v * 0.5)
    # rest on the ground: lowest point at 2 mm, then lift nothing below it
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z = v.co.z - zmin + 0.002
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = obj_from_bm(bm, "SD_" + pid, ["SD_Paper"])
    export_lods(pid, ob, (0.25,), report, "loose sheet of paper", collider=False)


def paper_ball(pid, seed, report):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.035)
    for v in bm.verts:
        p = v.co
        n = noise.noise(p * 60 + Vector((seed, 0, 0)))
        v.co = p * (1 + 0.35 * n) * Vector((1, 1, 0.8))
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (0.5 + p.x * 4, 0.5 + p.y * 4 + p.z * 2)
    ob = obj_from_bm(bm, "SD_" + pid, ["SD_Paper"])
    export_lods(pid, ob, (0.3,), report, "crumpled paper ball", collider=False)


def card_flat(pid, seed, half, report):
    """A flattened carton: two panels either side of a crease, one flap end lifted, corners dog-eared."""
    rng = random.Random(seed)
    W, H = 0.62, 0.42
    bm = bmesh.new()
    nx, ny = 24, 16
    verts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * W, (v - 0.5) * H
            z = 0.012 * max(0.0, 1 - abs(u - 0.47) / 0.04)                      # the crease stands up a little
            z += 0.07 * max(0.0, u - 0.86) ** 1.5 * 3                          # the flap end lifts
            z += 0.004 * noise.noise(Vector((x * 9 + seed, y * 9, 2)))
            if u < 0.1 and v < 0.12:
                z += 0.025 * (0.1 - u) / 0.1 * (0.12 - v) / 0.12                # dog-eared corner
            row.append((bm.verts.new((x, y, z)), (u, v)))
        verts.append(row)
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(ny):
        for i in range(nx):
            q = [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]]
            f = bm.faces.new([a for a, _ in q])
            for l, (_, (u, v)) in zip(f.loops, q):
                l[uv].uv = (half * 0.5 + u * 0.5, 0.5 + v * 0.5)
    # one double-sided sheet (a solidified copy was coplanar with it and z-fought), 1 mm off the paving
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin - 0.001
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = obj_from_bm(bm, "SD_" + pid, ["SD_Card"])
    export_lods(pid, ob, (0.3,), report, "flattened carton", collider=False)


def tin_crushed(pid, seed, half, lying, report):
    rng = random.Random(seed)
    bm = bmesh.new()
    r, h = 0.034, 0.118
    segs, rows = 24, 10
    rings = []
    for j in range(rows + 1):
        t = j / rows
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            squash = 0.42 + 0.58 * abs(t - 0.5) * 2                               # crushed in the middle
            pleat = 1 + 0.18 * (1 - abs(t - 0.5) * 2) * math.sin(a * 5 + seed)
            rr = r * (1 + (1 - squash) * 0.35) * pleat
            z = h * (0.5 + (t - 0.5) * (0.55 + 0.45 * squash))
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(rows):
        for i in range(segs):
            q = [rings[j][i], rings[j][(i + 1) % segs], rings[j + 1][(i + 1) % segs], rings[j + 1][i]]
            f = bm.faces.new(q)
            for k, l in enumerate(f.loops):
                ii = i + (1 if k in (1, 2) else 0)
                jj = j + (1 if k in (2, 3) else 0)
                l[uv].uv = (half * 0.5 + ii / segs * 0.5, jj / rows)
    for ring, uvv in ((rings[0], 0.02), (rings[-1], 0.98)):
        f = bm.faces.new(ring if uvv > 0.5 else ring[::-1])
        for l in f.loops:
            l[uv].uv = (half * 0.5 + 0.02, uvv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if lying:
        bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, h / 2), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = obj_from_bm(bm, "SD_" + pid, ["SD_Tin"])
    export_lods(pid, ob, (0.35,), report, "crushed tin", collider=False)


def rag(pid, seed, report):
    rng = random.Random(seed)
    bm = bmesh.new()
    n = 18
    S = 0.36
    verts = []
    for j in range(n + 1):
        row = []
        for i in range(n + 1):
            u, v = i / n, j / n
            x, y = (u - 0.5) * S, (v - 0.5) * S
            # bunched cloth: folds and a ridge where it was dropped
            z = 0.02 * max(0.0, noise.noise(Vector((x * 11 + seed, y * 11, 0)))) + 0.03 * math.exp(-((x + y * 0.4) / 0.05) ** 2)
            x += 0.03 * noise.noise(Vector((x * 7, y * 7 + seed, 3)))
            row.append((bm.verts.new((x, y, z)), (u, v)))
        verts.append(row)
    uv = bm.loops.layers.uv.new("UVMap")
    for j in range(n):
        for i in range(n):
            q = [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]]
            f = bm.faces.new([a for a, _ in q])
            for l, (_, (u, v)) in zip(f.loops, q):
                l[uv].uv = (u * 0.7, v * 0.7)
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = obj_from_bm(bm, "SD_" + pid, ["SD_Rag"])
    export_lods(pid, ob, (0.3,), report, "dropped rag", collider=False)


# ====================================================================== tarp over stacked stock (cloth simulation)
def tarp_stack(pid, seed, boxes, sheet, report):
    rng = random.Random(seed)
    proxies = []
    for (cx, cy, w, d, z0, h) in boxes:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, z0 + h / 2))
        o = bpy.context.active_object
        o.scale = (w, d, h)
        bpy.ops.object.transform_apply(scale=True)
        # soften the corners slightly so the cloth does not snag
        bev = o.modifiers.new("b", "BEVEL"); bev.width = 0.03; bev.segments = 2
        o.modifiers.new("c", "COLLISION")
        o.collision.thickness_outer = 0.012
        proxies.append(o)
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    gnd = bpy.context.active_object
    gnd.modifiers.new("c", "COLLISION")
    top = max(z0 + h for (_, _, _, _, z0, h) in boxes)
    SX, SY = sheet
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=int(SX / 0.045), y_subdivisions=int(SY / 0.045), size=1, location=(0, 0, top + 0.08))
    cloth = bpy.context.active_object
    cloth.scale = (SX, SY, 1)
    bpy.ops.object.transform_apply(scale=True)
    # a slight random rumple so the folds are not symmetric
    for v in cloth.data.vertices:
        v.co.z += 0.02 * noise.noise(Vector((v.co.x * 3 + seed, v.co.y * 3, 0)))
    cm = cloth.modifiers.new("cloth", "CLOTH")
    s = cm.settings
    s.quality = 8; s.mass = 0.45; s.tension_stiffness = 25; s.compression_stiffness = 25; s.shear_stiffness = 10
    s.bending_stiffness = 6.0; s.air_damping = 1.5
    cm.collision_settings.distance_min = 0.006
    cm.collision_settings.use_self_collision = False
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 70
    cm.point_cache.frame_start, cm.point_cache.frame_end = 1, 70
    for f in range(1, 71):
        sc.frame_set(f)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    cloth.select_set(True); bpy.context.view_layer.objects.active = cloth
    bpy.ops.object.modifier_apply(modifier="cloth")
    for o in proxies + [gnd]:
        bpy.data.objects.remove(o, do_unlink=True)
    # UVs: world-planar from above (canvas tiling ~0.6 m), then a thin solidify for a hem
    bm = bmesh.new(); bm.from_mesh(cloth.data)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (p.x / 0.6, p.y / 0.6 + p.z / 0.6 * 0.4)
    for v in bm.verts:
        v.co.z = max(v.co.z, 0.004)
    bm.to_mesh(cloth.data); bm.free()
    cloth.data.materials.clear(); cloth.data.materials.append(mat("SD_Tarp"))
    sol = cloth.modifiers.new("s", "SOLIDIFY"); sol.thickness = 0.004; sol.offset = 1
    bpy.ops.object.modifier_apply(modifier="s")
    for p in cloth.data.polygons:
        p.use_smooth = True
    # two rope tie-downs over the top, following the tarp (ray cast down)
    bvh = BVHTree.FromObject(cloth, bpy.context.evaluated_depsgraph_get())
    ropes = []
    for yline in (-0.22 * SY / 2.4 * 2, 0.22 * SY / 2.4 * 2):
        pts = []
        x = -SX / 2
        while x <= SX / 2:
            hit = bvh.ray_cast(Vector((x, yline, top + 1.0)), Vector((0, 0, -1)))
            if hit[0] is not None and hit[0].z > 0.02:
                pts.append(hit[0] + Vector((0, 0, 0.008)))
            x += 0.05
        if len(pts) > 4:
            pts = [pts[0] + Vector((-0.05, 0, -pts[0].z + 0.01))] + pts + [pts[-1] + Vector((0.05, 0, -pts[-1].z + 0.01))]
            bm = bmesh.new()
            rings = []
            for i, c in enumerate(pts):
                tng = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
                a1 = tng.cross(Vector((0, 1, 0))).normalized()
                a2 = tng.cross(a1).normalized()
                rings.append([bm.verts.new(c + (a1 * math.cos(2 * math.pi * k / 6) + a2 * math.sin(2 * math.pi * k / 6)) * 0.008) for k in range(6)])
            uvl = bm.loops.layers.uv.new("UVMap")
            for i in range(len(rings) - 1):
                for k in range(6):
                    f = bm.faces.new([rings[i][k], rings[i + 1][k], rings[i + 1][(k + 1) % 6], rings[i][(k + 1) % 6]])
                    for m, l in enumerate(f.loops):
                        l[uvl].uv = ((i + (m in (1, 2))) * 0.1, (k + (m in (2, 3))) * 0.1)
            ropes.append(obj_from_bm(bm, f"rope{len(ropes)}", ["SD_Rope"]))
    ob = join([cloth] + ropes, "SD_" + pid)
    export_lods(pid, ob, (0.3, 0.08), report, "tarp tied over stacked stock (cloth simulation)", collider=True)


# ====================================================================== scrap skip with sorted salvage
def import_prop(pid):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(OUT / pid / f"{pid}_LOD0.glb"))
    new = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    o = join(new, pid + "_part") if len(new) > 1 else new[0]
    return o


def scrap_skip(pid, seed, report):
    rng = random.Random(seed)
    L0, W0, L1, W1, Hs = 1.45, 0.9, 1.75, 1.1, 0.72     # base and rim footprints, height
    bm = bmesh.new()
    t = 0.004
    q0 = [(-L0 / 2, -W0 / 2), (L0 / 2, -W0 / 2), (L0 / 2, W0 / 2), (-L0 / 2, W0 / 2)]
    q1 = [(-L1 / 2, -W1 / 2), (L1 / 2, -W1 / 2), (L1 / 2, W1 / 2), (-L1 / 2, W1 / 2)]
    zb = 0.08                                           # on two skids
    vb = [bm.verts.new((x, y, zb)) for x, y in q0]
    vt = [bm.verts.new((x, y, zb + Hs)) for x, y in q1]
    bm.faces.new(vb[::-1])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vb[i], vb[j], vt[j], vt[i]])
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
    # dents on the sides
    for v in bm.verts:
        if zb + 0.05 < v.co.z < zb + Hs - 0.06:
            d = noise.noise(v.co * 3 + Vector((seed, 0, 0)))
            nrm = Vector((v.co.x, v.co.y, 0)).normalized()
            v.co -= nrm * max(0.0, d) * 0.03
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=t)
    uv = bm.loops.layers.uv.new("UVMap")
    bm.normal_update()
    box_uv(bm, uv, 1.1)
    skip = obj_from_bm(bm, "skip", ["SD_SkipSteel"])
    parts = [skip]
    # rolled rim, skids, lifting lugs and vertical ribs
    def bar(a, b, r, m, sides=8):
        bpy.ops.mesh.primitive_cylinder_add(vertices=sides, radius=r, depth=(Vector(b) - Vector(a)).length,
                                            location=(Vector(a) + Vector(b)) / 2)
        o = bpy.context.active_object
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = (Vector(b) - Vector(a)).to_track_quat("Z", "Y")
        o.data.materials.append(mat(m))
        bm2 = bmesh.new(); bm2.from_mesh(o.data)
        uvl = bm2.loops.layers.uv.verify()
        box_uv(bm2, uvl, 0.8)
        bm2.to_mesh(o.data); bm2.free()
        parts.append(o)
    for i in range(4):
        a = (*q1[i], zb + Hs); b = (*q1[(i + 1) % 4], zb + Hs)
        bar(a, b, 0.022, "SD_SkipSteel")
    for y in (-W0 / 2 + 0.12, W0 / 2 - 0.12):
        bar((-L0 / 2 - 0.04, y, 0.04), (L0 / 2 + 0.04, y, 0.04), 0.04, "SD_SkipSteel", 4)
    for x in (-L0 / 2 * 0.4, L0 / 2 * 0.4):
        for sgn in (-1, 1):
            yb, yt = sgn * W0 / 2, sgn * W1 / 2
            bar((x, yb + sgn * 0.01, zb + 0.02), (x * L1 / L0, yt + sgn * 0.01, zb + Hs - 0.03), 0.018, "SD_SkipSteel", 6)
    for sgn in (-1, 1):
        bar((sgn * (L1 / 2 - 0.08), -0.25, zb + Hs * 0.62), (sgn * (L1 / 2 - 0.08), 0.25, zb + Hs * 0.62), 0.03, "SD_SkipSteel", 8)
    # a fill surface just below the rim so the load has a body
    bm = bmesh.new()
    nx, ny = 20, 12
    vv = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            x, y = (u - 0.5) * (L1 - 0.06), (v - 0.5) * (W1 - 0.06)
            mound = 0.16 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            z = zb + Hs - 0.1 + mound + 0.03 * noise.noise(Vector((x * 5 + seed, y * 5, 0)))
            row.append(bm.verts.new((x, y, z)))
        vv.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new([vv[j][i], vv[j][i + 1], vv[j + 1][i + 1], vv[j + 1][i]])
    uvl = bm.loops.layers.uv.new("UVMap")
    bm.normal_update(); box_uv(bm, uvl, 0.7)
    parts.append(obj_from_bm(bm, "fill", ["SD_ScrapSheet"]))
    # the load: rims and a tyre from the kit, pipe offcuts, bent sheet
    rim_top = zb + Hs
    for k, (p, pos, rot) in enumerate([("rim_a", (-0.45, 0.12, rim_top - 0.12), (70, 0, 20)), ("rim_b", (0.2, -0.18, rim_top - 0.1), (62, 12, -40)),
                                        ("tyre", (0.52, 0.22, rim_top - 0.2), (58, 0, 75))]):
        o = import_prop(p)
        o.rotation_euler = [math.radians(a) for a in rot]
        o.location = pos
        parts.append(o)
    for k in range(9):
        L = rng.uniform(0.5, 1.2)
        x, y = rng.uniform(-0.55, 0.55), rng.uniform(-0.35, 0.35)
        a = rng.uniform(0, 6.28); tilt = rng.uniform(-0.35, 0.35)
        z = rim_top + rng.uniform(-0.05, 0.12)
        d = Vector((math.cos(a), math.sin(a), tilt)).normalized() * L / 2
        bar(tuple(Vector((x, y, z)) - d), tuple(Vector((x, y, z)) + d), rng.uniform(0.018, 0.045), "SD_ScrapSheet", 10)
    for k in range(5):
        bm = bmesh.new()
        w, hgt = rng.uniform(0.4, 0.8), rng.uniform(0.3, 0.55)
        n = 8
        vv = [[bm.verts.new(((i / n - 0.5) * w, 0.0, (j / 4) * hgt)) for i in range(n + 1)] for j in range(5)]
        for j in range(4):
            for i in range(n):
                bm.faces.new([vv[j][i], vv[j][i + 1], vv[j + 1][i + 1], vv[j + 1][i]])
        bend = rng.uniform(-0.4, 0.4)
        for v in bm.verts:
            v.co.y += bend * (v.co.x / w) ** 2 + 0.02 * noise.noise(v.co * 6 + Vector((k, seed, 0)))
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.003)
        uvl = bm.loops.layers.uv.new("UVMap"); bm.normal_update(); box_uv(bm, uvl, 0.7)
        o = obj_from_bm(bm, f"sheet{k}", ["SD_ScrapSheet"])
        o.rotation_euler = (math.radians(rng.uniform(-60, 60)), math.radians(rng.uniform(-30, 30)), rng.uniform(0, 6.28))
        o.location = (rng.uniform(-0.6, 0.6), rng.uniform(-0.35, 0.35), rim_top - 0.18)
        parts.append(o)
    ob = join(parts, "SD_" + pid)
    export_lods(pid, ob, (0.3, 0.08), report, "open steel scrap skip on skids with sorted salvage", collider=True)


BUILD = {
    "sack_tied_a": lambda r: sack("sack_tied_a", 11, 0.56, 0.44, 0.78, 0.02, 0.0, "SD_Sack", r),
    "sack_tied_b": lambda r: sack("sack_tied_b", 12, 0.62, 0.5, 0.64, 0.07, 0.3, "SD_Sack", r),
    "sack_tied_c": lambda r: sack("sack_tied_c", 13, 0.52, 0.42, 0.72, -0.05, 0.1, "SD_SackPale", r),
    "paper_a": lambda r: paper("paper_a", 21, 0, 1.0, 0.3, 0.0, r),
    "paper_b": lambda r: paper("paper_b", 22, 1, 0.6, 0.0, 1.0, r),
    "paper_c": lambda r: paper("paper_c", 23, 2, 1.4, 0.15, 0.3, r),
    "paper_d": lambda r: paper("paper_d", 24, 3, 0.9, 0.5, 0.0, r),
    "paper_ball": lambda r: paper_ball("paper_ball", 25, r),
    "card_flat_a": lambda r: card_flat("card_flat_a", 31, 0, r),
    "card_flat_b": lambda r: card_flat("card_flat_b", 32, 1, r),
    "tin_a": lambda r: tin_crushed("tin_a", 41, 0, True, r),
    "tin_b": lambda r: tin_crushed("tin_b", 42, 1, False, r),
    "rag": lambda r: rag("rag", 51, r),
    "tarp_stack": lambda r: tarp_stack("tarp_stack", 61, [(-0.25, 0.0, 0.8, 0.62, 0.0, 0.5), (0.42, 0.05, 0.55, 0.55, 0.0, 0.62),
                                                          (-0.15, 0.02, 0.6, 0.5, 0.5, 0.38)], (2.45, 2.0), r),
    "scrap_skip": lambda r: scrap_skip("scrap_skip", 71, r),
}


def main():
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(BUILD)
    path = OUT / "authored-props.json"
    report = json.loads(path.read_text()) if path.exists() else {}
    for pid in only:
        clean()
        BUILD[pid](report)
    path.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
