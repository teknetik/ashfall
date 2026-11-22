"""Headless Blender Cycles contact-sheet renderer for the processed SimReady asset library.

Renders category contact sheets (`review/sheet_<category>.png`) with a 1.80 m human scale reference
so an agent or artist can visually inspect proportions, grounding, and materials across all pulled assets.

Usage:
    env -i HOME=$HOME PATH=/usr/bin:/bin /Applications/Blender.app/Contents/MacOS/Blender \
        -b --factory-startup --python-exit-code 1 -P review_simready.py [-- category ...]
"""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ASSETS_DIR = HERE / "assets"
REVIEW_DIR = HERE / "review"


def render_category(cat, items):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    cols = 5 if len(items) <= 15 else 6
    sp = 2.2
    for i, meta in enumerate(items):
        aid = meta["id"]
        glb = ASSETS_DIR / aid / f"{aid}_LOD0.glb"
        if not glb.exists():
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(glb))
        new_objs = list(set(bpy.data.objects) - before)

        dims = meta["physical_properties"]["dimensions_m"]
        max_d = max(dims["width_x"], dims["height_y"], dims["depth_z"], 0.05)
        # Normalise display scale slightly in the contact sheet if tiny (< 0.25 m) so small tools are clearly legible,
        # while marking their real metric dimensions in the label below!
        disp_scale = 2.2 if max_d < 0.22 else (1.5 if max_d < 0.45 else (0.65 if max_d > 2.2 else 1.0))

        x = (i % cols) * sp
        y = -(i // cols) * sp * 1.35
        for o in new_objs:
            if o.parent is None:
                o.scale = (disp_scale, disp_scale, disp_scale)
                o.location = (x, y, 0.0)

        label_txt = f"{aid}\n{dims['width_x']:.2f}x{dims['height_y']:.2f}x{dims['depth_z']:.2f}m ({meta['geometry']['part_count']}p)"
        t = bpy.data.curves.new(aid + "_font", "FONT")
        t.body = label_txt
        t.size = 0.13
        t.align_x = "CENTER"
        to = bpy.data.objects.new(aid + "_label", t)
        bpy.context.scene.collection.objects.link(to)
        to.location = (x, y - 0.85, 0.003)

    lm = bpy.data.materials.new("label_mat")
    bsdf = lm.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.04, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    for o in bpy.data.objects:
        if o.name.endswith("_label"):
            o.data.materials.append(lm)

    # 1.8 m reference cylinder at top-left
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.22, depth=1.8, location=(-1.4, 0, 0.9))
    ref = bpy.context.active_object
    rm = bpy.data.materials.new("ref_mat")
    rm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.72, 0.38, 0.18, 1.0)
    ref.data.materials.append(rm)

    t = bpy.data.curves.new("ref_font", "FONT")
    t.body = "1.80m Hero\nScale Ref"
    t.size = 0.14
    t.align_x = "CENTER"
    to = bpy.data.objects.new("ref_label", t)
    bpy.context.scene.collection.objects.link(to)
    to.location = (-1.4, -0.85, 0.003)
    to.data.materials.append(lm)

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 20
    rows = (len(items) + cols - 1) // cols
    sc.render.resolution_x = 1920
    sc.render.resolution_y = max(900, min(1600, 340 * rows + 220))

    w = bpy.data.worlds.new("world")
    sc.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.76, 0.74, 0.70, 1.0)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.95

    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 3.8
    sun.rotation_euler = (math.radians(48), 0, math.radians(32))

    bpy.ops.mesh.primitive_plane_add(size=120, location=(6, -6, 0))
    g = bpy.context.active_object
    gm = bpy.data.materials.new("ground")
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.56, 0.48, 1.0)
    gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    g.data.materials.append(gm)

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cx = (cols - 1) * sp / 2.0 - 0.3
    cy = -(rows - 1) * sp * 1.35 / 2.0
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max((cols + 0.8) * sp, (rows + 0.6) * sp * 1.35 * (sc.render.resolution_x / sc.render.resolution_y) * 0.68)
    cam.location = (cx, cy - 10.0, 8.2)
    cam.rotation_euler = (Vector((cx, cy, 0.35)) - cam.location).to_track_quat("-Z", "Y").to_euler()

    out_png = REVIEW_DIR / f"sheet_{cat}.png"
    sc.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered {out_png}", flush=True)


def main():
    only = set(sys.argv[sys.argv.index("--") + 1 :]) if "--" in sys.argv else None
    cat_path = HERE / "catalog.json"
    if not cat_path.exists():
        sys.exit("catalog.json not found; run build_simready_pipeline.py first")
    catalog = json.loads(cat_path.read_text())
    by_cat = {}
    for a in catalog["assets"]:
        by_cat.setdefault(a["category"], []).append(a)
    for cat, items in sorted(by_cat.items()):
        if only and cat not in only:
            continue
        render_category(cat, items)


if __name__ == "__main__":
    main()
