"""Ward street dressing: Poly Haven props for Unity, Blender 5.2 headless (30 September 2026).

Every prop is one or more objects of a CC0 Poly Haven model (polyhaven/manifest.json) merged into one mesh, kept at its
scanned size (metres), rotated so its front faces Unity +Z, with its origin at the centre of its footprint on the ground.
LOD0 is the unreduced source; LOD1/LOD2 are collapse-decimated copies judged in Unity (they switch at 3-14 m and
14-60 m for a crate). Planted variants of the clay pot and the wooden planters get soil and the hill's Poly Haven plants
(art/hill_20260930/polyhaven), so doorways can carry a little care as well as stock.

Run:  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P prepare_ph_props.py [-- id ...]
Out:  unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props/<id>/<id>_LOD0..2.glb (no images; material names are the
      Poly Haven ones) and Art/StreetDressing/Props/ph-props.json (bounds, triangles, materials -> source maps).
      prepare_textures.py then writes the Unity maps (URP mask maps from the ARM maps) into Art/StreetDressing/Textures.
"""
import bpy, bmesh, json, math, random, sys, zlib
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PH = HERE / "polyhaven/models"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props"
sys.path.insert(0, str(ROOT / "art/hill_20260930"))

# id: (model, object-name filter (None = all meshes), yaw fix in degrees about up, LOD ratios, notes)
PROPS = {
    "drum_red": ("Barrel_01", None, 0, "steel drum, red paint, flammable pictogram"),
    "drum_blue": ("Barrel_02", None, 0, "blue poly water drum"),
    "drum_steel_blue": ("barrel_03", None, 0, "blue steel drum, dented"),
    "fire_barrel": ("barrel_stove", None, 0, "rusted burn barrel with vents"),
    "jerrycan_red": ("metal_jerrycan", None, 0, ""),
    "jerrycan_green": ("metal_jerrycan_green", None, 0, ""),
    "churn": ("metal_jug", None, 0, "milk/water churn"),
    "ammo_crate_a": ("old_military_crate", "_a", 0, "green steel-bound crate, lid closed"),
    "ammo_crate_b": ("old_military_crate", "_b", 0, "green steel-bound crate, lid ajar"),
    "crate_wood": ("wooden_crate_01", None, 0, "long wooden box with lid and latch"),
    "crate_wood_deep": ("wooden_crate_02", None, 90, "deep wooden crate with loose lid"),
    "crate_long": ("wooden_military_crate", None, 0, "long wooden transport crate"),
    "crate_yellow": ("plastic_crate_02", None, 0, "yellow stacking crate"),
    "crate_red": ("plastic_crate_03", None, 0, "red stacking crate"),
    "tote_blue": ("industrial_pastic_container", None, 0, "blue lidded tote, lids open"),
    "carton": ("cardboard_box_01", None, 0, "taped cardboard box"),
    "bucket_wood": ("wooden_bucket_01", None, 0, ""),
    "tub_wood": ("wooden_bucket_02", None, 0, "wide wooden tub"),
    "watering_can": ("watering_can_metal_01", None, 0, ""),
    "planter_long": ("planter_box_02", None, 0, "wooden planter, 1.25 m"),
    "planter_short": ("planter_box_01", None, 0, "wooden planter, 0.9 m"),
    "pot_clay": ("planter_pot_clay", None, 0, "terracotta pot"),
    "stool_folding": ("folding_wooden_stool", None, 0, ""),
    "stool_wood": ("wooden_stool_01", None, 0, ""),
    "stool_low": ("wooden_stool_02", None, 0, "low footstool"),
    "stool_painted": ("painted_wooden_stool", None, 0, ""),
    "stool_metal": ("metal_stool_02", None, 0, ""),
    "bench_painted": ("painted_wooden_bench", None, 0, ""),
    "broom": ("wooden_broom", None, 0, "yard broom, standing"),
    "dustpan": ("dustpan", None, 0, ""),
    "tyre": ("old_tyre", None, 0, "standing on its tread"),
    "rim_a": ("rusted_wheel_rim_01", None, 0, "standing on edge"),
    "rim_b": ("rusted_wheel_rim_02", None, 0, "standing on edge"),
    "gas_bottle": ("small_lpg_tank", None, 0, ""),
    "bin_galv": ("metal_trash_can", "plain", 0, "galvanised bin, lid leaning"),
    "bin_galv_rust": ("metal_trash_can", "rust", 0, "rusty galvanised bin, lid leaning"),
    "hand_truck": ("hand_truck", None, 0, "sack truck, upright"),
    "rack": ("worn_metal_rack", None, 0, "four-shelf steel rack"),
    "toolbox": ("metal_toolbox", None, 0, ""),
    "tool_cart": ("tool_cart", None, 0, "green workshop trolley"),
    "oil_tin": ("oil_tin", None, 0, ""),
    "basket_flat": ("wicker_basket_01", None, 0, ""),
    "basket_lidded": ("wicker_basket_02", None, 0, ""),
    "pot_enamel": ("pot_enamel_01", None, 0, "enamel cooking pot with lid"),
    "picnic_table": ("wooden_picnic_table", None, 0, "table with fixed benches"),
}
PLANTED = {   # id: (container prop, plant species mix, count range)
    "pot_clay_planted": ("pot_clay", ["succulent", "succulent", "iceplant"], (1, 2)),
    "pot_clay_planted_grass": ("pot_clay", ["grass2", "grass1", "grass2"], (4, 5)),
    "planter_long_planted": ("planter_long", ["grass2", "succulent", "celandine", "iceplant", "weed", "succulent"], (9, 12)),
    "planter_short_planted": ("planter_short", ["succulent", "iceplant", "celandine", "grass2", "succulent"], (6, 8)),
}
LOD_RATIOS = (0.2, 0.06)          # measured: 0.32/0.09 cost ~0.6 ms at the avenue views (street-dressing evidence)
LOD_MIN = (400, 120)


