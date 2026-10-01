"""Ward hydroponics: review renders of the yard props (Cycles CPU). Lays every prop's LOD (default 0) out in rows on a
sand ground with a 1.8 m figure, renders front-left and back-right views per row. Writes review/props_<lod>_<row>_<view>.png.

Run: $O/blender.sh review_props.py [-- lod=0 samples=24 only=a,b]
"""
import sys, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ARGS = dict(a.split("=") for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if "=" in a)
LOD = int(ARGS.get("lod", 0))
ONLY = [s for s in ARGS.get("only", "").split(",") if s]
bpy.ops.wm.open_mainfile(filepath=str(HERE / "hydroponics-props.blend"))
sc = bpy.context.scene
obs = []
for o in list(bpy.data.objects):
    keep = o.type == "MESH" and o.name.endswith(f"_LOD{LOD}") and (not ONLY or any(o.name == f"HY_{p}_LOD{LOD}" for p in ONLY))
    o.hide_render = not keep; o.hide_set(not keep)
    if keep: obs.append(o)
obs.sort(key=lambda o: o.name)
SDPH = Path("/home/teknetik/code/ao2/art/street_dressing_20260930/polyhaven/models")
holders = {}


def holder(o):
    """Fills are reviewed inside the street kit's scanned crate / basket (merged, footprint-centred like the kit)."""
    model = "plastic_crate_02" if "fill_crate" in o.name else "wicker_basket_01" if "fill_basket" in o.name else None
    if not model: return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(next((SDPH / model).glob("*.gltf"))))
    new = [x for x in bpy.data.objects if x not in before and x.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for x in new:
        x.select_set(True)
        if x.parent:
            mw = x.matrix_world.copy(); x.parent = None; x.matrix_world = mw
    bpy.context.view_layer.objects.active = new[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(new) > 1: bpy.ops.object.join()
    h = bpy.context.view_layer.objects.active
    vs = [v.co for v in h.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))); mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    from mathutils import Matrix
    h.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    return h


for o in obs:
    h = holder(o)
    if h: holders[o.name] = h


def dims(o):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    return mn, mx


# rows of up to 5, spaced by size (Blender X right, -Y towards the camera)
rows = [obs[i:i + 5] for i in range(0, len(obs), 5)]
PER = 5
centres = []
for r, row in enumerate(rows):
    x = 0.0
    for o in row:
        mn, mx = dims(o)
        w = mx.x - mn.x
        if o.name in holders:   # fill: keep its authored height inside the container; centre both on the slot
            o.location = Vector((x + w / 2, r * 6.0, 0)); holders[o.name].location = o.location
        else:
            o.location = Vector((x - mn.x + o.location.x, r * 6.0 - (mn.y + mx.y) / 2 + o.location.y, -mn.z + o.location.z))
        x += w + .9
    centres.append((x / 2, r * 6.0))


def flat(name, rgb, rough=.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=60)
me = bpy.data.meshes.new("ground"); bm.to_mesh(me); g = bpy.data.objects.new("ground", me); sc.collection.objects.link(g)
me.materials.append(flat("rv_ground", (.55, .45, .33), .9))
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.55, .62, .75, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .9
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 4.0; sun.rotation_euler = (math.radians(42), math.radians(8), math.radians(210))
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = int(ARGS.get("samples", 24))
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.view_settings.view_transform = "AgX"
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 35; cam.data.clip_start = .05
out = HERE / "review"; out.mkdir(exist_ok=True)
for r, (cx, cy) in enumerate(centres):
    xw = cx * 2
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=.2, radius2=.16, depth=1.8)
    me = bpy.data.meshes.new(f"fig{r}"); bm.to_mesh(me); f = bpy.data.objects.new(f"fig{r}", me); sc.collection.objects.link(f)
    me.materials.append(flat("rv_fig", (.6, .15, .1))); f.location = (xw + .4, cy + 1.2, .9)
    d = max(2.2, xw * .62)
    hgt = float(ARGS.get("h", 1.65))
    for view, eye in (("front", Vector((cx - xw * .12, cy - d, hgt))), ("back", Vector((cx + xw * .12, cy + d, hgt)))):
        cam.location = eye
        dv = Vector((cx, cy, .3)) - eye
        cam.rotation_euler = dv.to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(out / f"props_lod{LOD}_row{r}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", r, view, [o.name for o in rows[r]], flush=True)
