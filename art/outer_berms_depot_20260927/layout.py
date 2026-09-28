#!/usr/bin/env python3
"""Outer Berms machine depot layout (Unity world metres) -> layout.json, the single source used by the Unity pass
(Editor/OuterBermsDepotPass: ground drifts, apron, placements, spawns, lights, decals, cameras, landmarks) and by the
ground splat (art/west_gate_20260926/make_ground_splat.py, depot section).

prefab: "DP:<name>" = Prefabs/OuterBermsDepot, "WG:<name>" = Prefabs/WestGate.
y: number = absolute, "ground" = walkable ground at (x, z), "ground+d" / "ground-d", "ground-min" = lowest ground
under radius r (walls on slopes). rot = Unity Euler (overrides yaw)."""
import json
from pathlib import Path

items = []
def put(prefab, name, x, z, y="ground", yaw=0.0, rot=None, scale=1.0, r=0.0, group="Props", collider=True):
    items.append(dict(prefab=prefab, name=name, x=x, z=z, y=y, yaw=yaw, rot=rot, scale=scale, r=r, group=group, collider=collider))

HALL = (-79.75, 0.12, -48.0)
# --- structures (site-specific pieces share the hall anchor)
put("DP:DP_Hall", "Processing hall (ruin)", HALL[0], HALL[2], HALL[1], group="Structures")
put("DP:DP_DroneRack", "Drone docking rail", HALL[0], HALL[2], HALL[1], group="Structures")
put("DP:DP_Cables", "Power cables", HALL[0], HALL[2], HALL[1], group="Structures", collider=False)
put("DP:DP_Conveyor", "Conveyor spine", -88.4, -46.0, 0.0, group="Structures")
put("DP:DP_Plinth", "Cradle plinth", -80.4, -39.4, 0.5, group="Power cradles")
put("DP:DP_Cradle", "Charging cradle west", -83.0, -39.4, 0.5, 15, group="Power cradles")
put("DP:DP_Cradle", "Charging cradle centre", -80.4, -39.4, 0.5, 80, group="Power cradles")
put("DP:DP_CradleBroken", "Charging cradle east (broken)", -77.8, -39.4, 0.5, 200, group="Power cradles")
put("DP:DP_SignHallPlate", "Hall sign", -85.3, -44.32, 5.05, 0, group="Structures", collider=False)
put("DP:DP_SignVoltagePost", "High voltage sign", -76.05, -37.75, "ground", 25, group="Power cradles")
# --- broken perimeter walls
put("DP:DP_WallC", "West retaining wall", -87.75, -36.2, "ground-min", 90, r=1.6, group="Walls")
put("DP:DP_WallA", "West retaining wall", -87.95, -39.8, "ground-min", 93, r=1.5, group="Walls")
put("DP:DP_WallB", "West retaining wall (broken end)", -87.3, -33.15, "ground-min", 78, r=1.2, group="Walls")
put("DP:DP_WallA", "East yard wall", -72.7, -41.6, "ground-min", 88, r=1.5, group="Walls")
put("DP:DP_WallD", "East yard wall (stub)", -72.95, -37.6, "ground-min", 95, r=.9, group="Walls")
put("DP:DP_WallB", "East yard wall (broken end)", -73.4, -34.4, "ground-min", 64, r=1.2, group="Walls")
put("DP:DP_WallD", "Toppled wall panel", -75.4, -32.2, "ground+0.12", rot=[86, 30, 0], group="Walls")
# --- scrap and dead machines
put("DP:MX_ScrapHeapA", "Stripped scrap heap", -75.4, -45.2, "ground-min", 30, r=1.6, group="Scrap")
put("DP:MX_ScrapHeapB", "Machine debris", -86.0, -37.9, "ground-min", 100, r=1.2, group="Scrap")
put("DP:MX_ScrapHeapB", "Machine debris (hall)", -78.4, -46.9, "ground-min", 250, r=1.2, group="Scrap")
put("DP:DP_DeadWorker", "Stripped worker droid carcass", -84.7, -42.95, "ground", 205, group="Scrap")
put("DP:DP_CrashedDrone", "Crashed scrap drone", -74.6, -40.95, "ground-0.12", rot=[18, 40, 28], group="Scrap")
put("DP:PHD_WheelRimA", "Wheel rim", -78.4, -35.2, "ground+0.18", rot=[78, 10, 0], group="Scrap", collider=False)
put("DP:PHD_WheelRimB", "Wheel rim", -83.4, -42.0, "ground", 40, group="Scrap", collider=False)
put("DP:PHD_ToolChest", "Tool chest", -84.25, -44.35, "ground", 168, group="Props")
put("DP:PHD_StorageCart", "Tipped storage cart", -72.9, -45.9, "ground", rot=[0, 40, 12], group="Props")
put("DP:PHD_LpgTank", "Gas bottle (fallen)", -86.9, -44.6, "ground+0.2", rot=[90, 25, 0], group="Props", collider=False)
put("DP:PHD_HangingLamp", "Hanging lamp (dead)", -84.3, -48.4, 4.72, group="Structures", collider=False)
put("WG:PH_PowerBox", "Power cabinet", -81.3, -44.1, "ground", 180, group="Power cradles")
put("WG:PH_UtilityBox", "Distribution box", -80.15, -44.28, "ground", 180, group="Power cradles")
put("WG:PH_BarrelRed", "Oil drum", -86.4, -43.2, "ground", 20)
put("WG:PH_BarrelBlue", "Oil drum (spilled)", -86.95, -42.35, "ground+0.3", rot=[90, 60, 0])
put("WG:PH_Jerrycan", "Jerrycan", -83.9, -43.6, "ground", 35, collider=False)
put("WG:PH_OldTyre", "Old tyre", -73.8, -43.9, "ground", 0, collider=False)
put("WG:PH_OldTyre", "Old tyre", -73.75, -43.85, "ground+0.165", 35, collider=False)
put("WG:PH_OldTyre", "Old tyre (on edge)", -74.7, -36.3, "ground+0.38", rot=[90, 30, 0], collider=False)
put("WG:PH_TrashCanRust", "Bin (tipped)", -76.1, -35.3, "ground+0.28", rot=[0, 0, 90], collider=False)
# --- perimeter fence remnants at the road entry
put("DP:PHD_FencePost", "Fence post", -84.4, -32.45, "ground-0.1", 0, group="Fence")
put("DP:PHD_FencePost", "Fence post", -77.05, -32.85, "ground-0.1", 0, group="Fence")
put("DP:PHD_FencePost", "Fence post", -75.2, -33.0, "ground-0.1", 0, group="Fence")
put("DP:PHD_FencePanel", "Fence panel", -76.6, -32.9, "ground-0.05", 0, group="Fence")
put("DP:PHD_FencePanel", "Fence panel (leaning)", -75.65, -33.05, "ground-0.05", rot=[-14, 0, 6], group="Fence")
put("DP:PHD_FencePanel", "Fence panel (fallen)", -83.2, -31.3, "ground+0.04", rot=[90, 15, 0], group="Fence", collider=False)
# --- rocks and scrub at the margins
put("WG:PH_BoulderA", "Boulder", -70.8, -33.4, "ground-min", 40, r=.8, group="Terrain dressing")
put("DP:PHD_BoulderD", "Boulder", -89.4, -31.2, "ground-min", 10, r=.7, group="Terrain dressing")
put("DP:PHD_BoulderE", "Boulder", -90.6, -35.5, "ground-min", 70, r=.4, group="Terrain dressing")
put("WG:PH_BoulderC", "Boulder", -70.9, -47.4, "ground-min", 200, r=.8, group="Terrain dressing")
for i, (x, z, k) in enumerate([(-74.1, -31.4, "A"), (-86.2, -30.8, "B"), (-71.6, -44.9, "C"), (-89.1, -41.5, "D"), (-82.6, -33.1, "B"), (-77.9, -44.0, "A")]):
    put(f"WG:PH_Rock{k}", "Rock", x, z, "ground-min", i * 67.0, r=.3, group="Terrain dressing", collider=False)
