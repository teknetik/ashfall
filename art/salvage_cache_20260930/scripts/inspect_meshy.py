"""Blender 5.2 (CPU Cycles only): inspect a raw Meshy salvage-cache GLB before any cleanup.
Reports triangles, bounds, loose parts (floaters), non-manifold/boundary edges and texture sizes, then renders
front/right/back/left/top/3-4 views (textured) and a clay pass so geometry defects are not hidden by the texture.
Run: blender -b --factory-startup --python inspect_meshy.py -- meshy/run_a/model.glb review/inspect_run_a
"""
import bpy, bmesh, sys, json, math
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = Path(argv[0]).resolve(), Path(argv[1]).resolve()
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SRC))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
rep = {"source": str(SRC), "objects": []}
allco = []
for o in meshes:
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(o.matrix_world)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)  # glTF splits vertices at UV/normal seams
    bm.verts.ensure_lookup_table()
    # loose parts
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; comp = []; seen.add(v.index)
        while stack:
            x = stack.pop(); comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); stack.append(y)
        parts.append(comp)
    parts.sort(key=len, reverse=True)
    part_info = []
    for comp in parts[:40]:
        cs = [v.co for v in comp]
        mn = Vector((min(c.x for c in cs), min(c.y for c in cs), min(c.z for c in cs)))
        mx = Vector((max(c.x for c in cs), max(c.y for c in cs), max(c.z for c in cs)))
        part_info.append({"verts": len(comp), "min": [round(x, 4) for x in mn], "max": [round(x, 4) for x in mx]})
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    allco += [v.co.copy() for v in bm.verts]
    imgs = []
    for m in me.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    imgs.append({"node": n.label or n.name, "image": n.image.name, "size": list(n.image.size),
                                 "colorspace": n.image.colorspace_settings.name})
    rep["objects"].append({"name": o.name, "tris": tris, "verts": len(bm.verts), "loose_parts": len(parts),
                           "largest_parts": part_info, "non_manifold_edges": nonman, "boundary_edges": boundary,
                           "materials": [m.name for m in me.materials if m], "uv_layers": [u.name for u in me.uv_layers],
                           "images": imgs})
    bm.free()
mn = Vector((min(c.x for c in allco), min(c.y for c in allco), min(c.z for c in allco)))
mx = Vector((max(c.x for c in allco), max(c.y for c in allco), max(c.z for c in allco)))
rep["bounds_min"], rep["bounds_max"] = [round(x, 4) for x in mn], [round(x, 4) for x in mx]
rep["dims"] = [round(x, 4) for x in (mx - mn)]
(OUT / "inspect.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({k: v for k, v in rep.items() if k != "objects"}), [(o["name"], o["tris"], o["loose_parts"], o["non_manifold_edges"], o["boundary_edges"]) for o in rep["objects"]], flush=True)

# --- render setup (CPU Cycles) ---
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.render.resolution_x = sc.render.resolution_y = 768
sc.view_settings.view_transform = "AgX"
world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.64, 0.68, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.data.energy = 3.0; sun.rotation_euler = (math.radians(40), 0, math.radians(35)); sun.data.angle = math.radians(3)
ctr = (mn + mx) / 2; size = max(mx - mn)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.25
def look(loc):
    cam.location = loc
    cam.rotation_euler = (ctr - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
d = size * 3
views = {"front": (0, -d, 0), "right": (d, 0, 0), "back": (0, d, 0), "left": (-d, 0, 0), "top": (0, -0.001, d),
         "q34": (-d * .6, -d * .7, d * .45), "q34b": (d * .6, d * .7, d * .45)}
def render_all(tag):
    for k, off in views.items():
        look(ctr + Vector(off)); sc.render.filepath = str(OUT / f"{tag}_{k}.png"); bpy.ops.render.render(write_still=True)
render_all("tex")
clay = bpy.data.materials.new("clay"); clay.use_nodes = True
clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
clay.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
for o in meshes:
    o.data.materials.clear(); o.data.materials.append(clay)
render_all("clay")
print("rendered", OUT)
