#!/usr/bin/env python3
"""West Gate outpost layout (Unity world metres). Writes layout.json, the single source used by
make_ground_splat.py and the Unity Editor pass (WestGateOutpostPass). y: number = absolute, "ground" =
Berms ground height at (x, z), "ground-min" = lowest ground under the footprint radius r (walls on slopes).
Yaw follows Unity (degrees about +Y)."""
import json, math
from pathlib import Path

S = "Structures/"; P = "Props/"
items = []
def put(prefab, name, x, z, y="ground", yaw=0.0, scale=1.0, r=0.0, group="Outpost", drift=0.0, collider=True):
    items.append(dict(prefab=prefab, name=name, x=x, z=z, y=y, yaw=yaw, scale=scale, r=r, group=group, drift=drift, collider=collider))

# --- gate
put(S + "WG_GatePortal", "West Gate portal", -59.0, 1.0, 0.0, group="Gate")
put(S + "WG_GateRail", "Sliding gate rail", -60.41, 0.9, 0.0, group="Gate")
put(S + "WG_SlidingGate", "Sliding gate leaf (parked open)", -60.41, 8.85, 0.1, group="Gate", drift=.6)
for i, (x, z) in enumerate(((-59.95, -1.9), (-59.95, 3.9))):
    put(P + "PH_SecurityLight", f"Gantry floodlight west {i + 1}", x, z, 6.72, -90, group="Gate", collider=False)
for i, (x, z) in enumerate(((-58.05, -1.9), (-58.05, 3.9))):
    put(P + "PH_SecurityLight", f"Gantry floodlight east {i + 1}", x, z, 6.72, 90, group="Gate", collider=False)