def U(p):
    return Vector((-p[0], -p[2], p[1]))


def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def select_objects(model, filt):
    g = next((PH / model).glob("*.gltf"))
    bpy.ops.import_scene.gltf(filepath=str(g))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if filt == "plain":
        meshes = [o for o in meshes if "rust" not in o.name]
    elif filt == "rust":
        meshes = [o for o in meshes if "rust" in o.name]
    elif filt:
        meshes = [o for o in meshes if o.name.endswith(filt)]
    if not meshes:
        raise RuntimeError(f"no objects for {model} {filt}")
    return meshes


def join(meshes, name):
    """Bake transforms and merge into one object (materials kept per face)."""
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in meshes:
        o.select_set(True)
        if o.data.users > 1:
            o.data = o.data.copy()
        if o.parent:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    if ob.data.shape_keys:
        ob.shape_key_clear()        # the scanned rims ship with shape keys; keep the basis
    ob.name = name
    ob.data.name = name
    for o in list(bpy.data.objects):
        if o != ob:
            bpy.data.objects.remove(o, do_unlink=True)
    return ob


def normalise(ob, yaw):
    """Front to Unity +Z (Blender -Y), footprint centre to the origin, base on the ground."""
    if yaw:
        ob.data.transform(Matrix.Rotation(math.radians(yaw), 4, "Z"))
    vs = [v.co for v in ob.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    ob.data.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    ob.data.update()
    # Unity bounds: x = Blender x width, y = height, z = Blender y depth
    return [round(mx.x - mn.x, 4), round(mx.z - mn.z, 4), round(mx.y - mn.y, 4)]


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def decimated_copy(ob, ratio, min_tris, name):
    me = ob.data.copy()
    c = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(c)
    t0 = tris(me)
    r = max(ratio, min(1.0, min_tris / max(1, t0)))
    if r < 0.999:
        for o in bpy.context.selected_objects:
            o.select_set(False)
        c.select_set(True)
        bpy.context.view_layer.objects.active = c
        d = c.modifiers.new("d", "DECIMATE")
        d.ratio = r
        d.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier="d")
    c.data.name = name
    return c


def export(ob, path):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="NONE", export_tangents=True, export_normals=True, export_apply=True,
                              export_materials="EXPORT", export_vertex_color="NONE", export_extras=False)


