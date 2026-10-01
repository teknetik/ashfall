"""Planting for the hill beds and the tree ring, Blender 5.2 headless (30 September 2026).

Replaces the four procedural Hill grass patches and the 26 low-poly Hill weathered stones with CC0 Poly Haven plants
and stones (polyhaven/manifest.json): an irrigated oasis bed of medium grasses with succulent drifts (Cheiridopsis),
ice plant and small flowering weeds along the kerbs, a few Othonna shrubs as accents, scattered Namaqualand stones and
two feature boulders; inside the ring, bark litter, fallen twigs, stones and a few weeds by the wall.

Placement is deterministic (seeded Poisson disc per bed polygon from ward-hill.json, density and species driven by
low-frequency noise so plants read as drifts, clear of the terminals, stepping stones, Linn and the community board).
Heights come from hill_layout.bed_y / ring_soil_y, the same functions that shaped the soil.

Run:  blender -b --python-exit-code 1 -P scatter_hill_plants.py
Output: Art/WardHill/Models/HillPlants_LOD0.glb, HillPlants_LOD1.glb (one object per zone, one submesh per species
material, object origin at the zone's soil level so the ground-cover shader bends by height above the soil) and
Art/WardHill/Models/hill-plants.json.
"""
import bpy, bmesh, json, math, random, sys
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import hill_layout as H

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/WardHill/Models"
PH = HERE / "polyhaven/models"


def U(p):
    return Vector((-p[0], -p[2], p[1]))


# species: (model, object suffixes, decimate ratio for LOD0, LOD1 ratio, scale range)
SPECIES = {
    "grass2": ("grass_medium_02", ["a", "b", "c", "d", "e"], 0.26, 0.12, (1.1, 1.75)),
    "grass1": ("grass_medium_01", ["tall_a", "tall_b", "tall_c", "mid_b", "mid_c", "small_a", "small_b"], 0.32, 0.15, (1.15, 1.85)),
    "succulent": ("cheiridopsis_succulent", ["a", "b", "c", "d", "e", "f", "g"], 0.16, 0.06, (0.85, 1.25)),
    "iceplant": ("crystalline_iceplant", ["a", "b", "c", "d", "e"], 0.4, 0.16, (0.9, 1.4)),
    "celandine": ("celandine_01", ["a", "b", "e"], 1.0, 0.4, (0.9, 1.3)),
    "weed": ("weed_plant_02", ["a", "b", "c", "d"], 0.45, 0.18, (0.9, 1.4)),
    "shrub": ("othonna_cerarioides", ["d", "e", "f", "g"], 0.3, 0.1, (0.85, 1.1)),
    "stone": ("namaqualand_stones_01", ["a", "b", "c", "d", "e"], 0.05, 0.015, (1.2, 2.6)),
    "boulder": ("namaqualand_boulder_05", [""], 0.06, 0.015, (0.55, 0.7)),
    "bark": ("bark_debris_01", ["a", "b", "c", "d"], 0.022, 0.008, (0.8, 1.2)),
    "twig": ("dry_branches_medium_01", ["a", "b", "c"], 0.2, 0.08, (0.55, 0.85)),
}
CASTERS = {"boulder", "shrub", "twig"}   # everything else is ground cover: receives shadows, casts none


def load_sources():
    """Import every model once; returns {key: [mesh datablocks per variant]} with meshes in Unity-local metres (y up)."""
    src = {}
    for key, (model, variants, *_r) in SPECIES.items():
        before = set(bpy.data.objects)
        g = next((PH / model).glob("*.gltf"))
        bpy.ops.import_scene.gltf(filepath=str(g))
        objs = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
        meshes = []
        for v in variants:
            cand = [o for o in objs if (o.name.startswith(f"{model}_{v}") if v else True)]
            cand = [o for o in cand if "LOD1" not in o.name and "LOD2" not in o.name and "LOD3" not in o.name] or cand
            if not cand:
                print("missing variant", model, v, [o.name for o in objs])
                continue
            o = sorted(cand, key=lambda o: len(o.name))[0]
            me = o.data.copy()
            # bake the object transform, centre on the footprint, base at 0
            me.transform(o.matrix_world)
            xs = [p.co.x for p in me.vertices]
            ys = [p.co.y for p in me.vertices]
            zs = [p.co.z for p in me.vertices]
            me.transform(Matrix.Translation((-(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2, -min(zs))))
            meshes.append(me)
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        src[key] = meshes
        print(key, len(meshes), "variants", flush=True)
    return src


def decimated(me, ratio, name):
    if ratio >= 0.999:
        return me.copy()
    ob = bpy.data.objects.new(name, me.copy())
    bpy.context.scene.collection.objects.link(ob)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    d = ob.modifiers.new("d", "DECIMATE")
    d.ratio = ratio
    d.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier="d")
    out = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def point_in_poly(x, z, poly):
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < (x2 - x1) * (z - z1) / (z2 - z1 + 1e-12) + x1:
            inside = not inside
    return inside


