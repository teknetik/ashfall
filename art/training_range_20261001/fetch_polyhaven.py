#!/usr/bin/env python3
"""Fetch CC0 Poly Haven sources for the Warden training range pass (1 Oct 2026).
Workshop and range-master objects a scan does better than hand modelling (bench vice, megaphone, multimeter, compressor,
welding cart, caged work lamp, spade, sledgehammer) and two tiling wood textures for the Blender-authored timber
(posts, sleepers, bay dividers, benches). Unbranded assets only. Models go to polyhaven/models/<id>/, textures to
polyhaven/textures/<id>/, and polyhaven/manifest.json records names, authors, licence and source URLs.
Reuses the fetch helpers of art/street_dressing_20260930/fetch_polyhaven.py."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "street_dressing_20260930"))
import fetch_polyhaven as F  # noqa: E402

F.ROOT = HERE / "polyhaven"
F.MODELS = {aid: "2k" for aid in ["bench_vice_01", "Megaphone_01", "retro_multimeter", "old_military_compressor",
                                  "portable_welding_cart", "caged_hanging_light", "rusted_spade_01", "sledgehammer_01"]}
F.TEXTURES = {"rough_wood": "2k", "wood_planks_grey": "2k"}

if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(F.model, F.MODELS)) + list(ex.map(F.texture, F.TEXTURES))
    man = {aid: rec for aid, rec in res}
    (F.ROOT / "manifest.json").write_text(json.dumps(man, indent=1))
    print(len(man), "assets")