def material_sources(model):
    """Poly Haven glTF material -> source maps (relative to the model folder) and alpha mode."""
    g = json.loads(next((PH / model).glob("*.gltf")).read_text())
    imgs = [i["uri"] for i in g["images"]]
    tex = lambda ref: imgs[g["textures"][ref["index"]]["source"]] if ref else None
    out = {}
    for m in g["materials"]:
        pbr = m.get("pbrMetallicRoughness", {})
        out[m["name"]] = {"model": model, "base": tex(pbr.get("baseColorTexture")), "normal": tex(m.get("normalTexture")),
                          "arm": tex(pbr.get("metallicRoughnessTexture")), "alpha": m.get("alphaMode", "OPAQUE"),
                          "cutoff": m.get("alphaCutoff", 0.5), "doubleSided": m.get("doubleSided", False),
                          "roughness": pbr.get("roughnessFactor", 1.0), "metallic": pbr.get("metallicFactor", 1.0)}
    # alpha maps the glTF does not reference (fetched as extra maps)
    extras = sorted(p.name for p in (PH / model / "textures").glob("*alpha*"))
    for name, spec in out.items():
        cand = [e for e in extras if e.startswith(name.split(".")[0])]
        if spec["alpha"] != "OPAQUE" and cand:
            spec["alphaMap"] = "textures/" + cand[0]
    return out


def prep(pid, report):
    model, filt, yaw, notes = PROPS[pid]
    clean()
    ob = join(select_objects(model, filt), f"SD_{pid}")
    size = normalise(ob, yaw)
    entry = {"source": model, "objects": filt or "all", "notes": notes, "size": size, "lods": [], "materials": {}}
    lods = [ob] + [decimated_copy(ob, LOD_RATIOS[i], LOD_MIN[i], f"SD_{pid}_LOD{i + 1}") for i in range(2)]
    for i, o in enumerate(lods):
        o.name = f"SD_{pid}_LOD{i}"
        export(o, OUT / pid / f"{pid}_LOD{i}.glb")
        entry["lods"].append(tris(o.data))
    srcs = material_sources(model)
    for m in ob.data.materials:
        key = m.name
        spec = srcs.get(key) or srcs.get(key.split(".")[0]) or next((v for k, v in srcs.items() if k.split(".")[0] == key.split(".")[0]), None)
        entry["materials"][key] = spec
    report[pid] = entry
    print(pid, size, entry["lods"], list(entry["materials"]), flush=True)
    return ob