put(P + "PH_SecurityCamera", "Gantry camera", -59.95, -2.7, 6.2, -90, group="Gate", collider=False)
put(P + "PH_PowerBox", "Gate junction box", -57.72, 4.6, 0.85, 90, group="Gate", collider=False)
# --- guard post
put(S + "WG_GuardPost", "Warden post container", -71.65, -5.9, -1.38, 0, drift=1.2)
put(S + "WG_ShadeNet", "Issue canopy", -71.9, -4.68, -1.48, 0)
put(S + "WG_SandbagRoofRow", "Roof sandbags north", -71.3, -4.98, 1.23, 0, collider=False)
put(S + "WG_SandbagRoofRow", "Roof sandbags south", -73.4, -6.82, 1.23, 180, collider=False)
put(S + "WG_SandbagRoofRow", "Roof sandbags east", -69.0, -5.9, 1.23, 90, collider=False)
put(S + "WG_SandbagPile", "Roof sandbag pile", -74.0, -5.0, 1.23, 30, collider=False)
put(P + "PH_Searchlight", "Roof searchlight", -73.85, -5.15, 1.62, 20, collider=False)
put(P + "PH_AirconRusted", "Post air conditioner", -72.45, -7.5, "ground", 180)
put(P + "PH_Generator", "Post generator", -67.7, -6.75, "ground", -80, drift=.4)
put(P + "PH_Jerrycan", "Fuel can", -67.1, -7.35, "ground", 15)
put(P + "PH_Jerrycan", "Fuel can", -67.45, -7.55, "ground", 40)
put(P + "PH_PropaneTank", "Propane tank", -68.35, -7.75, "ground", 0)
put(P + "PH_BarrelRed", "Fuel drum", -68.9, -7.6, "ground", 30)
put(P + "PH_BarrelBlue", "Water drum", -75.25, -6.55, "ground", 0)
put(P + "PH_BarrelBlue", "Water drum", -75.4, -5.85, "ground", 70)
put(P + "PH_RadioSet", "Post radio", -69.52, -5.35, -0.41, 90, collider=False)
put(P + "PH_Clipboard", "Issue clipboard", -70.95, -4.45, -0.32, 10, collider=False)
put(P + "PH_Binoculars", "Issue binoculars", -70.2, -4.5, -0.32, -30, collider=False)
put(P + "PH_WallLamp", "Issue window lamp", -70.53, -4.63, 0.95, 0, collider=False)
put(P + "PH_WallLamp", "Post door lamp", -68.58, -6.6, 0.9, 90, collider=False)
put(S + "WG_ArmsLocker", "Arms locker visual", -72.3, -4.36, "ground", 180)
put(P + "PH_WoodenMilitaryCrate", "Arms crate", -73.45, -4.35, "ground", 0)
put(P + "PH_AmmoBox", "Nano cell case", -73.7, -4.3, "ground+0.465", 80, collider=False)
put(P + "PH_AmmoBox", "Nano cell case", -73.25, -4.4, "ground+0.465", 95, collider=False)
put(P + "PH_MilitaryCrateA", "Field case", -74.35, -3.75, "ground", 32)
put(P + "PH_MonoblocChair", "Warden chair", -73.55, -3.35, "ground", 150)
put(P + "PH_HandTruck", "Hand truck", -68.35, -4.4, "ground", 60, collider=False)
put(S + "WG_SandbagPile", "Sandbag pile (post west)", -75.3, -4.7, "ground-min", 10, r=.7)
put(S + "WG_SandbagWall2mLow", "Sandbag skirt (post west)", -74.95, -6.1, "ground-min", 90, r=1.0)
# --- lane furniture
put(S + "WG_BoomBarrier", "Checkpoint boom barrier", -67.2, -2.75, "ground", -90)
put(S + "WG_NoticeBoard", "Field briefing board", -64.3, -4.4, "ground", -135, drift=.3)
put(P + "PH_TrashCanRust", "Bin", -63.1, -5.3, "ground", 20)
put(P + "PH_OldTyre", "Old tyre", -62.6, -5.9, "ground", 0, collider=False)
put(P + "PH_OldTyre", "Old tyre", -62.62, -5.88, "ground+0.165", 35, collider=False)
put(S + "WG_SandbagCurveHigh", "Sentry sandbag nest", -60.25, -3.55, "ground-min", 180, r=1.6, drift=.5)
put(S + "WG_SandbagPile", "Sandbag pile (boom)", -66.3, -3.45, "ground", 60)
put(P + "PH_JerseyBarrierA", "Jersey barrier", -65.55, -3.2, "ground", 12, drift=.4)
put(P + "PH_JerseyBarrierB", "Jersey barrier", -76.0, -3.7, "ground", -18, drift=.4)
put(P + "PH_JerseyBarrierA", "Jersey barrier", -61.7, 5.7, "ground", 80, drift=.3)
put(P + "PH_JerseyBarrierA", "Jersey barrier (range)", -69.1, 3.55, "ground", 2, drift=.5)
put(P + "PH_JerseyBarrierB", "Jersey barrier (range)", -70.85, 3.6, "ground", -3, drift=.5)
put(P + "PH_JerseyBarrierA", "Jersey barrier (range)", -73.6, 3.15, "ground", 8, drift=.5)
put(P + "PH_JerseyBarrierB", "Jersey barrier (range)", -75.35, 2.7, "ground", 14, drift=.5)
put(S + "WG_LightTower", "Light tower", -67.9, 5.4, "ground", 150)
# --- range
put(S + "WG_FiringBench", "Firing bench", -66.9, 8.2, "ground", -62.7)
put(S + "WG_SandbagWall2mLow", "Firing point sandbags (front)", -67.75, 8.62, "ground-min", -62.7, r=1.0)
put(S + "WG_SandbagWall2mHigh", "Firing point sandbags (side)", -66.0, 9.3, "ground-min", -152.7, r=1.0, drift=.4)
put(S + "WG_SandbagPile", "Sandbag pile (range)", -67.1, 6.35, "ground", 20)
put(S + "WG_RangeSign", "Training range sign", -65.6, 4.55, "ground", -53)
put(S + "WG_LiveFireSign", "Live fire sign", -70.2, 4.05, "ground", 0)
put(S + "WG_RangeControlSign", "Range control post", -68.6, 6.9, "ground", -90)
put(P + "PH_PowerBox", "Range control box", -68.6, 6.9, "ground+0.72", -90, collider=False)
put(S + "WG_RangeFlag", "Range flag", -68.4, 11.0, "ground", 0)
# --- rocks and plants (kept clear of the lane, firing lanes and interaction stand points)
put(P + "PH_BoulderA", "Boulder", -76.6, -7.6, "ground-min", 40, .9, r=1.0, group="Terrain dressing", drift=.8)
put(P + "PH_BoulderB", "Boulder", -63.3, 12.6, "ground-min", 120, .55, r=.8, group="Terrain dressing", drift=.6)
put(P + "PH_BoulderC", "Boulder", -77.8, 5.6, "ground-min", 200, .6, r=.8, group="Terrain dressing", drift=.6)
put(P + "PH_BoulderA", "Boulder", -64.8, -7.5, "ground-min", 10, .5, r=.6, group="Terrain dressing", drift=.5)
put(P + "PH_BoulderC", "Boulder", -61.6, -8.8, "ground-min", 290, .45, r=.6, group="Terrain dressing", drift=.5)
plants = [("PH_RooibosA", -61.2, 14.2, 0), ("PH_RooibosB", -61.5, 15.6, 80), ("PH_SearsiaSmall", -62.2, 17.0, 200), ("PH_DideltaSmall", -61.0, -6.4, 30),
          ("PH_RooibosC", -61.4, -7.3, 140), ("PH_SearsiaSmall", -61.6, -10.4, 60), ("PH_RooibosA", -70.3, -8.1, 220), ("PH_DideltaSmall", -73.9, -8.3, 10),
          ("PH_RooibosB", -76.3, -5.1, 300), ("PH_RooibosC", -69.6, 6.9, 100), ("PH_DideltaSmall", -64.0, 6.3, 45), ("PH_RooibosA", -63.3, 9.4, 170),
          ("PH_SearsiaSmall", -79.5, -4.8, 20), ("PH_RooibosB", -65.9, -6.4, 260), ("PH_DryBranchA", -64.3, -6.2, 30), ("PH_DryBranchB", -74.8, 4.2, 110),
          ("PH_RooibosC", -76.9, 3.7, 20), ("PH_DideltaSmall", -71.8, 5.4, 300)]
