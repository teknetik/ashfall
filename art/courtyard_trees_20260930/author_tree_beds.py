"""Courtyard tree beds for the two birches, Blender 5.2 headless (30 September 2026).

Carl (30 Sep 2026): "i think the other two trees in the courtyard should have similar enclosures to the large tree. move the
trees if need be". The courtyard birches (scene roots `birch 3` by Salvage and `birch 4b` by Air + Water) get the hero
tree's enclosure at street level, on the same stone (shared kit art/ward_masonry_kit, Athen Hill/Masonry Lit) and the same
construction as the hill ring (art/hill_20260930/author_ward_hill.py, whose helpers this imports):

* one dressed course, outer face bent round the trunk, and curved coping stones with a seat 0.49 m above the paving;
* leaf-litter soil 0.25 m below the coping rising to the trunk flare, surface roots, a drip line from an irrigation riser;
* a ring of curved apron flags on the street paving and sheltered sand against the wall foot (LOD0);
* bronze uplights in the coping (the lens material and lights join the Ward lighting clock in Unity);
* history: Birch 4b's roots have lifted and cracked one coping stone (iron dog cramps over the crack), Birch 3 has one
  paler replacement stone; light old battle damage like the rest of the district.

Both trees move north so their rings clear the porches (the trunks are centred on their roots, see BEDS):
birch 3 (-19.75, 24.39) -> (-19.60, 25.55): 2.1 m from the Salvage porch and its crown further off the north wall;
birch 4b (-16.34, -3.64) -> (-16.34, -1.85): 1.4 m of walkway to the Air + Water porch, the cross street stays 5 m wide.

Run:  env -i HOME=$HOME PATH=/usr/bin:/bin blender -b --factory-startup --python-exit-code 1 -P author_tree_beds.py
Outputs (Unity metres local to each bed root at the trunk centre, paving at y 0):
  unity/AthenHill/Assets/AthenHill/Art/CourtyardTrees/Models/TreeBed_<Key>_LOD0/1.glb, TreeBedPlants_<Key>_LOD0/1.glb,
  tree-beds.json (tree moves, ring/soil collider specs, lights, triangle counts) and art/courtyard_trees_20260930/
  tree-beds-source.blend. Plants reuse the hill's CC0 Poly Haven sources (art/hill_20260930/polyhaven) and materials.
"""
import bpy, bmesh, json, math, random, sys, types
from pathlib import Path
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "art/ward_masonry_kit"))
sys.path.insert(0, str(ROOT / "art/hill_20260930"))
import ward_masonry as WM
from ward_masonry import (Part, Frame, stone_tint, fill_wall, finalize_parts, AOBaker, lerp, smoothstep, drng, export,
                          tri_count, MORTAR_FRONT, ScarSet, U)
import hill_layout as HL
import author_ward_hill as AWH       # ring helpers (prism, flag, arc_solid, bend, bevel_sharp, obox, root_mesh, HillDrips)
import scatter_hill_plants as SHP    # Poly Haven plant loading, decimation, Poisson disc

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/CourtyardTrees/Models"
OUT.mkdir(parents=True, exist_ok=True)
J = 0.009

# heights above the street paving (y 0); the hero ring's proportions (its course is 1.46-1.86, coping to 1.99 on a 1.5 hill)
RING_BOT, RING_TOP = -0.04, 0.36
RING_CAP = (0.36, 0.49)
RING_CAP_OVER = 0.05
SOIL_EDGE, SOIL_MID = 0.245, 0.325
APRON_W, APRON_TOP = 0.42, 0.02
TRUNK_R = 0.36                      # both birch trunks measure 0.30-0.38 m at the ground (tree-probe.json)

