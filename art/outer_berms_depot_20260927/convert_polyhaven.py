"""Blender 5.2 batch conversion of the depot's Poly Haven CC0 props (27 Sep 2026) into Unity-ready GLBs.
Run: blender -b --python-exit-code 1 -P convert_polyhaven.py [-- Name ...]
Executes the West Gate converter's functions (LOD0..n meshes, origin at ground-contact centre, PH_ materials,
no embedded images) with the output redirected to Art/OuterBermsDepot/Props; records polyhaven-conversion.json."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
WG = HERE.parent / "west_gate_20260926"
src = (WG / "convert_polyhaven.py").read_text()
ns = {"__file__": str(WG / "convert_polyhaven.py"), "__name__": "wg_convert"}
exec(src[:src.index("only = sys.argv")], ns)
ns["OUT"] = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/OuterBermsDepot/Props"
ns["OUT"].mkdir(parents=True, exist_ok=True)
ns["REPORT"].clear()
_dec = ns["decimate"]
def _decimate(obj, ratio):
    if obj.data.shape_keys: obj.shape_key_clear()   # some scans ship shape keys; LOD decimation needs them gone
    _dec(obj, ratio)
ns["decimate"] = _decimate
JOBS = {
    "PHD_WheelRimA": ("rusted_wheel_rim_01", "*", 6000, [.3]),
    "PHD_WheelRimB": ("rusted_wheel_rim_02", "*", 6000, [.3]),
    "PHD_HangingLamp": ("hanging_industrial_lamp", "*", 5000, [.3]),
    "PHD_ToolChest": ("metal_tool_chest", "*", 6000, [.3]),
    "PHD_StorageCart": ("industrial_storage_cart", "*", 9000, [.3]),
    "PHD_LpgTank": ("small_lpg_tank", "*", 6000, [.3]),
    "PHD_BoulderD": ("namaqualand_boulder_05", "*", 14000, [.25, .07]),
    "PHD_BoulderE": ("namaqualand_boulder_06", "*", 14000, [.25, .07]),
    "PHD_Crane": ("overhead_crane", "*", 40000, [.3, .1]),
    "PHD_FencePanel": ("modular_chainlink_fence", ["modular_chainlink_fence"], None, [.4]),
    "PHD_FencePost": ("modular_chainlink_fence", ["modular_chainlink_fence_post"], None, [.4]),
}
only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for out, (asset, parts, lod0, ratios) in JOBS.items():
    if only and out not in only:
        continue
    ns["SRC"] = HERE / "polyhaven/models" if (HERE / "polyhaven/models" / asset).exists() else WG / "polyhaven/models"
    ns["run"](out, asset, parts, lod0, ratios)
rp = HERE / "polyhaven-conversion.json"
old = json.loads(rp.read_text()) if rp.exists() else {}
old.update(ns["REPORT"]); rp.write_text(json.dumps(old, indent=1))
