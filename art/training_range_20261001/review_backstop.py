"""Blender review of the backstop revetment from the firing line (world-space asset; flat colours, survey ground).
Run: $O/blender.sh review_backstop.py"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ground as GR
SRC = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Structures/TR_Revetment.glb"
A = json.loads((HERE / "authored-assets.json").read_text())["TR_Revetment"]["origin"]
U = lambda x, y, z: Vector((-(x - A[0]), -(z - A[2]), y - A[1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
for o in bpy.data.objects:
    if o.type == "MESH" and (o.name.startswith("COL_") or "_LOD1" in o.name):
        o.hide_render = True
PAL = {"TimberDark": (.2, .14, .09), "Timber": (.4, .3, .2), "TimberFresh": (.6, .45, .28), "Hessian": (.55, .47, .33), "SandFill": (.62, .52, .38),
       "RustSteel": (.3, .18, .11), "LaneNumbersPaint": (.9, .88, .8)}
for m in bpy.data.materials:
    m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    k = m.name.split(".")[0].replace("TR_", "").replace("WG_", "")
    if b: b.inputs["Base Color"].default_value = (*PAL.get(k, (.5, .5, .5)), 1); b.inputs["Roughness"].default_value = .8
# survey ground as a mesh around the backstop
import bmesh
bm = bmesh.new(); vs = {}
for i in range(0, 61):
    for j in range(0, 61):
        x = -92 + i * .5; z = 2 + j * .5; y = GR.ground(x, z)
        vs[i, j] = bm.verts.new(U(x, y, z))
for i in range(60):
    for j in range(60):
        bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
me = bpy.data.meshes.new("ground"); bm.to_mesh(me); g = bpy.data.objects.new("ground", me); bpy.context.scene.collection.objects.link(g)
gm = bpy.data.materials.new("g"); gm.use_nodes = True; gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (.55, .45, .33, 1); me.materials.append(gm)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 24; sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = 1600; sc.render.resolution_y = 900
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.7, .74, .8, 1)
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.data.energy = 3.5; sun.rotation_euler = (math.radians(45), 0, math.radians(150))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 28
VIEWS = [("backstop_from_line", (-66.0, 0.2, 7.5), (-80.0, -0.4, 17.0)), ("backstop_close", (-77.0, 0.3, 12.5), (-82.5, -0.2, 16.0)),
         ("backstop_leftend", (-79.5, 0.2, 9.0), (-84.5, -0.3, 9.6))]
if len(sys.argv) > 1 and "--" in sys.argv:
    VIEWS = [v for v in VIEWS if v[0] in sys.argv[sys.argv.index("--") + 1:]]
for name, eye, tgt in VIEWS:
    cam.location = U(*eye); cam.rotation_euler = (U(*tgt) - U(*eye)).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = str(HERE / f"review/{name}.png"); bpy.ops.render.render(write_still=True)