for name, x, z, yaw in plants:
    put(P + name, name.replace("PH_", "").lower(), x, z, "ground", yaw, group="Terrain dressing", collider=False, drift=.3)

# --- gameplay anchors (moved objects keep their components, IDs and references)
anchors = {
    "ossa": dict(x=-69.4, z=-3.25, yaw=35), "rell": dict(x=-61.6, z=-1.3, yaw=290),
    "locker": dict(x=-72.3, z=-4.36, yaw=180), "board": dict(x=-64.3, z=-4.4, yaw=-135),
    "range_reset": dict(x=-68.6, z=6.9, yaw=-90), "respawn": dict(x=-68.6, z=-1.2, yaw=60),
    "landmarks": {"checkpoint_approach": [-57.0, 1.0], "checkpoint_ossa": [-68.6, -2.1], "checkpoint_rell": [-62.82, -0.86],
                  "checkpoint_board": [-63.38, -3.48], "checkpoint_locker": [-72.3, -3.15], "checkpoint_firingline": [-66.2, 7.6],
                  "checkpoint_range_reset": [-67.45, 6.9], "checkpoint_road": [-76.0, -6.0]},
    "road": [[-59.9, 1.0], [-66.5, 0.8], [-72.0, 0.2], [-77.0, -1.5], [-82.0, -8.0], [-85.0, -20.0], [-83.0, -31.0], [-80.0, -37.0], [-80.0, -41.0]],
    "apron": dict(x0=-66.6, x1=-60.0, z0=-3.1, z1=5.1),
}
# --- pebble / rock scatter: shoulders, wall base, mound flanks; clear of the lane, firing lanes and stand points
import random
rnd = random.Random(2609)
def seg_d(px, pz, a, b):
    ax, az = a; bx, bz = b; dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz
    t = max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L2)); return math.hypot(px - ax - t * dx, pz - az - t * dz)
road = anchors["road"]; ap = anchors["apron"]
fire = [((-66.2, 7.6), p) for p in ((-78, 11), (-80.5, 15.5), (-77.5, 20))]
stands = [tuple(v) for v in anchors["landmarks"].values()] + [(a["x"], a["z"]) for k, a in anchors.items() if isinstance(a, dict) and "x" in a]
solid = [(it["x"], it["z"], 1.6 if it["prefab"].startswith(S) else .9) for it in items]
kinds = [("PH_RockA", 1.4, 3.2), ("PH_RockB", 1.6, 3.6), ("PH_RockC", 1.6, 3.6), ("PH_RockD", 1.4, 3.0), ("PH_StonesA", 2.0, 4.5), ("PH_StonesB", 1.6, 3.5), ("PH_StonesC", 1.6, 3.5)]
placed = 0; tries = 0
while placed < 190 and tries < 20000:
    tries += 1
    x, z = rnd.uniform(-82, -60.6), rnd.uniform(-14, 19)
    rd = min(seg_d(x, z, a, b) for a, b in zip(road[:-1], road[1:]))
    if rd < 2.3: continue
    if ap["x0"] - .4 < x < ap["x1"] and ap["z0"] - .4 < z < ap["z1"] + .4: continue
    if -75.6 < x < -67.8 and -7.8 < z < -2.3: continue            # post, canopy and issue area
    if any(seg_d(x, z, a, b) < 1.1 for a, b in fire): continue
    if any(math.hypot(x - sx, z - sz) < 1.6 for sx, sz in stands): continue
    if any(math.hypot(x - sx, z - sz) < r for sx, sz, r in solid): continue
    # bias: denser near the wall base, the lane shoulders and mound flanks
    w = .25 + .75 * math.exp(-(rd - 2.3) / 3) + .6 * math.exp(-(x + 60.5) ** 2 / 3)
    if rnd.random() > w: continue
    k, s0, s1 = rnd.choice(kinds)
    put(P + k, "scatter " + k[3:].lower(), round(x, 2), round(z, 2), "ground-min", round(rnd.uniform(0, 360)), round(rnd.uniform(s0, s1), 2),
        r=.12, group="Scatter", collider=False)
    placed += 1
