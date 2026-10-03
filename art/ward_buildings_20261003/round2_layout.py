"""Round two (3 Oct 2026) layout edits, re-runnable: watchtower variants, new WB_* paint materials, moved/added review
cameras (cam_wb2_*). Run: python3 round2_layout.py (edits layout.json in place)."""
import json
from pathlib import Path
P = Path(__file__).with_name("layout.json")
L = json.loads(P.read_text())
B = {b["key"]: b for b in L["buildings"]}
M = L["materials"]
# painted steel on the isotropic sheet-steel set (VH_Paint's texture has horizontal streaks that slice into stripes on
# curved faces and its mid-grey base darkened every tint); colours above 1 compensate the 0.47 mean base map
M["WB_CylBone"] = {"set": "VH_SheetSteel", "color": [1.36, 1.36, 1.5], "tile": 1.0, "smooth": 0.85}
M["WB_CylRed"] = {"set": "VH_SheetSteel", "color": [0.98, 0.42, 0.38], "tile": 1.0, "smooth": 0.85}
M["WB_TankBone"] = {"set": "VH_SheetSteel", "color": [1.36, 1.34, 1.45], "tile": 1.6, "smooth": 0.8}
M["WB_TankTeal"] = {"set": "VH_SheetSteel", "color": [0.55, 0.98, 1.15], "tile": 1.6, "smooth": 0.8}
# watchtower variants: per-instance models, build-only keys for 2-4
t = B["watchtower"]
models = {"Watchtower NW (1)": "Watchtower", "Watchtower SW (2)": "Watchtower2", "Watchtower NE (3)": "Watchtower3", "Watchtower SE (4)": "Watchtower4"}
for inst in t["instances"]:
    inst["model"] = models[inst["name"]]
for k in (2, 3, 4):
    key = f"watchtower{k}"
    if key not in B:
        e = {"key": key, "model": f"Watchtower{k}", "buildOnly": True, "lods": 3, "lodDistances": t["lodDistances"],
             "_doc": "built for the watchtower key's instances (variant %d)" % k}
        L["buildings"].append(e)
        B[key] = e


def cams(b, new):
    names = {c["name"] for c in new}
    b["cameras"] = [c for c in b["cameras"] if c["name"] not in names] + new


cams(t, [
    {"name": "cam_wb2_tower_sw_top", "pos": [-47.0, 1.65, -29.5], "target": [-55.4, 10.4, -40.5], "fov": 50},
    {"name": "cam_wb2_tower_ne_gable", "pos": [45.3, 1.65, 29.0], "target": [43.4, 9.5, 40.0], "fov": 55},
    {"name": "cam_wb2_tower_se_shores", "pos": [35.0, 1.65, -39.0], "target": [42.0, 4.0, -41.5], "fov": 55},
    {"name": "cam_wb2_tower_nw_patch", "pos": [-47.5, 1.65, 33.5], "target": [-53.3, 4.5, 41.2], "fov": 55},
])
h = B["hall"]
cams(h, [
    {"name": "cam_wb2_hall_salvage", "pos": [33.0, 1.65, 18.5], "target": [35.5, 3.6, 28.0], "fov": 55},
    {"name": "cam_wb2_hall_scaffold", "pos": [31.0, 1.65, 23.2], "target": [34.2, 4.2, 27.4], "fov": 60},
    {"name": "cam_wb2_hall_cordon", "pos": [42.5, 1.65, 22.5], "target": [39.5, 2.2, 27.5], "fov": 55},
    {"name": "cam_wb2_hall_shearlegs", "pos": [37.0, 1.65, 30.8], "target": [42.5, 3.5, 34.2], "fov": 60},
    {"name": "cam_wb2_hall_bench", "pos": [33.2, 1.65, 32.5], "target": [29.5, 1.2, 34.0], "fov": 60},
])
n = B["nanofab"]
cams(n, [{"name": "cam_wb2_nanofab_gas", "pos": [44.9, 1.65, -27.5], "target": [43.2, 2.2, -33.5], "fov": 55}])
a = B["aquifer"]
for c in a["cameras"]:
    if c["name"] == "cam_wb_aquifer_market":       # round one's camera stood inside a market cloth
        c["pos"] = [-30.8, 1.65, -19.6]
        c["target"] = [-35.2, 3.4, -32.5]
cams(a, [{"name": "cam_wb2_aquifer_tanks_shade", "pos": [-30.5, 1.65, -42.4], "target": [-38.0, 3.0, -39.0], "fov": 55}])
s = B["tubeseg"]
cams(s, [{"name": "cam_wb2_tube_hatch_w", "pos": [-46.0, 1.65, 35.0], "target": [-43.7, 4.3, 41.9], "fov": 55}])
# West Gate bastions (replace the retrofit's `Gate defences`): root = street face at world x 44.0, rampart face 45.95
if "gatebastion" not in B:
    e = {"key": "gatebastion", "model": "GateBastion", "rootName": "Ward building: West Gate bastions",
         "cameraRoot": "Ward buildings review cameras: West Gate bastions", "lods": 3, "lodDistances": [20, 60, 500],
         "instances": [], "retire": ["Ward district retrofit/Gate defences"], "cameras": []}
    L["buildings"].append(e)
    B["gatebastion"] = e
    L["buildings"].append({"key": "gatebastionn", "model": "GateBastionN", "buildOnly": True, "lods": 3, "lodDistances": [20, 60, 500],
                           "_doc": "north bastion (mirrored gun position), used by the gatebastion key"})
g = B["gatebastion"]
g["instances"] = [{"name": "Gate bastion south (post 1)", "model": "GateBastion", "pos": [44.0, 0.0, -10.75], "yaw": 270},
                  {"name": "Gate bastion north (post 2)", "model": "GateBastionN", "pos": [44.0, 0.0, 22.5], "yaw": 270}]
g["cameras"] = [
    {"name": "cam_wb2_gate_spawn", "pos": [41.2, 1.65, -3.2], "target": [44.6, 1.2, -9.6], "fov": 55},
    {"name": "cam_wb2_gate_gun", "pos": [42.1, 1.65, -5.6], "target": [44.8, 1.4, -9.0], "fov": 60},
    {"name": "cam_wb2_gate_north", "pos": [40.8, 1.65, 14.0], "target": [44.6, 1.2, 21.6], "fov": 55},
    {"name": "cam_wb2_gate_apron", "pos": [35.5, 1.65, 3.5], "target": [45.0, 1.6, -7.5], "fov": 55},
]
P.write_text(json.dumps(L, indent=1))
print("layout updated")
