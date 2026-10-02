"""Salvage shop props: Blender (headless) inspection renders, Cycles on CPU at low samples.
Run through the capped wrapper:  ~/.local/state/ward-programme/blender.sh review.py -- <mode> <prop> [yaw]

  source <prop> [yaw]  the Meshy download (<prop>/textured.glb) as delivered: stats (objects, triangles, loose parts,
                       materials, map sizes, bounds) to <prop>/review/source-stats.json and textured views, uniformly
                       scaled to the target width with the base on the floor (front = Blender -Y = Unity +Z after the
                       optional yaw fix): front, side (from the right), back, three-quarter, a close view at 0.8 m and an
                       orthographic front with a 0.1 m grid (to read positions off) next to a 1.8 m scale figure.
  lods <SS_id>         the prepared Unity models (LOD0 and LOD1 .glb from the Unity Props folder) with the extracted maps:
                       side-by-side three-quarter views (near and at LOD1 distance) and a 0.8 m close of each.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
UNITY_PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODE, PROP = args[0], args[1]
YAW = float(args[2]) if len(args) > 2 else 0.0
if MODE == "lods":                         # PROP is the Unity id; renders go to the source attempt's folder
    SRC = json.loads((UNITY_PROPS / "salvage-shop-props.json").read_text())[PROP]["source"].split("/")[-2]
else:
    SRC = PROP
REC = json.loads((HERE / SRC / "record.json").read_text())
TW, TH, TD = REC["target_size_m"]          # width (x), height (y), depth (z), Unity axes
OUT = HERE / SRC / "review"
OUT.mkdir(exist_ok=True)


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in set(bpy.data.objects) - before]


def mesh_objects(objs):
    return [o for o in objs if o.type == "MESH"]


def world_bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in mesh_objects(objs) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def normalise(objs, yaw):
    """Parent the import under one empty, yaw it, scale uniformly to the target width, base on the floor, centred."""
    root = bpy.data.objects.new("fit", None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    root.rotation_euler = (0, 0, math.radians(yaw))
    bpy.context.view_layer.update()
    mn, mx = world_bounds(objs)
    s = TW / (mx.x - mn.x)
    root.scale = (s, s, s)
    bpy.context.view_layer.update()
    mn, mx = world_bounds(objs)
    root.location = (-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)
    bpy.context.view_layer.update()
    return s, world_bounds(objs)


def stats(objs):
    ms = mesh_objects(objs)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms)
    parts = []
    for o in ms:
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bm.verts.ensure_lookup_table()
        seen = set()
        mw = o.matrix_world
        for v in bm.verts:
            if v.index in seen:
                continue
            stack = [v]; comp = []
            seen.add(v.index)
            while stack:
                x = stack.pop(); comp.append(x)
                for e in x.link_edges:
                    w = e.other_vert(x)
                    if w.index not in seen:
                        seen.add(w.index); stack.append(w)
            ps = [mw @ c.co for c in comp]
            mn = Vector((min(p.x for p in ps), min(p.y for p in ps), min(p.z for p in ps)))
            mx = Vector((max(p.x for p in ps), max(p.y for p in ps), max(p.z for p in ps)))
            parts.append({"verts": len(comp), "min": [round(c, 3) for c in mn], "max": [round(c, 3) for c in mx]})
        nm = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
    parts.sort(key=lambda p: -p["verts"])
    imgs = {i.name: list(i.size) for i in bpy.data.images}
    custom = [o.data.has_custom_normals for o in ms] if hasattr(ms[0].data, "has_custom_normals") else None
    return {"mesh_objects": len(ms), "triangles": tris, "loose_parts": len(parts), "largest_parts": parts[:12],
            "small_parts_lt_50_verts": sum(1 for p in parts if p["verts"] < 50), "non_manifold_edges_last_mesh": nm,
            "materials": sorted({s.material.name for o in ms for s in o.material_slots if s.material}),
            "images": imgs, "custom_normals": custom,
            "vertices": sum(len(o.data.vertices) for o in ms)}


def scene_setup(samples=48, res=(1280, 960)):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.66, 0.72, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.55
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.2; sun.data.angle = math.radians(3)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35))     # from the front-left, above
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA")); sc.collection.objects.link(fill)
    fill.data.energy = 120; fill.data.size = 3
    fill.location = (2.5, -2.5, 2.6)
    fill.rotation_euler = (Vector((0, 0, 1)) - fill.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    g = bpy.context.active_object; gm = bpy.data.materials.new("floor"); gm.use_nodes = True
    b = gm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.42, 0.36, 0.29, 1); b.inputs["Roughness"].default_value = 0.85
    g.data.materials.append(gm)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    return sc, cam


def figure(x):
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.18, depth=1.8, location=(x, 0, 0.9))
    f = bpy.context.active_object; fm = bpy.data.materials.new("figure"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.25, 0.18, 1)
    f.data.materials.append(fm)
    return f


def shoot(sc, cam, name, pos, target, lens=35.0, ortho=None):
    cam.location = pos
    cam.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("render", sc.render.filepath, flush=True)


def grid(w, h):
    """0.1 m grid on a plane just in front of the model (front view), every metre darker."""
    objs = []
    gm = bpy.data.materials.new("grid"); gm.use_nodes = True
    nt = gm.node_tree; bsdf = nt.nodes["Principled BSDF"]
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1, 0.1, 0.6, 1); em.inputs[1].default_value = 2
    nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs[0])
    gm2 = bpy.data.materials.new("grid_m"); gm2.use_nodes = True
    em2 = gm2.node_tree.nodes.new("ShaderNodeEmission"); em2.inputs[0].default_value = (0.1, 1, 0.2, 1); em2.inputs[1].default_value = 3
    gm2.node_tree.links.new(em2.outputs[0], gm2.node_tree.nodes["Material Output"].inputs[0])
    y = -(TD / 2 + 0.6)
    n = int(round(w / 0.1))
    for i in range(-n, n + 1):
        x = i * 0.1
        major = i % 5 == 0
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
        c = bpy.context.active_object; c.scale = (0.004 if major else 0.0015, 0.001, h)
        c.data.materials.append(gm2 if major else gm); objs.append(c)
    for j in range(0, int(round(h / 0.1)) + 1):
        z = j * 0.1
        major = j % 5 == 0
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y, z))
        c = bpy.context.active_object; c.scale = (2 * w, 0.001, 0.004 if major else 0.0015)
        c.data.materials.append(gm2 if major else gm); objs.append(c)
    for o in objs:
        o.visible_shadow = False
    return objs


def views(sc, cam, h, tag=""):
    span = max(TW, h)
    d = span * 1.45 + 0.8
    mid = (0, 0, h * 0.5)
    shoot(sc, cam, f"{tag}front", (0, -d, h * 0.55 + 0.2), mid)
    shoot(sc, cam, f"{tag}side_right", (d * 0.9, 0, h * 0.55 + 0.2), mid)
    shoot(sc, cam, f"{tag}back", (0, d, h * 0.55 + 0.2), mid)
    shoot(sc, cam, f"{tag}three_quarter", (-d * 0.62, -d * 0.78, h * 0.75 + 0.5), (0, 0, h * 0.42))
    shoot(sc, cam, f"{tag}three_quarter_right", (d * 0.62, -d * 0.78, h * 0.75 + 0.5), (0, 0, h * 0.42))


def source():
    clear()
    objs = import_glb(HERE / PROP / "textured.glb")
    st = stats(objs)
    s, (mn, mx) = normalise(objs, YAW)
    size = [mx.x - mn.x, mx.z - mn.z, mx.y - mn.y]
    st.update(scale=s, yaw=YAW, fitted_size_unity_xyz=[round(v, 3) for v in size],
              target=REC["target_size_m"])
    (OUT / "source-stats.json").write_text(json.dumps(st, indent=1))
    print(json.dumps({k: v for k, v in st.items() if k != "largest_parts"}), flush=True)
    sc, cam = scene_setup()
    h = size[1]
    fig = figure(-(TW / 2 + 0.45))
    views(sc, cam, h)
    # close views at the player's distance (0.8 m from the front face), eye height 1.6 m
    front = mn.y
    look_h = min(h * 0.6, 1.2)
    shoot(sc, cam, "close_centre", (0.15, front - 0.8, 1.6), (0.05, front + TD * 0.4, look_h), lens=28)
    shoot(sc, cam, "close_right", (TW * 0.25, front - 0.8, 1.6), (TW * 0.3, front + TD * 0.4, look_h + 0.1), lens=28)
    shoot(sc, cam, "close_left", (-TW * 0.25, front - 0.8, 1.6), (-TW * 0.3, front + TD * 0.4, look_h - 0.1), lens=28)
    # orthographic front with a 0.1 m grid (green every 0.5 m) to read positions off
    fig.hide_render = True
    grid(TW / 2 + 0.3, h + 0.2)
    sc.render.resolution_x, sc.render.resolution_y = 1600, int(1600 * (h + 0.4) / (TW + 0.6))
    shoot(sc, cam, "ortho_front_grid", (0, -(TD / 2 + 5), (h + 0.2) / 2), (0, 0, (h + 0.2) / 2), ortho=TW + 0.6)


def B(u):
    """Unity local point -> Blender."""
    return Vector((-u[0], -u[2], u[1]))


def add_screen(man, xs):
    """The authored screen overlay (emissive quad), the light point (cyan dot) and the use point (floor disc)."""
    s = man["screen"]
    sm = bpy.data.materials.new("screen"); sm.use_nodes = True
    nt = sm.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(ROOT / "unity/AthenHill" / s["texture"]))
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); nt.links.new(t.outputs[0], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.6; b.inputs["Roughness"].default_value = 0.15
    dm = bpy.data.materials.new("dot"); dm.use_nodes = True
    dm.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (0.2, 0.9, 1, 1)
    dm.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 8
    um = bpy.data.materials.new("use"); um.use_nodes = True
    um.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.8, 0.1, 1)
    for x in xs:
        w, h = s["quad_size"]
        bpy.ops.mesh.primitive_plane_add(size=1)
        q = bpy.context.active_object; q.scale = (w, h, 1)
        n, up = B(s["normal"]), B(s["up"])
        rot = n.to_track_quat("Z", "Y")
        q.rotation_euler = rot.to_euler()
        q.location = B(s["center"]) + Vector((x, 0, 0))
        q.data.materials.append(sm)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.015, location=B(man["light_point"]) + Vector((x, 0, 0)))
        bpy.context.active_object.data.materials.append(dm)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.01, location=B(man["use_point"]) + Vector((x, 0, 0.005)))
        bpy.context.active_object.data.materials.append(um)


def lods():
    clear()
    global TW, TD
    man = json.loads((UNITY_PROPS / "salvage-shop-props.json").read_text())[PROP]
    TW, TD = man["size"][0], man["size"][2]
    d = UNITY_PROPS / PROP
    objs = {}
    for i in (0, 1):
        o = import_glb(d / f"{PROP}_LOD{i}.glb")
        objs[i] = o
    mat = bpy.data.materials.new("review"); mat.use_nodes = True
    nt = mat.node_tree; b = nt.nodes["Principled BSDF"]

    def tex(path, non_color):
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = bpy.data.images.load(str(path))
        if non_color:
            n.image.colorspace_settings.name = "Non-Color"
        return n
    base = tex(d / man["maps"]["BaseColor"], False); nt.links.new(base.outputs[0], b.inputs["Base Color"])
    mask = tex(d / man["maps"]["Mask"], True)
    sep = nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(mask.outputs[0], sep.inputs[0])
    nt.links.new(sep.outputs[0], b.inputs["Metallic"])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
    nt.links.new(mask.outputs[1], inv.inputs[1]); nt.links.new(inv.outputs[0], b.inputs["Roughness"])
    nrm = tex(d / man["maps"]["Normal"], True)
    nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(nrm.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    for i, os_ in objs.items():
        for o in mesh_objects(os_):
            o.data.materials.clear(); o.data.materials.append(mat)
            o.location.x += (i - 0.5) * (TW + 0.6)
    if "screen" in man:
        add_screen(man, [(i - 0.5) * (TW + 0.6) for i in objs])
    sc, cam = scene_setup()
    h = man["size"][1]
    figure(0)
    span = 2 * TW + 0.6
    shoot(sc, cam, "lods_three_quarter", (-span * 0.35, -span * 1.1, h * 0.8 + 0.6), (0, 0, h * 0.45))
    shoot(sc, cam, "lods_far", (-span * 1.1, -span * 3.2, h + 1.5), (0, 0, h * 0.45), lens=50)
    for i in (0, 1):
        x = (i - 0.5) * (TW + 0.6)
        if "use_point" in man:
            # the player's view from the use point (eye 1.62 m), looking at the worktop centre
            eye = B(man["use_point"]) + Vector((x, 0, 1.62)); tgt = B(man["worktop_centre"]) + Vector((x, 0, 0.15))
            shoot(sc, cam, f"lod{i}_use_view", eye, tgt, lens=24)
            shoot(sc, cam, f"lod{i}_close_screen", eye + Vector((0.35, 0.25, -0.2)), B(man["screen"]["center"]) + Vector((x, 0, 0)), lens=35)
            shoot(sc, cam, f"lod{i}_oblique", B(man["use_point"]) + Vector((x - 1.3, 0.1, 1.5)), B(man["worktop_centre"]) + Vector((x + 0.3, 0, 0.3)), lens=28)
        else:
            front = -man["size"][2] / 2
            shoot(sc, cam, f"lod{i}_close", (x + 0.15, front - 0.8, 1.6), (x + 0.05, front + man["size"][2] * 0.4, min(h * 0.6, 1.2)), lens=28)


{"source": source, "lods": lods}[MODE]()