# angles are degrees from +X towards +Z, as on the hill; roots: (angle, reach from the trunk centre, base radius)
BEDS = {
    "Birch3": dict(tree="birch 3", old=(-19.750027, 24.39377), centre=(-19.60, 25.55), RO=1.62, RI=1.22, seed=3,
                   uplights=[26.0, 206.0], standpipe=128.0, heave=None, replaced=252.0, cap_start=11.0,
                   impacts=[(-12.0, 0.22, 0.45, 0.75)], drifts=[(150.0, 235.0), (292.0, 330.0)],
                   roots=[(14, 0.98, 0.05), (86, 0.9, 0.044), (162, 1.04, 0.052), (238, 0.86, 0.04), (312, 1.0, 0.048)]),
    "Birch4b": dict(tree="birch 4b", old=(-16.339277, -3.6388378), centre=(-16.339277, -1.85), RO=1.80, RI=1.38, seed=4,
                    uplights=[42.0, 222.0], standpipe=302.0, heave=158.0, replaced=None, cap_start=4.0,
                    impacts=[(2.0, 0.24, 0.55, 0.9), (96.0, 0.2, 0.4, 0.6)], drifts=[(120.0, 196.0), (250.0, 286.0)],
                    roots=[(20, 1.1, 0.052), (94, 1.0, 0.046), (158, 1.72, 0.072), (214, 1.08, 0.05), (286, 0.96, 0.044),
                           (338, 1.12, 0.05)]),
}


def layout(b):
    """What the imported hill helpers read from their module-level `H` (ring centre, radii, coping, noise)."""
    return types.SimpleNamespace(RING_C=(0.0, 0.0), RO=b["RO"], RI=b["RI"], RING_CAP=RING_CAP, vnoise=HL.vnoise,
                                 BLOCK=HL.BLOCK, TRUNK_C=(0.0, 0.0))


def soil_y(b, x, z):
    """Leaf-litter soil: 0.245 m below the coping at the wall, rising to the trunk flare."""
    r = math.hypot(x, z)
    t = max(0.0, min(1.0, (b["RI"] - r) / (b["RI"] - 0.45)))
    base = SOIL_EDGE + (SOIL_MID - SOIL_EDGE) * (t * t * (3 - 2 * t))
    flare = 0.045 * max(0.0, 1.0 - (r - TRUNK_R) / 0.35) if r > TRUNK_R else 0.045
    s = b["seed"] * 7.3
    return base + flare + 0.012 * HL.vnoise(x + s, z, 2.3, 7) + 0.005 * HL.vnoise(x, z + s, 7.1, 8)


def arc_drift(part, r, a0, a1, width, height, key, y=0.0):
    """Sand banked against the outer wall foot along an arc (triangular section, feathered ends)."""
    rr = drng("drift", key)
    bm = part.bm
    mi = part.mi("VH_Sand")
    n = max(6, int(math.radians(a1 - a0) * r / 0.09))
    rows = []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        env = math.sin(math.pi * t) ** 0.6
        hgt = height * env * rr.uniform(0.6, 1.2)
        wdt = width * env * rr.uniform(0.7, 1.2) + 0.02
        c = Vector((math.cos(a), 0.0, math.sin(a)))
        rows.append([bm.verts.new(c * (r + 0.004) + Vector((0, y - 0.004, 0))),
                     bm.verts.new(c * (r + 0.02 + wdt * 0.3) + Vector((0, y + hgt, 0))),
                     bm.verts.new(c * (r + 0.02 + wdt) + Vector((0, y - 0.004, 0)))])
    for i in range(n):
        for k in range(2):
            f = bm.faces.new([rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]])
            f.material_index = mi
    for f in bm.faces:
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()