def dist_to_poly_edge(x, z, poly):
    best = 9.0
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        dx, dz = bx - ax, bz - az
        t = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz + 1e-12)))
        best = min(best, math.hypot(x - ax - dx * t, z - az - dz * t))
    return best


def poisson(poly, rng, rmin, tries=26, accept=lambda x, z, r: True):
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    pts = []
    cell = rmin / math.sqrt(2)
    grid = {}
    n = int((x1 - x0) * (z1 - z0) / (rmin * rmin) * 2.2)
    for _ in range(n * tries // 6):
        x, z = rng.uniform(x0, x1), rng.uniform(z0, z1)
        if not point_in_poly(x, z, poly):
            continue
        r = rmin * (0.75 + 0.6 * (0.5 + 0.5 * H.vnoise(x, z, 0.55, 21)))   # density drifts
        gx, gz = int((x - x0) / cell), int((z - z0) / cell)
        ok = True
        for ix in range(gx - 3, gx + 4):
            for iz in range(gz - 3, gz + 4):
                for (px, pz, pr) in grid.get((ix, iz), ()):
                    if math.hypot(px - x, pz - z) < min(r, pr):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok or not accept(x, z, r):
            continue
        grid.setdefault((gx, gz), []).append((x, z, r))
        pts.append((x, z, r))
    return pts


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rec_hill = json.loads((OUT / "ward-hill.json").read_text())
    beds = {b["name"]: [tuple(p) for p in b["polygon"]] for b in rec_hill["beds"]}
    excl = [tuple(e) for e in rec_hill["exclusions"]]
    src = load_sources()
    # per-LOD variant meshes
    lod_mesh = {0: {}, 1: {}}
    for key, (model, variants, r0, r1, _s) in SPECIES.items():
        for vi, me in enumerate(src[key]):
            lod_mesh[0][(key, vi)] = decimated(me, r0, f"{key}{vi}L0")
            lod_mesh[1][(key, vi)] = decimated(me, r1, f"{key}{vi}L1")

    rng = random.Random(20260930)
    placements = {}   # zone -> list of (key, variant, x, y, z, yaw, scale, tilt, lod1)

    def clear(x, z, r):
        return all(math.hypot(x - ex, z - ez) > er + r * 0.4 for ex, ez, er in excl)

    for bname, poly in beds.items():
        pl = []
        # two feature boulders in the larger beds, before anything else
        if bname in ("bed_east", "bed_southwest"):
            spots = [(-5.7, 3.6, 38.0)] if bname == "bed_east" else [(5.4, 5.2, -120.0)]
            for (bx, bz, yaw) in spots:
                pl.append(("boulder", 0, bx, H.bed_y(bx, bz) - 0.12, bz, yaw, 0.62, 0.0, True))
                excl.append((bx, bz, 0.75))
        pts = poisson(poly, rng, 0.33, accept=lambda x, z, r: clear(x, z, r) and dist_to_poly_edge(x, z, poly) > 0.07)
        for (x, z, r) in pts:
            edge = dist_to_poly_edge(x, z, poly)
            patch = H.vnoise(x, z, 0.45, 31)       # succulent drifts in an irrigated grass bed
            roll = rng.random()
            if edge < 0.3 and roll < 0.3:
                key = rng.choice(["iceplant", "celandine", "weed", "succulent"])
            elif patch > 0.5 and roll < 0.65:
                key = "succulent" if roll < 0.5 else "iceplant"
            elif roll < 0.035:
                key = "stone"
            elif roll < 0.07:
                key = "celandine"
            else:
                key = "grass2" if rng.random() < 0.6 else "grass1"
            vi = rng.randrange(len(src[key]))
            s0, s1 = SPECIES[key][4]
            sc = rng.uniform(s0, s1)
            y = H.bed_y(x, z) - (0.02 if key not in ("stone",) else 0.01)
            tilt = rng.uniform(-6, 6) if key.startswith("grass") else rng.uniform(-3, 3)
            lod1 = key in ("grass2", "succulent", "shrub", "boulder") or (key == "grass1" and rng.random() < 0.5)
            pl.append((key, vi, x, y, z, rng.uniform(0, 360), sc, tilt, lod1))
        # a few Othonna shrubs as accents away from paths
        shrub_spots = {"bed_east": [(-6.0, -1.5), (-4.4, 5.8), (-6.1, -2.9)], "bed_southwest": [(6.0, 3.1), (3.3, 6.0)],
                       "bed_northwest": [(6.0, -5.9), (2.6, -6.0)]}[bname]
        for (sx, sz) in shrub_spots:
            if point_in_poly(sx, sz, poly) and clear(sx, sz, 0.5):
                # remove small plants under the shrub
                pl = [p for p in pl if math.hypot(p[2] - sx, p[4] - sz) > 0.45 or p[0] == "boulder"]
                pl.append(("shrub", rng.randrange(len(src["shrub"])), sx, H.bed_y(sx, sz) - 0.03, sz, rng.uniform(0, 360), rng.uniform(0.85, 1.05), 0.0, True))
        placements[bname] = pl

    # ring interior: litter, twigs, stones, weeds by the wall; keep a clear band round the trunk and roots' root collar
    pl = []
    ring_poly = [(H.RING_C[0] + (H.RI - 0.08) * math.cos(2 * math.pi * i / 64), H.RING_C[1] + (H.RI - 0.08) * math.sin(2 * math.pi * i / 64)) for i in range(64)]
    pts = poisson(ring_poly, rng, 0.42, accept=lambda x, z, r: math.hypot(x - H.TRUNK_C[0], z - H.TRUNK_C[1]) > 1.0 and clear(x, z, r))
    for (x, z, r) in pts:
        rad = math.hypot(x - H.RING_C[0], z - H.RING_C[1])
        roll = rng.random()
        if rad > H.RI - 0.45 and roll < 0.45:
            key = rng.choice(["weed", "celandine", "weed", "iceplant"])
        elif roll < 0.55:
            key = "bark"
        elif roll < 0.68:
            key = "twig"
        elif roll < 0.82:
            key = "stone"
        else:
            continue
        vi = rng.randrange(len(src[key]))
        s0, s1 = SPECIES[key][4]
        y = H.ring_soil_y(x, z) - (0.03 if key in ("bark", "twig") else 0.015)
        pl.append((key, vi, x, y, z, rng.uniform(0, 360), rng.uniform(s0, s1), rng.uniform(-4, 4), key in ("bark", "twig", "weed")))
    placements["ring"] = pl

    # zone objects: origin at the zone's nominal soil level (the ground-cover shader bends by height above it)
    # the long bed on the stairless side is split in two so each half drops detail and culls on its own
    east = placements.pop("bed_east")
    placements["bed_east_north"] = [p for p in east if p[4] < 0]
    placements["bed_east_south"] = [p for p in east if p[4] >= 0]
    zone_base = {"bed_east_north": H.BED_Y, "bed_east_south": H.BED_Y, "bed_southwest": H.BED_Y, "bed_northwest": H.BED_Y, "ring": H.SOIL_EDGE + 0.05}
    report = {"source": "art/hill_20260930/scatter_hill_plants.py", "date": "2026-09-30", "zones": {}, "lods": {}}
    for lod in (0, 1):
        objs = []
        for zone, pl_all in placements.items():
          for group in ("cover", "cast"):
              pl = [p for p in pl_all if (p[0] in CASTERS) == (group == "cast")]
              if not pl:
                  continue
              base = zone_base[zone]
              bm = bmesh.new()
              mats = []
              count = 0
              for (key, vi, x, y, z, yaw, sc, tilt, lod1) in pl:
                  if lod == 1 and not lod1:
                      continue
                  me = lod_mesh[lod][(key, vi)]
                  # Blender space: mesh z up; Unity (x, y, z) -> Blender (-x, -z, y); origin at base
                  M = (Matrix.Translation(U((x, y - base, z))) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @
                       Matrix.Rotation(math.radians(tilt), 4, "X") @ Matrix.Scale(sc, 4))
                  tmp = me.copy()
                  tmp.transform(M)
                  off = len(mats)
                  for m in tmp.materials:
                      if m.name not in mats:
                          mats.append(m.name)
                  remap = [mats.index(m.name) for m in tmp.materials]
                  bm_t = bmesh.new()
                  bm_t.from_mesh(tmp)
                  for f in bm_t.faces:
                      f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
                  bm_t.to_mesh(tmp)
                  bm_t.free()
                  bm.from_mesh(tmp)
                  bpy.data.meshes.remove(tmp)
                  count += 1
              me = bpy.data.meshes.new(f"HillPlants_{zone}_{group}_LOD{lod}")
              bm.to_mesh(me)
              bm.free()
              for mname in mats:
                  me.materials.append(bpy.data.materials.get(mname))
              ob = bpy.data.objects.new(f"HillPlants_{zone}_{group}_LOD{lod}", me)
              ob.location = U((0, base, 0))
              bpy.context.scene.collection.objects.link(ob)
              objs.append(ob)
              report["zones"].setdefault(f"{zone}_{group}", {})[f"LOD{lod}"] = {"instances": count, "triangles": sum(len(p.vertices) - 2 for p in me.polygons),
                                                                   "materials": mats}
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.export_scene.gltf(filepath=str(OUT / f"HillPlants_LOD{lod}.glb"), export_format="GLB", use_selection=True,
                                  export_yup=True, export_image_format="NONE", export_tangents=True, export_normals=True,
                                  export_apply=True, export_materials="EXPORT", export_vertex_color="NONE")
        report["lods"][f"LOD{lod}"] = sum(z[f"LOD{lod}"]["triangles"] for z in report["zones"].values())
        print(f"HillPlants LOD{lod}", report["lods"][f"LOD{lod}"], flush=True)
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    report["species_counts"] = {}
    for zone, pl in placements.items():
        for p in pl:
            report["species_counts"][p[0]] = report["species_counts"].get(p[0], 0) + 1
    report["materials"] = sorted({m for z in report["zones"].values() for l in z.values() for m in l["materials"]})
    (OUT / "hill-plants.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":   # importable for its helpers (art/courtyard_trees_20260930)
    main()