# ------------------------------------------------------------------ planted containers
def planted(pid, report, src, lod_mesh):
    import scatter_hill_plants as SHP
    cont, mix, (n0, n1) = PLANTED[pid]
    model, filt, yaw, notes = PROPS[cont]
    # plant meshes (datablocks) survive: only the objects are removed
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    ob = join(select_objects(model, filt), f"SD_{pid}")
    size = normalise(ob, yaw)
    # find the inside floor / liner by casting down from above the rim at a few points
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
    top = size[1]
    w, d = size[0], size[2]
    hits = []
    for fx, fy in [(0, 0), (0.2, 0.2), (-0.2, 0.2), (0.2, -0.2), (-0.2, -0.2)]:
        loc, nrm, idx, dist = bvh.ray_cast(Vector((fx * w, fy * d, top + 0.5)), Vector((0, 0, -1)))
        if loc is not None:
            hits.append(loc.z)
    floor = sorted(hits)[len(hits) // 2] if hits else top * 0.5
    soil_z = min(top - 0.035, max(floor + 0.02, top - 0.09))
    # soil: an inset rounded rectangle / disc just below the rim
    round_pot = abs(w - d) < 0.05
    bm = bmesh.new()
    rim_in = 0.84 if round_pot else 0.9
    if round_pot:
        r = min(w, d) / 2 * rim_in
        # the pot tapers: radius at the soil level from the outer shell (cast sideways)
        loc, *_ = bvh.ray_cast(Vector((0, 0, soil_z)), Vector((1, 0, 0)))
        if loc is not None:
            r = max(0.05, loc.x - 0.012)
        ring = [bm.verts.new((r * math.cos(a), r * math.sin(a), soil_z)) for a in [2 * math.pi * i / 28 for i in range(28)]]
        bm.faces.new(ring)
        footprint = lambda x, y: math.hypot(x, y) < r - 0.03
    else:
        hx, hy = w / 2 * rim_in - 0.02, d / 2 * rim_in - 0.02
        for fx, fy in [(1, 0), (0, 1)]:
            loc, *_ = bvh.ray_cast(Vector((0, 0, soil_z)), Vector((fx, fy, 0)))
            if loc is not None:
                if fx:
                    hx = min(hx, loc.x - 0.012)
                else:
                    hy = min(hy, loc.y - 0.012)
        bm.faces.new([bm.verts.new((x, y, soil_z)) for x, y in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))])
        footprint = lambda x, y: abs(x) < hx - 0.04 and abs(y) < hy - 0.04
    soil_me = bpy.data.meshes.new(f"{pid}_soil")
    bm.to_mesh(soil_me)
    bm.free()
    mat = bpy.data.materials.get("WH_BedSoil") or bpy.data.materials.new("WH_BedSoil")
    soil_me.materials.append(mat)
    # UVs in metres (tiling soil)
    soil_me.uv_layers.new(name="UVMap")
    for loop in soil_me.loops:
        v = soil_me.vertices[loop.vertex_index].co
        soil_me.uv_layers[0].data[loop.index].uv = (v.x * 1.5, v.y * 1.5)
    soil = bpy.data.objects.new(f"{pid}_soil", soil_me)
    bpy.context.scene.collection.objects.link(soil)
    rng = random.Random(zlib.crc32(pid.encode()))
    n = rng.randint(n0, n1)
    placed = []
    tries = 0
    plant_objs = []
    while len(placed) < n and tries < 400:
        tries += 1
        x = rng.uniform(-w / 2, w / 2)
        y = rng.uniform(-d / 2, d / 2)
        if not footprint(x, y) or any(math.hypot(x - px, y - py) < (0.05 if PLANTED[pid][0] == "pot_clay" else 0.11) for px, py in placed):
            continue
        k = rng.choice(mix)
        variants = [key for key in lod_mesh[0] if key[0] == k]
        vi = rng.choice(variants)[1]
        s0, s1 = SHP.SPECIES[k][4]
        pot = PLANTED[pid][0] == "pot_clay"
        sc = rng.uniform(s0, s1) * ({"grass2": 1.35, "grass1": 1.3, "succulent": 0.42, "iceplant": 0.5} if pot else
                                    {"grass2": 0.75, "grass1": 0.7, "succulent": 0.9}).get(k, 0.85)
        me = lod_mesh[0][(k, vi)].copy()
        me.transform(Matrix.Translation((x, y, soil_z - 0.01)) @ Matrix.Rotation(rng.uniform(0, 6.28), 4, "Z") @ Matrix.Scale(sc, 4))
        po = bpy.data.objects.new(f"plant{len(placed)}", me)
        bpy.context.scene.collection.objects.link(po)
        plant_objs.append(po)
        placed.append((x, y))
    # join: container + soil + plants
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in [ob, soil] + plant_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = f"SD_{pid}"
    vs = [v.co for v in ob.data.vertices]
    size = [round(max(v.x for v in vs) - min(v.x for v in vs), 4), round(max(v.z for v in vs), 4), round(max(v.y for v in vs) - min(v.y for v in vs), 4)]
    entry = {"source": PROPS[cont][0], "container": cont, "plants": len(placed), "notes": f"{PROPS[cont][3]} with soil and {len(placed)} plants",
             "size": size, "lods": [], "materials": {}}
    lods = [ob] + [decimated_copy(ob, LOD_RATIOS[i], LOD_MIN[i], f"SD_{pid}_LOD{i + 1}") for i in range(2)]
    for i, o in enumerate(lods):
        o.name = f"SD_{pid}_LOD{i}"
        export(o, OUT / pid / f"{pid}_LOD{i}.glb")
        entry["lods"].append(tris(o.data))
    srcs = material_sources(PROPS[cont][0])
    for m in ob.data.materials:
        entry["materials"][m.name] = srcs.get(m.name) or {"shared": m.name}
    report[pid] = entry
    print(pid, size, entry["lods"], list(entry["materials"]), flush=True)


def main():
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None
    path = OUT / "ph-props.json"
    report = json.loads(path.read_text()) if path.exists() else {}
    for pid in PROPS:
        if only and pid not in only:
            continue
        prep(pid, report)
    want_planted = [p for p in PLANTED if not only or p in only]
    if want_planted:
        import scatter_hill_plants as SHP
        clean()
        src = SHP.load_sources()
        lod_mesh = {0: {}}
        for k in {k for p in want_planted for k in PLANTED[p][1]}:
            model, variants, r0, r1, _s = SHP.SPECIES[k]
            for vi, me in enumerate(src[k]):
                lod_mesh[0][(k, vi)] = SHP.decimated(me, max(r0, 0.3), f"{k}{vi}L0")
        for pid in want_planted:
            planted(pid, report, src, lod_mesh)
    OUT.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
