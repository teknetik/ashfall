#!/usr/bin/env python3
"""Fetch CC0 Poly Haven texture sources for the Vanguard Hall rebuild (30 Sep 2026).
Writes polyhaven/<id>/ (Diffuse, GL normal, ARM, Displacement) and polyhaven/manifest.json with authors/licence."""
import hashlib, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
TEXTURES = {"worn_rock_natural_01": "4k", "sandstone_cracks": "4k", "rust_coarse_01": "2k", "rusty_metal_03": "2k",
            "rough_linen": "2k", "large_sandstone_blocks_01": "2k", "metal_plate": "2k", "painted_metal_shutter": "2k", "rusty_metal_sheet": "2k", "dense_sand": "2k"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AthenHill-asset-fetch/1.0 (local game production)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()

def fetch(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and hashlib.md5(dest.read_bytes()).hexdigest() == md5:
        return
    dest.write_bytes(get(url))

def texture(aid):
    res = TEXTURES[aid]
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    info = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
    got = {}
    for key in ["Diffuse", "nor_gl", "arm", "Rough", "AO", "Displacement"]:
        if key in files and res in files[key]:
            f = files[key][res].get("jpg") or files[key][res].get("png")
            fetch(f["url"], ROOT / aid / Path(f["url"]).name, f.get("md5"))
            got[key] = Path(f["url"]).name
    return aid, {"kind": "texture", "name": info["name"], "authors": info["authors"], "license": "CC0",
                 "source": f"https://polyhaven.com/a/{aid}", "dimensions_mm": info.get("dimensions"),
                 "resolution": res, "files": got}

if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        man = dict(ex.map(texture, TEXTURES))
    (ROOT / "manifest.json").write_text(json.dumps(man, indent=1))
    for k, v in man.items():
        print(k, v["dimensions_mm"], v["files"])