for i, (x, z, k) in enumerate([(-78.9, -33.6, "A"), (-85.4, -34.3, "B"), (-72.2, -39.8, "C"), (-81.0, -45.3, "A"), (-74.0, -38.2, "B")]):
    put(f"WG:PH_Stones{k}", "Stones", x, z, "ground", i * 53.0, group="Terrain dressing", collider=False)
put("WG:PH_DryBranchA", "Dry scrub", -88.8, -33.8, "ground", 20, group="Terrain dressing", collider=False)
put("WG:PH_RooibosB", "Scrub", -90.2, -38.4, "ground", 140, group="Terrain dressing", collider=False)
put("WG:PH_SearsiaSmall", "Scrub", -70.6, -46.5, "ground", 60, group="Terrain dressing", collider=False)
put("WG:PH_DryBranchB", "Dry scrub", -74.3, -48.0, "ground", 200, group="Terrain dressing", collider=False)
put("WG:PH_RooibosA", "Scrub", -71.4, -30.6, "ground", 300, group="Terrain dressing", collider=False)

anchors = {
    "hall": HALL,
    # sand drifts added to the walkable ground (x, z, rx, rz, h, yaw)
    "drifts": [
        dict(x=-86.7, z=-39.5, rx=1.3, rz=2.2, h=.32, yaw=0),      # spill through the west wall notch
        dict(x=-86.9, z=-35.9, rx=1.0, rz=2.0, h=.22, yaw=0),      # banked against the west wall
        dict(x=-73.6, z=-41.4, rx=.9, rz=2.1, h=.2, yaw=0),        # lee of the east wall
        dict(x=-75.8, z=-47.4, rx=2.6, rz=1.6, h=.35, yaw=20),     # sand blown into the sheared east bay
        dict(x=-83.6, z=-46.2, rx=2.2, rz=1.2, h=.18, yaw=0),      # inside the hall's north line
    ],
    # yard apron (cracked concrete mesh), cut where the ground rises into drifts
    "apron": dict(x0=-87.2, x1=-72.9, z0=-44.2, z1=-32.6, cut_height=.4),
    # encounter spawns (Machine depot nest): worker between plinth and hall, worker east of the plinth, drone west
    "spawns": [dict(x=-82.2, z=-42.4, face=[-80.5, -33.0]), dict(x=-75.2, z=-38.7, face=[-80.5, -33.0]), dict(x=-84.9, z=-36.9, face=[-80.5, -31.0])],
    "landmarks": {"depot_approach": [-82.6, -28.4], "depot_yard": [-80.6, -36.2], "depot_hall": [-80.2, -45.6]},
    "carcass": dict(x=-86.0, z=-47.6, y="ground-0.45", rot=[9, 118, -14]),
    "decals": [
        dict(kind="DP_DecalOilPool", x=-81.8, z=-37.5, w=2.2, l=1.6, dx=1, dz=.2, depth=1.2, fade=.9),
        dict(kind="DP_DecalOilPool", x=-78.2, z=-41.5, w=1.8, l=1.4, dx=.3, dz=1, depth=1.2, fade=.85),
        dict(kind="DP_DecalOilPool", x=-84.1, z=-41.7, w=1.5, l=1.5, dx=1, dz=-.4, depth=1.2, fade=.8),
        dict(kind="DP_DecalOilPool", x=-80.4, z=-35.6, w=1.3, l=1.0, dx=1, dz=.6, depth=1.0, fade=.7),
        dict(kind="DP_DecalOilPool", x=-86.2, z=-42.6, w=1.6, l=2.4, dx=.2, dz=1, depth=1.4, fade=.9),
        dict(kind="DP_DecalScorch", x=-77.7, z=-39.3, w=3.2, l=3.2, dx=1, dz=0, depth=2.2, fade=.95),
        dict(kind="DP_DecalScorch", x=-74.6, z=-41.0, w=2.2, l=2.6, dx=.6, dz=1, depth=1.4, fade=.8),
        dict(kind="DP_DecalSprayKeepOut", x=-87.36, z=-36.3, y=1.0, w=2.3, l=1.15, dx=0, dz=1, depth=.7, fade=.95, proj=[-1, 0, 0]),
        dict(kind="DP_DecalSprayCount", x=-73.05, z=-41.3, y=.85, w=1.1, l=.55, dx=0, dz=1, depth=.7, fade=.9, proj=[1, 0, 0]),
        dict(kind="WG_DecalTyreTracks", x=-81.4, z=-34.6, w=2.6, l=5.5, dx=.25, dz=-1, depth=1.0, fade=.75),
        dict(kind="WG_DecalSandSpill", x=-86.6, z=-37.8, w=1.8, l=3.6, dx=0, dz=1, depth=1.2, fade=.8),
        dict(kind="WG_DecalSandSpill", x=-73.5, z=-39.6, w=1.4, l=3.0, dx=0, dz=1, depth=1.2, fade=.7),
        dict(kind="WG_DecalGrime", x=-80.4, z=-38.0, w=7.8, l=1.0, dx=1, dz=0, depth=1.6, fade=.6),
    ],
    "cameras": {
        "cam_depot_approach": [[-83.2, 1.7, -27.6], [-80.5, 1.3, -42.0], 60],
        "cam_depot_yard": [[-74.3, 1.65, -34.2], [-82.5, 1.6, -44.5], 62],
        "cam_depot_cradles": [[-79.4, 1.6, -35.3], [-80.4, 1.2, -39.6], 58],
        "cam_depot_hall": [[-77.8, 1.65, -41.6], [-84.5, 3.2, -49.0], 64],
        "cam_depot_conveyor": [[-83.8, 1.7, -35.4], [-94.5, 6.2, -39.5], 62],
        "cam_depot_aerial": [[-65.5, 15.0, -23.5], [-81.0, 0.0, -42.0], 55],
        "cam_depot_west": [[-89.4, 1.7, -30.4], [-78.0, 1.8, -44.0], 60],
        "cam_depot_fight": [[-81.0, 1.75, -32.0], [-80.4, 1.1, -40.5], 55],
    },
}
Path(__file__).with_name("layout.json").write_text(json.dumps({"items": items, "anchors": anchors}, indent=1))
print(len(items), "items")
