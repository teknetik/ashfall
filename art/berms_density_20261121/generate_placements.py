#!/usr/bin/env python3
"""Generate purposeful, collision-checked Outer Berms density & wasteland danger placements (21 Nov 2026).

Reads art/berms_variety_20261120/survey.json so every placement stays clear of all 206
encounters, spawns, waystations, landmarks, and existing colliders in the Outer Berms bowl.
Verifies every referenced prefab exists on disk under unity/AthenHill/Assets/AthenHill/Prefabs/.
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
PREFAB_ROOT = REPO_ROOT / "unity" / "AthenHill" / "Assets" / "AthenHill" / "Prefabs"
SURVEY = ROOT.parent / "berms_variety_20261120" / "survey.json"
OUT = ROOT / "placements.json"

rng = random.Random(20261121)

survey = json.loads(SURVEY.read_text(encoding="utf-8"))
markers = survey["markers"]
colliders = survey["colliders"]

# Playable interior margin inside the mountain ring
X_MIN, X_MAX = -520.0, -98.0
Z_MIN, Z_MAX = -205.0, 195.0


def clear_of_scene(x: float, z: float, pad_marker: float = 16.0, pad_col: float = 4.5) -> bool:
    if not (X_MIN <= x <= X_MAX and Z_MIN <= z <= Z_MAX):
        return False
    for m in markers:
        p = m["pos"]
        r = pad_marker
        if m["kind"] in ("encounter", "waystation"):
            r = max(r, 20.0)
        elif m["kind"] in ("spawn", "droid", "salvage", "loot"):
            r = max(r, 12.0)
        elif m["kind"] == "landmark":
            r = max(r, 14.0)
        if math.hypot(x - p[0], z - p[2]) < r:
            return False
    for c in colliders:
        mn, mx = c["min"], c["max"]
        if (mn[0] - pad_col) <= x <= (mx[0] + pad_col) and (mn[2] - pad_col) <= z <= (mx[2] + pad_col):
            return False
    return True


placements = []
placed_xy = []


def add_prop(group: str, cluster: str, prefab: str, x: float, z: float,
             yaw: float = None, scale: float = 1.0, sink: float = 0.08,
             shadows: bool = True, collider: str = "keep", cull: float = 0.012,
             min_self_sep: float = 1.6, check_scene: bool = True,
             hazard: str = None) -> bool:
    if check_scene and not clear_of_scene(x, z):
        return False
    for px, pz in placed_xy:
        if math.hypot(x - px, z - pz) < min_self_sep:
            return False
    if yaw is None:
        yaw = round(rng.uniform(0, 360), 1)
    entry = {
        "group": group,
        "cluster": cluster,
        "prefab": prefab,
        "x": round(x, 2),
        "z": round(z, 2),
        "yaw": round(yaw, 1),
        "scale": round(scale, 3),
        "sink": round(sink, 3),
        "shadows": shadows,
        "collider": collider,
        "cull": cull,
    }
    if hazard:
        entry["hazard"] = hazard
    placements.append(entry)
    placed_xy.append((x, z))
    return True


def add_vignette(group: str, name: str, cx: float, cz: float, yaw: float, items: list,
                 pad_marker: float = 18.0, pad_col: float = 6.0) -> int:
    """Place a multi-prop vignette rotated around (cx, cz). Only places if anchor is clear."""
    if not clear_of_scene(cx, cz, pad_marker=pad_marker, pad_col=pad_col):
        return 0
    rad = math.radians(yaw)
    ca, sa = math.cos(rad), math.sin(rad)
    added = 0
    for item in items:
        if len(item) == 8:
            prefab, lx, lz, dyaw, sc, sink, sh, col = item
            hazard = None
        else:
            prefab, lx, lz, dyaw, sc, sink, sh, col, hazard = item
        wx = cx + lx * ca - lz * sa
        wz = cz + lx * sa + lz * ca
        if add_prop(group, name, prefab, wx, wz, (yaw + dyaw) % 360, sc, sink, sh, col,
                    min_self_sep=1.1, check_scene=True, hazard=hazard):
            added += 1
    return added


# 1. Collapsed Industrial Conveyor Spines (ruined haul corridors with real silhouettes & cover)
CONVEYOR_VIGNETTES = [
    ("Conveyor spine · east flats", -148.0, -28.0, 22.0),
    ("Conveyor spine · central wash", -246.0, -74.0, 155.0),
    ("Conveyor spine · relay approach", -286.0, -14.0, 40.0),
    ("Conveyor spine · north haul", -175.0, 18.0, 112.0),
    ("Conveyor spine · west basin", -382.0, -34.0, 75.0),
]
for name, cx, cz, yaw in CONVEYOR_VIGNETTES:
    add_vignette("IndustrialRuins", name, cx, cz, yaw, [
        ("OuterBermsDepot/DP_Conveyor", 0.0, 0.0, 0.0, 1.0, 0.12, True, "keep", "arc"),
        ("OuterBermsDepot/DP_Plinth", -4.8, 0.4, 5.0, 1.0, 0.15, True, "keep"),
        ("OuterBermsDepot/DP_WallA", 4.6, -2.6, 12.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/DP_WallB", -3.2, 3.8, -80.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/DP_SignVoltagePost", 5.8, 2.2, 30.0, 1.0, 0.08, True, "keep"),
        ("OuterBermsDepot/MX_ScrapHeapA", -1.4, -3.5, 45.0, 0.95, 0.14, True, "keep"),
        ("OuterBermsDepot/PHD_LpgTank", 2.8, 3.4, 90.0, 1.0, 0.08, True, "keep"),
        ("WestGate/PH_BoulderB", -6.2, -2.1, 140.0, 1.15, 0.18, True, "keep"),
        ("WestGate/PH_RooibosB", 6.5, -1.0, 20.0, 1.1, 0.08, False, "remove"),
    ])

# 2. Fallen Quantum Tube Branch Line (arcing across the northern and western flats)
TUBE_VIGNETTES = [
    ("Quantum Tube ruin · east span", -162.0, 108.0, 62.0),
    ("Quantum Tube ruin · north ridge", -232.0, 106.0, 88.0),
    ("Quantum Tube ruin · west plain", -375.0, 42.0, 134.0),
    ("Quantum Tube ruin · south flats", -328.0, -135.0, 18.0),
    ("Quantum Tube ruin · far west", -448.0, 76.0, 110.0),
]
for name, cx, cz, yaw in TUBE_VIGNETTES:
    add_vignette("QuantumTubeRuins", name, cx, cz, yaw, [
        ("BermsExpanse/Landmarks/TubePylonFall", 0.0, 0.0, 0.0, 0.88, 0.25, True, "keep", "arc"),
        ("OuterBermsDepot/DP_Plinth", -5.5, 2.2, 15.0, 1.05, 0.15, True, "keep"),
        ("OuterBermsDepot/DP_CradleBroken", 4.8, -2.4, 105.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/DP_WallC", -2.5, -5.2, 42.0, 1.0, 0.14, True, "keep"),
        ("OuterBermsDepot/PHD_BoulderD", 5.6, 3.6, 70.0, 1.25, 0.22, True, "keep"),
        ("WestGate/PH_BoulderA", -6.4, -2.8, 210.0, 1.2, 0.2, True, "keep"),
        ("WestGate/PH_SearsiaSmall", 3.2, 5.1, 45.0, 1.15, 0.08, False, "remove"),
    ])

# 3. Warden Forward Cover Posts & Sandbag Redoubts (tactical cover along patrol trails)
COVER_POSTS = [
    ("Warden post · gate approach", -128.0, 14.0, -15.0),
    ("Warden post · south trail", -142.0, -76.0, 35.0),
    ("Warden post · waystation south", -242.0, 12.0, -40.0),
    ("Warden post · relay east", -294.0, 30.0, 12.0),
    ("Warden post · caravan watch", -166.0, 56.0, 28.0),
    ("Warden post · scrapyard ridge", -254.0, -112.0, 65.0),
    ("Warden post · mesa flank", -328.0, 64.0, -25.0),
    ("Warden post · outer relay", -392.0, 14.0, 5.0),
]
for name, cx, cz, yaw in COVER_POSTS:
    add_vignette("WardenCoverPosts", name, cx, cz, yaw, [
        ("WestGate/WG_SandbagWall2mLow", 0.0, 0.0, 0.0, 1.0, 0.06, True, "keep"),
        ("WestGate/WG_SandbagWall2mLow", 2.2, 0.9, 32.0, 1.0, 0.06, True, "keep"),
        ("WestGate/WG_SandbagPile", -2.1, 0.6, -20.0, 1.0, 0.06, True, "keep"),
        ("StreetDressing/SD_ammo_crate_a", 0.5, -1.5, 18.0, 1.0, 0.03, True, "keep"),
        ("StreetDressing/SD_field_generator", -1.4, -2.0, 72.0, 0.95, 0.05, True, "keep"),
        ("TrainingRange/TR_SpentCells_3", 1.8, -1.2, 40.0, 1.0, 0.02, False, "remove"),
        ("StreetDressing/SD_tarp_stack", -2.8, -1.2, 110.0, 0.95, 0.05, True, "keep"),
    ])

# 4. Karaveen Skirmish & Salvage Wrecks (storytelling between POIs)
SKIRMISH_WRECKS = [
    ("Skirmish wreck · east basin", -178.0, -82.0, 48.0),
    ("Skirmish wreck · north wash", -262.0, 98.0, 132.0),
    ("Skirmish wreck · central flats", -216.0, 28.0, 16.0),
    ("Skirmish wreck · south canyon", -298.0, -148.0, 82.0),
    ("Skirmish wreck · west dune", -436.0, -48.0, 195.0),
    ("Skirmish wreck · derrick road", -338.0, 128.0, 250.0),
]
for name, cx, cz, yaw in SKIRMISH_WRECKS:
    add_vignette("SkirmishWrecks", name, cx, cz, yaw, [
        ("BermsExpanse/Landmarks/CaravanHaulerWreck", 0.0, 0.0, 0.0, 0.78, 0.22, True, "keep", "smoke"),
        ("OuterBermsDepot/DP_CrashedDrone", 4.6, 2.4, 55.0, 1.0, 0.1, True, "keep", "arc"),
        ("OuterBermsDepot/DP_DeadWorker", -4.2, 3.1, 140.0, 1.0, 0.08, True, "keep"),
        ("TrainingRange/TR_WorkerDroidShell", 3.5, -3.4, 220.0, 1.0, 0.08, True, "keep"),
        ("StreetDressing/SD_crate_wood", -2.6, -3.2, 25.0, 1.0, 0.04, True, "keep"),
        ("StreetDressing/SD_drum_red", 2.4, 4.1, 90.0, 1.0, 0.04, True, "keep"),
        ("WestGate/PH_OldTyre", -5.2, -1.0, 12.0, 1.0, 0.05, False, "remove"),
        ("WestGate/PH_Jerrycan", -1.4, -4.1, 65.0, 1.0, 0.03, False, "remove"),
    ])

# 5. Mid-Basin Boulder & Scrub Clusters (natural foreground/midground breakup across open sand)
BOULDERS = [
    "WestGate/PH_BoulderA",
    "WestGate/PH_BoulderB",
    "WestGate/PH_BoulderC",
    "OuterBermsDepot/PHD_BoulderD",
    "OuterBermsDepot/PHD_BoulderE",
]
SCRUB = [
    "WestGate/PH_SearsiaSmall",
    "WestGate/PH_RooibosA",
    "WestGate/PH_RooibosB",
    "WestGate/PH_RooibosC",
    "WestGate/PH_DryBranchA",
    "WestGate/PH_DryBranchB",
]

cluster_centers = [
    (-124.0, -52.0), (-154.0, -112.0), (-196.0, -124.0), (-142.0, 96.0),
    (-192.0, 118.0), (-230.0, -18.0), (-268.0, -32.0), (-314.0, -54.0),
    (-358.0, -68.0), (-368.0, -124.0), (-404.0, -142.0), (-452.0, -144.0),
    (-414.0, 68.0), (-392.0, 124.0), (-346.0, 154.0), (-288.0, 168.0),
    (-466.0, 26.0), (-494.0, 68.0),
]

for idx, (cx, cz) in enumerate(cluster_centers, start=1):
    if not clear_of_scene(cx, cz, pad_marker=16.0, pad_col=5.0):
        continue
    cname = f"Desert cluster · {idx:02d}"
    # 2-3 boulders + 3-4 scrub/branch accents per cluster
    for b in range(rng.randint(2, 3)):
        ang = rng.uniform(0, math.tau)
        dist = rng.uniform(0.0, 4.2) if b > 0 else 0.0
        add_prop("DesertClusters", cname, rng.choice(BOULDERS),
                 cx + math.cos(ang) * dist, cz + math.sin(ang) * dist,
                 scale=rng.uniform(0.95, 1.65), sink=rng.uniform(0.15, 0.28),
                 shadows=True, collider="keep", cull=0.01, min_self_sep=1.7)
    for s_idx in range(rng.randint(3, 4)):
        ang = rng.uniform(0, math.tau)
        dist = rng.uniform(1.8, 6.5)
        add_prop("DesertClusters", cname, rng.choice(SCRUB),
                 cx + math.cos(ang) * dist, cz + math.sin(ang) * dist,
                 scale=rng.uniform(0.85, 1.35), sink=0.08,
                 shadows=False, collider="remove", cull=0.008, min_self_sep=1.2)

# 6. Rusted Perimeter Hazard Fencing & Broken Warning Posts (dead zones, blast craters, Tier-3 approaches)
HAZARD_PERIMETERS = [
    ("Hazard line · reaper den south", -212.0, 118.0, 28.0),
    ("Hazard line · reaper den west", -278.0, 134.0, 112.0),
    ("Hazard line · post relay east", -396.0, 42.0, -18.0),
    ("Hazard line · post relay south", -418.0, -14.0, 74.0),
    ("Hazard line · fans camp north", -468.0, -76.0, 35.0),
    ("Hazard line · fans camp east", -454.0, -124.0, 102.0),
    ("Hazard line · southern cache rim", -222.0, -126.0, 52.0),
    ("Hazard line · central blast crater", -186.0, -48.0, 145.0),
    ("Hazard line · western dead zone", -352.0, -16.0, 88.0),
    ("Hazard line · north haul breach", -196.0, 44.0, -32.0),
]
for name, cx, cz, yaw in HAZARD_PERIMETERS:
    add_vignette("HazardPerimeters", name, cx, cz, yaw, [
        ("OuterBermsDepot/PHD_FencePost", -4.6, 0.2, 6.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/PHD_FencePanel", -2.2, 0.1, 4.0, 1.0, 0.14, True, "keep"),
        ("OuterBermsDepot/PHD_FencePost", 0.2, -0.2, -12.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/PHD_FencePanel", 2.8, 0.6, 19.0, 1.0, 0.16, True, "keep"),
        ("OuterBermsDepot/PHD_FencePost", 5.2, 1.4, 24.0, 1.0, 0.12, True, "keep"),
        ("OuterBermsDepot/DP_SignVoltagePost", -0.8, 2.1, -18.0, 1.0, 0.08, True, "keep", "arc"),
        ("WestGate/PH_JerseyBarrierA", 1.8, -2.3, 14.0, 1.0, 0.1, True, "keep"),
        ("StreetDressing/SD_fire_barrel", -3.2, -2.0, 40.0, 1.0, 0.05, True, "keep", "smoke"),
        ("OuterBermsDepot/DP_Cables", 0.4, -1.6, 75.0, 1.0, 0.04, False, "remove"),
    ], pad_marker=16.5, pad_col=5.0)

# 7. Industrial Ruin Silhouettes & Ambush Choke Points (dramatic cranes, walls, drone racks, scrap skips)
AMBUSH_CHOKE_POINTS = [
    ("Ambush choke · east haulway", -158.0, -6.0, 26.0),
    ("Ambush choke · central crane yard", -262.0, -52.0, 118.0),
    ("Ambush choke · relay corridor", -312.0, -24.0, 52.0),
    ("Ambush choke · northern gantry", -298.0, 88.0, 164.0),
    ("Ambush choke · west basin gate", -398.0, -62.0, 32.0),
    ("Ambush choke · derrick south cut", -358.0, 112.0, 205.0),
    ("Ambush choke · fans approach", -464.0, -18.0, 84.0),
    ("Ambush choke · south wash trench", -216.0, -96.0, 140.0),
]
for name, cx, cz, yaw in AMBUSH_CHOKE_POINTS:
    add_vignette("AmbushChokePoints", name, cx, cz, yaw, [
        ("OuterBermsDepot/PHD_Crane", 0.0, 0.0, 0.0, 0.96, 0.18, True, "keep", "arc"),
        ("OuterBermsDepot/DP_WallC", -5.2, 2.4, 15.0, 1.0, 0.14, True, "keep"),
        ("OuterBermsDepot/DP_WallD", 5.4, -2.2, -165.0, 1.0, 0.14, True, "keep"),
        ("OuterBermsDepot/DP_DroneRack", -3.4, -3.6, 62.0, 1.0, 0.1, True, "keep"),
        ("OuterBermsDepot/MX_ScrapHeapB", 3.6, 3.8, 128.0, 1.0, 0.16, True, "keep"),
        ("OuterBermsDepot/PHD_StorageCart", -1.6, 4.4, 210.0, 1.0, 0.08, True, "keep"),
        ("StreetDressing/SD_scrap_skip", 4.4, 0.8, 84.0, 1.0, 0.08, True, "keep"),
        ("StreetDressing/SD_fire_barrel", -4.8, -0.8, 20.0, 1.0, 0.05, True, "keep", "smoke"),
        ("OuterBermsDepot/DP_SignVoltagePost", 6.2, 2.8, -30.0, 1.0, 0.08, True, "keep"),
    ], pad_marker=17.5, pad_col=5.5)

# Verify every referenced prefab exists on disk
missing_prefabs = sorted({
    p["prefab"] for p in placements
    if not (PREFAB_ROOT / f"{p['prefab']}.prefab").is_file()
})
if missing_prefabs:
    raise FileNotFoundError(f"Missing prefabs on disk: {missing_prefabs}")

doc = {
    "version": 2,
    "created": "2026-11-21",
    "description": "Additive Outer Berms density & wasteland danger pass: industrial conveyor spines, fallen Quantum Tube branch ruins, Warden cover posts, skirmish wrecks, rusted hazard perimeters, industrial ambush choke points and desert boulder/scrub clusters with arc/smoke hazard FX tags.",
    "prefabs": placements,
}
OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

by_group = {}
by_hazard = {}
for p in placements:
    by_group[p["group"]] = by_group.get(p["group"], 0) + 1
    h = p.get("hazard")
    if h:
        by_hazard[h] = by_hazard.get(h, 0) + 1

print(f"Wrote {len(placements)} collision-checked Outer Berms placements to {OUT} (0 missing prefabs)")
for g, n in sorted(by_group.items()):
    print(f"  {g:20s}: {n}")
print(f"Hazard FX tags: {by_hazard}")