print("scatter", placed)

# --- URP decals: kind, centre (x, y|"ground", z), size (w, len, depth), direction of the length axis (x, z),
# projection "down" (onto the ground) or a horizontal vector (onto a wall face), opacity
decals = []
def decal(kind, x, z, w, l, depth=1.6, dx=-1.0, dz=0.0, proj="down", y="ground", fade=1.0):
    decals.append(dict(kind=kind, x=x, z=z, y=y, w=w, l=l, depth=depth, dx=dx, dz=dz, proj=proj, fade=fade))
decal("WG_DecalTyreTracks", -63.3, 0.9, 2.4, 7.0, depth=2.6, fade=.85)
decal("WG_DecalTyreTracks", -63.6, 1.3, 2.4, 6.0, depth=2.6, fade=.45)
decal("WG_DecalTyreTracks", -70.2, 0.45, 2.4, 8.0, dx=-1, dz=-.08, fade=.8)
decal("WG_DecalTyreTracks", -75.8, -0.95, 2.4, 8.0, dx=-.92, dz=-.4, fade=.7)
decal("WG_DecalTyreTracks", -80.2, -5.0, 2.4, 8.0, dx=-.6, dz=-.8, fade=.6)
for x, z, s_, f in ((-61.9, 2.4, 1.1, .8), (-66.3, -1.8, .9, .7), (-72.6, 0.9, 1.5, .6), (-67.75, -6.75, 1.4, .9), (-68.2, -7.5, .9, .7)):
    decal("WG_DecalOilStain", x, z, s_, s_, depth=1.2, dx=.3, dz=1, fade=f)
for x, z, w, l, dx, dz in ((-58.7, -1.9, 1.6, 1.2, 0, 1), (-60.9, -2.55, 2.2, 1.6, 1, .3), (-60.9, 4.5, 2.0, 1.5, 1, -.3), (-60.9, 9.0, 1.3, 7.0, 0, 1),
                           (-68.1, -4.5, 1.6, 1.4, 1, 0), (-64.3, -4.2, 1.5, 1.2, 1, 1), (-62.0, -3.8, 1.8, 1.4, 1, .2), (-66.6, 8.6, 2.0, 1.5, .4, .9)):
    decal("WG_DecalSandSpill", x, z, w, l, depth=1.4, dx=dx, dz=dz, fade=.9)
# grime skirts on vertical faces: projection vector points into the face
decal("WG_DecalGrime", -71.65, -4.42, 6.0, 0.9, depth=.6, dx=1, dz=0, proj=(0, 0, -1), y=-1.0, fade=.8)
decal("WG_DecalGrime", -71.65, -7.38, 6.0, 0.9, depth=.6, dx=1, dz=0, proj=(0, 0, 1), y=-1.0, fade=.7)
decal("WG_DecalGrime", -60.18, -8.0, 9.0, 1.2, depth=.5, dx=0, dz=1, proj=(1, 0, 0), y=0.2, fade=.75)
decal("WG_DecalGrime", -60.18, 17.0, 8.0, 1.2, depth=.5, dx=0, dz=1, proj=(1, 0, 0), y=0.2, fade=.75)
anchors["decals"] = decals

out = {"items": items, "anchors": anchors}
Path(__file__).with_name("layout.json").write_text(json.dumps(out, indent=1))
print(len(items), "placements")
