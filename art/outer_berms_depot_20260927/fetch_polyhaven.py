#!/usr/bin/env python3
"""Fetch the CC0 Poly Haven sources for the Outer Berms depot pass (27 Sep 2026) into ./polyhaven.
Reuses the West Gate downloader (2k glTF models, 2k JPG texture maps; md5-checked); records authors/licence
in polyhaven/manifest.json. Sources already fetched by West Gate are reused from that folder instead."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "west_gate_20260926"))
import fetch_polyhaven as wg
wg.ROOT = HERE / "polyhaven"
MODELS = """overhead_crane modular_industrial_pipes_01 rusted_wheel_rim_01 rusted_wheel_rim_02 hanging_industrial_lamp
namaqualand_boulder_05 namaqualand_boulder_06 metal_tool_chest industrial_storage_cart small_lpg_tank""".split()
TEXTURES = """rusty_corrugated_iron rusty_metal_03 rusty_metal_04 metal_grate_rusty rusty_metal_grid concrete_floor_worn_001
concrete_wall_004 concrete_debris box_profile_metal_sheet rubberized_track rust_coarse_01 rusted_shutter chipped_concrete""".split()
if __name__ == "__main__":
    mp = wg.ROOT / "manifest.json"; man = json.loads(mp.read_text()) if mp.exists() else {}
    with ThreadPoolExecutor(8) as ex:
        jobs = [ex.submit(wg.model, a) for a in MODELS] + [ex.submit(wg.texture, a) for a in TEXTURES]
        for j in jobs:
            try:
                aid, rec = j.result(); man[aid] = rec; print("ok", aid, flush=True)
            except Exception as e:
                print("FAILED", e, file=sys.stderr, flush=True)
    wg.ROOT.mkdir(parents=True, exist_ok=True); mp.write_text(json.dumps(man, indent=1, sort_keys=True))