def build(key, b, lod):
    L = random.Random(20260930 + b["seed"])
    WM.set_state(lod, L, "tree_bed_" + key)
    WM.WEAR["ground_y"] = 0.0
    WM.TINT[:] = [1.0, 1.0, 1.0]
    WM.reset_materials()
    AWH.H = layout(b)
    coll = bpy.data.collections.new(f"TreeBed_{key}_LOD{lod}")
    bpy.context.scene.collection.children.link(coll)
    p = lambda s, wear=True: Part(f"TB_{key}_{s}_LOD{lod}", wear=wear)
    ring, pave = p("Ring"), p("Apron")
    metal, sand, litter = p("Metal", False), p("Sand", False), p("Soil", False)
    drips = AWH.HillDrips()
    scars = ScarSet(base=0.1)
    RO, RI = b["RO"], b["RI"]
    rec = {"tree": b["tree"], "old_position": list(b["old"]), "position": list(b["centre"]), "lights": [], "notes": []}

    # ------------------------------------------------------------------ the dressed course, outer and inner faces
    Fs = Frame((0, 0, 0), (1, 0, 0), (0, 0, 1))
    Ro_base = RO - HL.BLOCK
    C = 2 * math.pi * Ro_base
    v0, f0 = len(ring.bm.verts), len(ring.bm.faces)
    fill_wall(ring, Fs, 0.0, C, [RING_BOT, RING_TOP], [], mat="VH_Ashlar", key="ringO", lmin=0.42, lmax=0.64, mortar=False)
    u = 0.0
    while u < C - 1e-4:
        Fs.box(ring, u, min(C, u + 0.16), RING_BOT, RING_TOP, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
        u += 0.16
    AWH.bend(ring, v0, f0, Ro_base, inner=False)
    Ri_base = RI + HL.BLOCK
    Ci = 2 * math.pi * Ri_base
    v0, f0 = len(ring.bm.verts), len(ring.bm.faces)
    fill_wall(ring, Fs, 0.0, Ci, [SOIL_EDGE - 0.12, RING_TOP], [], mat="VH_Ashlar", key="ringI", lmin=0.36, lmax=0.52, mortar=False)
    u = 0.0
    while u < Ci - 1e-4:
        Fs.box(ring, u, min(Ci, u + 0.16), SOIL_EDGE - 0.12, RING_TOP, 0.02, MORTAR_FRONT, "VH_Mortar", skip=("s0", "bottom", "top", "s1", "s3"))
        u += 0.16
    AWH.bend(ring, v0, f0, Ri_base, inner=True)

    # ------------------------------------------------------------------ coping stones (seat)
    rc = (RO + RI) / 2
    hw = (RO - RI) / 2 + RING_CAP_OVER
    y0c, y1c = RING_CAP
    cprof = [(-hw, y0c), (hw, y0c), (hw, y1c - 0.035), (hw - 0.02, y1c - 0.008), (hw - 0.05, y1c), (0.0, y1c + 0.004),
             (-hw + 0.05, y1c), (-hw + 0.02, y1c - 0.008), (-hw, y1c - 0.035)][::-1]
    rr = drng("ringcap", key)
    a = b["cap_start"]
    end = a + 360.0
    caps = []
    while a < end - 1e-3:
        span = math.degrees(rr.uniform(0.78, 1.02) / rc)
        if end - (a + span) < math.degrees(0.5 / rc):
            span = end - a
        caps.append((a, a + span))
        a += span
    jd = math.degrees(J / rc)

    def nearest(angle):
        return min(range(len(caps)), key=lambda i: abs(((caps[i][0] + caps[i][1]) / 2 - angle + 180) % 360 - 180))
    heave = nearest(b["heave"]) if b["heave"] is not None else -1
    replaced = nearest(b["replaced"]) if b["replaced"] is not None else -1
    for i, (a0, a1) in enumerate(caps):
        if i == heave:
            # a root lifts the inner edge towards the stone's far end; the stone cracked a third of the way along
            crack = a0 + (a1 - a0) * 0.4
            for (c0, c1, lift0, lift1) in ((a0 + jd / 2, crack - 0.2, 0.0, 0.01), (crack + 0.2, a1 - jd / 2, 0.014, 0.03)):
                def lift(t, l0=lift0, l1=lift1):
                    base_ = lerp(l0, l1, t)
                    return lambda o, bb=base_: bb * (0.55 + 0.45 * (-o / hw))
                bid = ring.new_block(tint=stone_tint(), erode=0.01)
                vs, fs = AWH.arc_solid(ring, rc, c0, c1, cprof, "VH_Ashlar", bid, lift=lift)
                AWH.bevel_sharp(ring, fs, 0.009)
            for ca in (crack, a1):
                rad = math.radians(ca)
                cx, cz = rc * math.cos(rad), rc * math.sin(rad)
                tx, tz = -math.sin(rad), math.cos(rad)
                ytop = y1c + (0.022 if ca == crack else 0.032)
                for off in (-0.065, 0.065):
                    ox, oz = cx + math.cos(rad) * off, cz + math.sin(rad) * off
                    AWH.obox(metal, (ox, oz), (tx, tz), 0.085, 0.011, ytop - 0.006, ytop + 0.011, "VH_Steel")
                    for e_ in (-0.077, 0.077):
                        AWH.obox(metal, (ox + tx * e_, oz + tz * e_), (tx, tz), 0.011, 0.014, ytop - 0.012, ytop - 0.004, "VH_Dark")
                drips.ring.append((ca % 360, 4.5, "rust", 0.85))
            rec["notes"].append(f"root-heaved coping stone at {round((a0 + a1) / 2 % 360, 1)} deg, cracked at {round(crack % 360, 1)} deg, 4 iron cramps")
            continue
        tint = stone_tint()
        if i == replaced:
            tint = tuple(min(1.0, c * 1.16) for c in stone_tint(sigma=0.04))    # a later, paler replacement stone
            rec["notes"].append(f"paler replacement coping stone at {round((a0 + a1) / 2 % 360, 1)} deg")
        bid = ring.new_block(tint=tint, erode=0.008 if i != replaced else 0.004)
        vs, fs = AWH.arc_solid(ring, rc, a0 + jd / 2, a1 - jd / 2, cprof, "VH_Ashlar", bid)
        AWH.bevel_sharp(ring, fs, 0.008)
    rec["ring"] = {"centre": [0.0, 0.0], "outer": RO + RING_CAP_OVER, "inner": RI - RING_CAP_OVER, "bottom": -0.1,
                   "top": RING_CAP[1], "soil_top": (SOIL_EDGE + SOIL_MID) / 2}
    for (deg, y, radius, st) in b["impacts"]:
        rad = math.radians(deg)
        scars.impact((RO * math.cos(rad), y, RO * math.sin(rad)), radius, st)

    # ------------------------------------------------------------------ uplights in the coping
    for ua in b["uplights"]:
        rad = math.radians(ua)
        cx, cz = (rc + 0.05) * math.cos(rad), (rc + 0.05) * math.sin(rad)
        ytop = y1c + 0.004
        metal.cyl((cx, ytop - 0.02, cz), (cx, ytop + 0.016, cz), 0.066, "VH_Bronze", 20)
        metal.cyl((cx, ytop + 0.016, cz), (cx, ytop + 0.022, cz), 0.05, "VH_LampLens", 20)
        for k in range(4):
            aa = rad + math.pi / 4 + k * math.pi / 2
            metal.cyl((cx + 0.058 * math.cos(aa), ytop + 0.016, cz + 0.058 * math.sin(aa)),
                      (cx + 0.058 * math.cos(aa), ytop + 0.022, cz + 0.058 * math.sin(aa)), 0.005, "VH_Steel", 6)
        # a birch carries its crown from ~3 m up: graze the trunk and fill the lower crown (first pass at 30 / 12 m / 50 deg
        # left the trunks dark in the 20:30 native captures; now as strong as the hero ring's uplights)
        tgt = (cx * 0.12, 4.8, cz * 0.12)
        rec["lights"].append({"name": f"Tree uplight {int(ua)}", "type": "Spot", "pos": [cx, ytop + 0.05, cz], "target": list(tgt),
                              "intensity": 70.0, "range": 14.0, "angle": 66.0, "inner": 30.0, "color": [1.0, 0.87, 0.7]})

    # ------------------------------------------------------------------ irrigation riser and drip line (aquifer water)
    rad = math.radians(b["standpipe"])
    px, pz = (RI - 0.2) * math.cos(rad), (RI - 0.2) * math.sin(rad)
    ys = soil_y(b, px, pz)
    metal.cyl((px, ys - 0.1, pz), (px, ys + 0.34, pz), 0.024, "VH_Steel", 12)
    metal.cyl((px, ys + 0.24, pz), (px, ys + 0.29, pz), 0.04, "VH_Bronze", 14)
    for k in range(6):
        aa = k * math.pi / 3
        metal.cyl((px, ys + 0.38, pz), (px + 0.062 * math.cos(aa), ys + 0.38, pz + 0.062 * math.sin(aa)), 0.006, "VH_Bronze", 6)
    metal.cyl((px, ys + 0.372, pz), (px, ys + 0.386, pz), 0.068, "VH_Bronze", 18)
    metal.cyl((px, ys + 0.372, pz), (px, ys + 0.386, pz), 0.056, "VH_Bronze", 18)
    metal.cyl((px, ys + 0.34, pz), (px, ys + 0.39, pz), 0.012, "VH_Steel", 8)
    if lod == 0:
        # black drip line from the riser foot round the bed, half in the litter, emitters every ~0.3 m
        rl = RI * 0.62
        pts = [(px, ys + 0.02, pz)]
        steps = 64
        for k in range(steps + 1):
            aa = rad - math.radians(18) - 2 * math.pi * 0.9 * k / steps
            x, z = rl * math.cos(aa), rl * math.sin(aa)
            pts.append((x, soil_y(b, x, z) + 0.004, z))
        metal.tube(pts, 0.009, "VH_Dark", sides=6)
        for k in range(2, steps, 5):
            x, y, z = pts[k]
            metal.cyl((x, y - 0.004, z), (x, y + 0.016, z), 0.012, "VH_Dark", 6)

    # ------------------------------------------------------------------ apron: curved flags on the street paving
    ra, rb = RO + 0.004, RO + APRON_W
    n_ap = int(round(2 * math.pi * (ra + rb) / 2 / 0.68))
    off = b["cap_start"] + 9.0
    for k in range(n_ap):
        a0 = 360.0 * k / n_ap + off
        a1 = 360.0 * (k + 1) / n_ap + off
        jd2 = math.degrees(0.005 / rb)
        outer = AWH.circle_pts(rb, a0 + jd2, a1 - jd2, 0.1)
        inner = AWH.circle_pts(ra, a0 + jd2 * 1.2, a1 - jd2 * 1.2, 0.1)[::-1]
        AWH.flag(pave, outer + inner, APRON_TOP, key=(key, "apron", k), thick=0.12)

    # ------------------------------------------------------------------ leaf-litter soil (polar grid tucked under the wall)
    bml = litter.bm
    mi_l = litter.mi("WH_RingLitter")
    nr, na = (12, 72) if lod == 0 else (5, 32)
    rows = []
    for i in range(nr + 1):
        r = 0.25 + (RI + 0.03 - 0.25) * i / nr
        row = []
        for j in range(na):
            a_ = 2 * math.pi * j / na
            x, z = r * math.cos(a_), r * math.sin(a_)
            row.append(bml.verts.new(Vector((x, soil_y(b, x, z), z))))
        rows.append(row)
    for i in range(nr):
        for j in range(na):
            jj = (j + 1) % na
            f = bml.faces.new([rows[i][j], rows[i][jj], rows[i + 1][jj], rows[i + 1][j]])
            f.material_index = mi_l
    cap = bml.faces.new(rows[0])
    cap.material_index = mi_l
    for f in bml.faces:
        f.normal_update()
        if f.normal.y < 0:
            f.normal_flip()

    # ------------------------------------------------------------------ sheltered sand against the wall foot (LOD0)
    if lod == 0:
        for k, (a0, a1) in enumerate(b["drifts"]):
            arc_drift(sand, RO, a0, a1, 0.2, 0.045, (key, k), y=APRON_TOP)

    # ------------------------------------------------------------------ surface roots from the trunk flare
    paths = []
    for k, (deg, reach, r0) in enumerate(b["roots"]):
        rr = drng("root", key, k)
        a_ = math.radians(deg)
        heave_root = b["heave"] is not None and abs(deg - b["heave"]) < 1e-6
        pts = []
        start = TRUNK_R - 0.06
        s = start
        w1, w2 = rr.uniform(0, 6.28), rr.uniform(0, 6.28)
        while s <= reach:
            t = (s - start) / (reach - start)
            aa = a_ + (0.14 * math.sin(s * 3.1 + w1) + 0.05 * math.sin(s * 8.3 + w2)) * min(1.0, t * 3)
            x, z = s * math.cos(aa), s * math.sin(aa)
            rad_ = lerp(r0, r0 * 0.3, t ** 0.75)
            collar = max(0.0, 1 - (s - start) / 0.25)
            hump = 0.5 + 0.5 * math.sin(s * 4.1 + w1)
            above = -0.35 + 0.45 * hump + 0.6 * collar - 1.0 * smoothstep(0.5, 1.0, t)
            if heave_root:
                above = 0.3 + 0.25 * hump + 0.5 * collar - 0.9 * smoothstep(0.86, 1.0, t)
            pts.append((x, soil_y(b, x, z) + rad_ * 0.6 * above, z))
            s += 0.05
        paths.append((pts, r0, r0 * 0.3))
        if r0 >= 0.05 and len(pts) > 8:
            side = rr.choice((-1, 1))
            b0 = pts[int(len(pts) * 0.45)]
            sp = []
            ln = rr.uniform(0.3, 0.5)
            steps = max(4, int(ln / 0.05))
            for i in range(steps + 1):
                t = i / steps
                aa = a_ + side * (0.6 + 0.3 * t)
                sx, sz = b0[0] + ln * t * math.cos(aa), b0[2] + ln * t * math.sin(aa)
                rr_ = r0 * 0.4 * (1 - 0.7 * t)
                sp.append((sx, soil_y(b, sx, sz) + rr_ * 0.6 * (0.4 - 1.2 * smoothstep(0.5, 1.0, t)), sz))
            paths.append((sp, r0 * 0.4, r0 * 0.12))

    parts = [ring, pave, metal, litter] + ([sand] if lod == 0 else [])
    finalize_parts(parts)
    ao = AOBaker([ring, pave, litter], ground_y=0.0, samples=24 if lod == 0 else 10, ground_weight=0.16, strength=0.85)
    objs = [ring.build(coll, ao=ao, drips=drips, ground_y=0.0, splash=0.3, scars=scars),
            pave.build(coll, ao=ao, drips=drips, ground_y=0.0, splash=0.1, scars=scars),
            metal.build(coll),
            litter.build(coll, macro=0.0, splash=0.0),
            AWH.root_mesh(f"TB_{key}_Roots_LOD{lod}", paths, coll, lod)]
    if lod == 0:
        objs.append(sand.build(coll, macro=0.0, splash=0.0))
    else:
        sand.bm.free()
    rec["triangles"] = tri_count(objs)
    rec["objects"] = {o.name: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for o in objs}
    return objs, rec


# ====================================================================== planting inside each ring
BED_SPECIES = ["weed", "celandine", "iceplant", "grass2", "bark", "twig", "stone"]


def plant(key, b, src, lod_mesh, rng):
    """Weeds, ice plant and a few grass tufts by the wall; bark, twigs and stones on the litter; the trunk collar clear."""
    SHP.H = layout(b)
    RI = b["RI"]
    poly = [((RI - 0.07) * math.cos(2 * math.pi * i / 48), (RI - 0.07) * math.sin(2 * math.pi * i / 48)) for i in range(48)]
    uprad = [(math.radians(a), 0.0) for a in b["uplights"]]
    riser = math.radians(b["standpipe"])

    def clear(x, z, r):
        rad = math.hypot(x, z)
        if rad < TRUNK_R + 0.32:
            return False
        a = math.atan2(z, x)
        if abs((a - riser + math.pi) % (2 * math.pi) - math.pi) * rad < 0.22 and rad > RI - 0.4:
            return False
        return True
    pts = SHP.poisson(poly, rng, 0.22, accept=lambda x, z, r: clear(x, z, r))
    pl = []
    for (x, z, r) in pts:
        rad = math.hypot(x, z)
        roll = rng.random()
        if rad > RI - 0.36 and roll < 0.7:
            k = rng.choice(["weed", "celandine", "weed", "iceplant", "grass2", "celandine"])
        elif roll < 0.12:
            k = rng.choice(["celandine", "weed"])
        elif roll < 0.5:
            k = "bark"
        elif roll < 0.6:
            k = "twig"
        elif roll < 0.72:
            k = "stone"
        else:
            continue
        vi = rng.randrange(len(src[k]))
        s0, s1 = SHP.SPECIES[k][4]
        sc = rng.uniform(s0, s1) * {"grass2": 0.62, "bark": 0.6, "twig": 0.8}.get(k, 1.0)
        y = soil_y(b, x, z) - (0.03 if k in ("bark", "twig") else 0.015)
        pl.append((k, vi, x, y, z, rng.uniform(0, 360), sc, rng.uniform(-4, 4), k in ("bark", "twig", "weed", "grass2")))
    return pl


def export_plants(key, pl, lod_mesh, lod):
    base = SOIL_EDGE + 0.04
    objs = []
    report = {}
    for group in ("cover", "cast"):
        sel = [p for p in pl if (p[0] in SHP.CASTERS) == (group == "cast")]
        if lod == 1:
            sel = [p for p in sel if p[8]]
        if not sel:
            continue
        bm = bmesh.new()
        mats = []
        for (k, vi, x, y, z, yaw, sc, tilt, _l1) in sel:
            me = lod_mesh[lod][(k, vi)]
            M = (Matrix.Translation(U((x, y - base, z))) @ Matrix.Rotation(math.radians(yaw), 4, "Z") @
                 Matrix.Rotation(math.radians(tilt), 4, "X") @ Matrix.Scale(sc, 4))
            tmp = me.copy()
            tmp.transform(M)
            for m in tmp.materials:
                if m.name not in mats:
                    mats.append(m.name)
            remap = [mats.index(m.name) for m in tmp.materials]
            bt = bmesh.new()
            bt.from_mesh(tmp)
            for f in bt.faces:
                f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
            bt.to_mesh(tmp)
            bt.free()
            bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)
        name = f"TreeBedPlants_{key}_{group}_LOD{lod}"
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for mname in mats:
            me.materials.append(bpy.data.materials.get(mname))
        ob = bpy.data.objects.new(name, me)
        ob.location = U((0, base, 0))
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
        report[group] = {"instances": len(sel), "triangles": sum(len(p_.vertices) - 2 for p_ in me.polygons), "materials": mats}
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT / f"TreeBedPlants_{key}_LOD{lod}.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_image_format="NONE", export_tangents=True, export_normals=True,
                              export_apply=True, export_materials="EXPORT", export_vertex_color="NONE")
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return report


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(BEDS)
    report = {"source": "art/courtyard_trees_20260930/author_tree_beds.py", "date": "2026-09-30",
              "units": "Unity metres local to each bed root (trunk centre, street paving at y 0)", "beds": {}}
    for key in only:
        b = BEDS[key]
        entry = {"lods": {}}
        for lod in (0, 1):
            objs, rec = build(key, b, lod)
            export(objs, OUT / f"TreeBed_{key}_LOD{lod}.glb")
            entry["lods"][f"LOD{lod}"] = {"triangles": rec["triangles"], "objects": rec["objects"]}
            if lod == 0:
                entry.update({k: v for k, v in rec.items() if k not in ("triangles", "objects")})
            print(f"TreeBed_{key} LOD{lod}: {rec['triangles']} triangles", rec["objects"], flush=True)
        report["beds"][key] = entry
    # planting (sources imported once; the Poly Haven meshes carry the hill's material names)
    src = SHP.load_sources()
    lod_mesh = {0: {}, 1: {}}
    for k in BED_SPECIES:
        model, variants, r0, r1, _s = SHP.SPECIES[k]
        for vi, me in enumerate(src[k]):
            lod_mesh[0][(k, vi)] = SHP.decimated(me, r0, f"{k}{vi}L0")
            lod_mesh[1][(k, vi)] = SHP.decimated(me, r1, f"{k}{vi}L1")
    for key in only:
        b = BEDS[key]
        pl = plant(key, b, src, lod_mesh, random.Random(4100 + b["seed"]))
        report["beds"][key]["plants"] = {f"LOD{lod}": export_plants(key, pl, lod_mesh, lod) for lod in (0, 1)}
        counts = {}
        for p_ in pl:
            counts[p_[0]] = counts.get(p_[0], 0) + 1
        report["beds"][key]["plant_counts"] = counts
        print(f"TreeBedPlants_{key}", counts, flush=True)
    path = OUT / "tree-beds.json"
    if path.exists() and only != list(BEDS):
        old = json.loads(path.read_text())
        old["beds"].update(report["beds"])
        report["beds"] = old["beds"]
    path.write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "tree-beds-source.blend"))


if __name__ == "__main__":
    main()
