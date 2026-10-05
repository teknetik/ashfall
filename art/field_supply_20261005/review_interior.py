"""Source review renders of the walk-in Field Supply (Blender 5.2, Cycles on the CPU; not the game's render).

Run:  blender.sh art/field_supply_20261005/review_interior.py [-- views=a,b]
Imports Art/WardShops/Models/FieldSupply_LOD0.glb with the north avenue preview shading, puts the cover atlas on the
magazine screens, hangs the Meshy packs (meshy/field-supply-20261005/props) on the pack wall's top hooks, adds the
pendant lamps and a 1.8 m marker, and renders review/<view>.png. Views are in shop-local Unity metres (facade faces +Z).
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NA = ROOT / "art/north_avenue_20260930"
src = (NA / "review_north.py").read_text().replace("\nmain()\n", "\n")
ns = {"__file__": str(NA / "review_north.py"), "__name__": "review_north"}
exec(compile(src, str(NA / "review_north.py"), "exec"), ns)
ns["TINTS"].update({"SS_Timber": (0.36, 0.25, 0.16), "SS_Boards": (0.42, 0.3, 0.19), "SS_Enamel": (0.85, 0.84, 0.8),
                    "SS_BulbWarm": (1.0, 0.75, 0.45), "FS_MedRed": (0.55, 0.08, 0.06), "FS_MedOlive": (0.25, 0.28, 0.16),
                    "FS_MedWhite": (0.85, 0.85, 0.82), "FS_NanoGlow": (0.25, 0.9, 1.0), "FS_Amber": (0.8, 0.5, 0.1),
                    "FS_Felt": (0.06, 0.16, 0.17), "FS_Canvas": (0.55, 0.45, 0.3), "FS_Webbing": (0.42, 0.38, 0.26),
                    "FS_CaseGlass": (0.6, 0.7, 0.72), "FS_Screens": (1, 1, 1)})
ns["EMIT"].update({"SS_BulbWarm", "FS_NanoGlow"})
ns["OUT"] = HERE / "review"
ns["OUT"].mkdir(exist_ok=True)
U = ns["U"]
PROPS = ROOT / "meshy/field-supply-20261005/props"

VIEWS = {
    "bay_in": ((-0.6, 1.65, 3.2), (-0.6, 1.4, -5.0), 22),
    "counter": ((-1.6, 1.65, -1.3), (2.2, 1.35, -2.8), 20),
    "pack_wall": ((-0.2, 1.65, -2.4), (-1.3, 1.6, -6.4), 20),
    "shelf": ((-1.2, 1.65, -1.0), (-3.3, 1.6, -2.1), 18),
    "cabinet": ((1.9, 1.65, -1.2), (3.3, 1.5, -2.9), 18),
    "inside_out": ((1.2, 1.65, -5.6), (-0.8, 1.8, 0.0), 20),
    "keeper_view": ((2.6, 1.6, -3.4), (-1.5, 1.3, -1.0), 18),
}


def screens_material(mat):
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(HERE / "covers/magazine_atlas.png"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.4
    bsdf.inputs["Roughness"].default_value = 0.25


def hang(path, hook, height):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    pivot = bpy.data.objects.new("pack", None)
    bpy.context.scene.collection.objects.link(pivot)
    for r in roots:
        r.parent = pivot
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = height / max(1e-4, hi.z - lo.z)
    pivot.scale = (s, s, s)
    # Blender: +Z up; Unity (x, y, z) -> (-x, -z, y). Hook in Unity coords; the pack's back to the wall (Unity -z = Blender +y)
    hx, hy, hz = hook
    c = (lo + hi) / 2
    pivot.location = U((hx, hy + 0.06, hz)) - Vector((c.x * s, hi.y * s - 0.0, hi.z * s))
    return pivot


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    views = [a[6:] for a in args if a.startswith("views=")]
    names = views[0].split(",") if views else list(VIEWS)
    sc = ns["setup"]("FieldSupply")
    sc.cycles.samples = 40
    for m in bpy.data.materials:
        if m.name.startswith("prev_FS_Screens"):
            screens_material(m)
        if m.name.startswith("prev_FS_CaseGlass"):
            b = m.node_tree.nodes["Principled BSDF"]
            b.inputs["Alpha"].default_value = 0.08
            b.inputs["Roughness"].default_value = 0.05
    rec = json.loads((ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models/field_supply.json").read_text())
    for lamp in rec["interior"]["lamps"]:
        x, y, z = lamp["pos"]
        L = bpy.data.objects.new(lamp["name"], bpy.data.lights.new(lamp["name"], "POINT"))
        L.data.energy = 170
        L.data.color = (1.0, 0.78, 0.55)
        L.data.shadow_soft_size = 0.05
        L.location = U((x, y - 0.06, z))
        sc.collection.objects.link(L)
    hooks = {h["name"]: h["pos"] for h in rec["interior"]["pack_hooks"]}
    for name, hook, h in (("pack_rucksack", "top_0", 0.62), ("pack_frame", "top_1", 0.78), ("pack_carrier", "top_2", 0.7),
                          ("pack_rig", "top_3", 0.62), ("pack_field", "low_0", 0.52)):
        p = PROPS / name / "model.glb"
        if p.exists() and hook in hooks:
            hang(p, hooks[hook], h)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.8, location=U((0.4, 0.5 + 0.9, -2.7)))
    for v in names:
        eye, tgt, lens = VIEWS[v]
        ns["shoot"](sc, "fieldsupply_" + v, eye, tgt, lens)


main()
