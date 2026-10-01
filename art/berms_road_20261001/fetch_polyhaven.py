#!/usr/bin/env python3
"""Fetch CC0 Poly Haven ground scans for the Berms road ground V2 pass (1 Oct 2026).

2k JPG maps (diffuse, GL normal, ARM, displacement) into polyhaven/textures/<id>/ (git-ignored heavy media), with
each asset's Poly Haven record (authors, CC0, dimensions) in polyhaven/manifest.json. Same pattern as
art/west_gate_20260926/fetch_polyhaven.py. Re-running skips files whose md5 matches.
"""
import hashlib, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
TEXTURES = sys.argv[1:] or "rocky_trail_02 rock_ground_02 gravel_ground_01 pebble_ground_01 floor_pebbles_01".split()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AthenHill-asset-fetch/1.0 (local game production)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and hashlib.md5(dest.read_bytes()).hexdigest() == md5:
        return
    dest.write_bytes(get(url))


def texture(aid):
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    info = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
    d = ROOT / "textures" / aid
    got = {}
    for key in ["Diffuse", "nor_gl", "arm", "Rough", "AO", "Displacement"]:
        if key in files and "2k" in files[key]:
            f = files[key]["2k"].get("jpg") or files[key]["2k"].get("png")
            fetch(f["url"], d / Path(f["url"]).name, f.get("md5"))
            got[key] = Path(f["url"]).name
    return aid, {"kind": "texture", "name": info["name"], "authors": info["authors"], "license": "CC0",
                 "source": f"https://polyhaven.com/a/{aid}", "dimensions_mm": info.get("dimensions"),
                 "resolution": "2k", "maps": got}


if __name__ == "__main__":
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    with ThreadPoolExecutor(4) as ex:
        for j in [ex.submit(texture, a) for a in TEXTURES]:
            try:
                aid, rec = j.result(); manifest[aid] = rec; print("ok", aid, flush=True)
            except Exception as e:
                print("FAILED", e, file=sys.stderr, flush=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
