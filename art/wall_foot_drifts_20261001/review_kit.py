"""Blender (headless, Cycles) review of the wall-foot drift kit in context (1 October 2026).

Run:  $O/blender.sh review_kit.py -- <run> [views]       views: eye,close,corner,post,top (default all)

A 7 m ashlar wall (Vanguard Hall ashlar texture) on the city flag paving (PV_Flags_BaseMap, 4 m tile), a return wall for
the inside corner, a 0.52 m post footing and the eight kit pieces at LOD0 (WFD_Kit.glb as exported) with the sand
material (WFD_Sand_BaseMap / Normal, 1.5 m tile), lit by a sun from the west-south-west (the Ward's wind) at 55 degrees.
A 1.8 m figure for scale. Renders to review/<run>/<view>.png. Decals are judged in Unity, not here.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = ROOT / "unity/AthenHill/Assets/AthenHill/Art"
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
run = args[0] if args else "r1"
views = args[1].split(",") if len(args) > 1 else ["eye", "close", "corner", "post", "top"]
OUT = HERE / "review" / run
OUT.mkdir(parents=True, exist_ok=True)


def U(x, y, z):
    """Unity (x, y, z) -> Blender."""
    return Vector((-x, -z, y))


def tex_mat(name, base, normal=None, scale=1.0, rough=0.85, nstr=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / scale, 1 / scale, 1 / scale)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(str(base))
    nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if normal:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = bpy.data.images.load(str(normal))
        tn.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs["Vector"], tn.inputs["Vector"])
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nstr
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


def box(name, lo, hi, mat, uv_scale=1.0):
    """Axis-aligned box from Unity corners lo..hi with box-projected UVs in metres."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.name = name
    a, b = U(*lo), U(*hi)
    c = (a + b) / 2
    o.location = c
    o.scale = (abs(b.x - a.x), abs(b.y - a.y), abs(b.z - a.z))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.cube_project(cube_size=1.0 / uv_scale)
    bpy.ops.object.mode_set(mode="OBJECT")
    o.data.materials.append(mat)
    return o


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    paving = tex_mat("paving", ART / "CityPaving/Textures/PV_Flags_BaseMap.png", ART / "CityPaving/Textures/PV_Flags_Normal.png", 4.0, 0.8)
    ashlar = tex_mat("ashlar", ART / "VanguardHall/Textures/VH_Ashlar_BaseMap.jpg", ART / "VanguardHall/Textures/VH_Ashlar_Normal.jpg", 2.0, 0.85)
    sand = tex_mat("WFD_Sand_review", ART / "WallFootDrifts/Textures/WFD_Sand_BaseMap.png", ART / "WallFootDrifts/Textures/WFD_Sand_Normal.png",
                   1.5, 0.92, 1.0)
    # ground (UVs in metres from a 40 m plane)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    g = bpy.context.active_object
    for l in g.data.uv_layers.active.data:
        l.uv = (l.uv[0] * 40, l.uv[1] * 40)
    g.data.materials.append(paving)
    # wall along Unity +X with its face at z = 0 (city side +Z), a return wall at x = 3.6 running +Z, a post footing
    box("wall", (-4.0, 0.0, -0.8), (3.6, 3.2, 0.0), ashlar, 1.0)
    box("return", (3.6, 0.0, -0.8), (4.4, 3.2, 2.6), ashlar, 1.0)
    box("post_footing", (-2.26, 0.0, 2.24), (-1.74, 0.23, 2.76), ashlar, 1.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.09, depth=4.0, location=U(-2.0, 2.2, 2.5))
    # the kit, placed in Unity metres (x, y, z, yaw degrees, scale)
    bpy.ops.import_scene.gltf(filepath=str(ART / "WallFootDrifts/Models/WFD_Kit.glb"))
    objs = {o.name: o for o in bpy.data.objects if o.name.startswith("WFD_") and o.name.endswith("_LOD0")}
    for o in list(bpy.data.objects):
        if o.name.startswith("WFD_") and not o.name.endswith("_LOD0"):
            bpy.data.objects.remove(o, do_unlink=True)
    place = {"Run_L": (-3.0, 0.0, 0.0, 0.0, 1.15), "Run_M": (-1.35, 0.0, 0.0, 0.0, 1.0), "Run_S": (-0.35, 0.0, 0.0, 0.0, 1.0),
             "Run_Low": (1.0, 0.0, 0.0, 0.0, 1.0), "Corner_L": (3.6, 0.0, 0.0, 0.0, 1.0),
             "Post": (-2.0, 0.0, 2.5, 72.0, 1.0), "Sheet": (1.2, 0.0, 2.6, 8.0, 1.0), "Corner_S": (2.2, 0.0, 0.0, 0.0, 0.01)}
    # the corner piece: local +X along the wall (-X world here), +Z along the return (+Z) -> yaw so X = -world X
    place["Corner_L"] = (3.6, 0.0, 0.0, -90.0, 1.0)
    for k, o in objs.items():
        key = k[4:-5]
        x, y, z, yaw, s = place.get(key, (0, -5, 0, 0, 1))
        o.rotation_mode = "XYZ"
        # glTF import puts objects in Blender space already; place by world origin and Blender Z rotation (= -Unity yaw)
        o.location = U(x, y, z)
        o.rotation_euler = (o.rotation_euler[0], o.rotation_euler[1], math.radians(-yaw))
        o.scale = (s, s, s)
        o.data.materials.clear()
        o.data.materials.append(sand)
        if key == "Corner_S":
            o.hide_render = True
    # figure for scale
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.2, depth=1.8, location=U(-4.6, 0.9, 1.4))
    # light: sun from the west-south-west, 55 degrees up; sky
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 4.0
    sun.data.angle = math.radians(1.0)
    d = U(0.95, -1.4, 0.31).normalized()            # direction the light travels (Unity): towards +X, down, a little +Z
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.68, 0.9, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.view_settings.view_transform = "AgX"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    shots = {"eye": ((-0.6, 1.65, 4.2), (-1.4, 0.1, 0.2), 55), "close": ((-1.0, 1.0, 1.7), (-2.2, 0.05, 0.1), 55),
             "corner": ((1.6, 1.4, 2.6), (3.4, 0.05, 0.3), 55), "post": ((-0.6, 1.5, 4.6), (-1.95, 0.05, 2.7), 50),
             "top": ((0.0, 9.0, 1.6), (0.0, 0.0, 1.4), 60)}
    for v in views:
        pos, tgt, fov = shots[v]
        cam.location = U(*pos)
        cam.data.angle = math.radians(fov)
        cam.rotation_euler = (U(*tgt) - U(*pos)).to_track_quat("-Z", "Y").to_euler()
        sc.render.filepath = str(OUT / f"{v}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", v)


main()
