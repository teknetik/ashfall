"""Source review renders of the walk-in Salvage shop (Blender 5.2, Cycles on the CPU; not the game's render).

Run:  blender.sh review_interior.py [-- views=a,b]
Imports Art/WardShops/Models/Salvage_LOD0.glb with the north avenue preview shading (vertex colour x tint for the
masonry, flat tints elsewhere), adds the three pendant lamps as point lights and a 1.8 m marker inside, and renders
review/<view>.png. Views are in shop-local Unity metres (facade faces +Z).
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.argv = [a for a in sys.argv]
NA = ROOT / "art/north_avenue_20260930"
src = (NA / "review_north.py").read_text().replace("\nmain()\n", "\n")
ns = {"__file__": str(NA / "review_north.py"), "__name__": "review_north"}
exec(compile(src, str(NA / "review_north.py"), "exec"), ns)
ns["TINTS"].update({"SS_Timber": (0.36, 0.25, 0.16), "SS_Boards": (0.42, 0.3, 0.19), "SS_Enamel": (0.85, 0.84, 0.8),
                    "SS_BulbWarm": (1.0, 0.75, 0.45), "WS_CladTeal": (0.3, 0.45, 0.46)})
ns["EMIT"].add("SS_BulbWarm")
ns["OUT"] = HERE / "review"
ns["OUT"].mkdir(exist_ok=True)
U = ns["U"]

VIEWS = {
    "bay_in": ((-1.0, 1.65, 3.2), (-1.0, 1.4, -5.0), 22),
    "inside_counter": ((-1.9, 1.65, -1.1), (1.6, 1.25, -2.7), 20),
    "inside_bench": ((0.3, 1.65, -2.2), (-1.3, 1.3, -6.4), 22),
    "inside_out": ((0.6, 1.65, -5.7), (-1.3, 1.9, 0.0), 20),
    "ceiling": ((0.2, 1.6, -2.8), (0.6, 4.4, -4.6), 16),
    "rear_corner": ((-2.7, 1.65, -1.2), (2.7, 1.4, -6.2), 20),
    "door_jamb": ((0.9, 1.65, -1.6), (1.95, 2.2, -0.2), 20),
}


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    views = [a[6:] for a in args if a.startswith("views=")]
    names = views[0].split(",") if views else list(VIEWS)
    sc = ns["setup"]("Salvage")
    sc.cycles.samples = 48
    rec = json.loads((ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardShops/Models/salvage.json").read_text())
    for lamp in rec["interior"]["lamps"]:
        x, y, z = lamp["pos"]
        L = bpy.data.objects.new(lamp["name"], bpy.data.lights.new(lamp["name"], "POINT"))
        L.data.energy = 180
        L.data.color = (1.0, 0.78, 0.55)
        L.data.shadow_soft_size = 0.05
        L.location = U((x, y - 0.06, z))
        sc.collection.objects.link(L)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=1.8, location=U((-0.6, 0.5 + 0.9, -3.4)))
    for v in names:
        eye, tgt, lens = VIEWS[v]
        ns["shoot"](sc, "salvage_" + v, eye, tgt, lens)


main()
