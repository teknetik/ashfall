#!/usr/bin/env python3
"""Fetch CC0 Poly Haven sources for the West Gate / Warden outpost pass (26 Sep 2026).

Models: 2k glTF + textures. Textures: 2k JPG (diffuse, GL normal, ARM/rough, displacement).
Every asset records its Poly Haven info (authors, licence CC0, dimensions, polycount) in
polyhaven/manifest.json. Re-running skips files whose md5 already matches.
"""
import hashlib, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
MODELS = """concrete_road_barrier concrete_road_barrier_02 old_military_crate wooden_military_crate ammo_box
metal_jerrycan_green barrel_03 Barrel_01 portable_searchlight security_light industrial_wall_lamp portable_generator
exterior_aircon_unit power_box_01 utility_box_02 vintage_radio_transceiver modular_electricity_poles modular_electric_cables
plastic_monobloc_chair_01 metal_trash_can old_tyre namaqualand_boulder_02 namaqualand_boulder_03 namaqualand_boulder_04
namaqualand_rocks_01 namaqualand_stones_01 sand_rocks_small_01 searsia_burchellii wild_rooibos_bush didelta_spinosa
dry_branches_medium_01 tool_cart worn_metal_rack binoculars clipboard modular_chainlink_fence propane_tank
security_camera_01 hand_truck""".split()
TEXTURES = """dry_ground_rocks gravelly_sand sandy_gravel_02 rocky_trail dense_sand muddy_tracks dry_ground_01
container_side green_metal_rust rusty_painted_metal metal_plate_02 painted_metal_shutter worn_corrugated_iron
hessian_230 concrete_floor_damaged_01 rusty_metal_02 plywood anti_skid_tiles""".split()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AthenHill-asset-fetch/1.0 (local game production)"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and hashlib.md5(dest.read_bytes()).hexdigest() == md5:
        return
    dest.write_bytes(get(url))


def model(aid):
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    info = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
    g = files["gltf"]["2k"]["gltf"]
    d = ROOT / "models" / aid
    fetch(g["url"], d / Path(g["url"]).name, g.get("md5"))
    for rel, f in g["include"].items():
        fetch(f["url"], d / rel, f.get("md5"))
    return aid, {"kind": "model", "name": info["name"], "authors": info["authors"], "license": "CC0",
                 "source": f"https://polyhaven.com/a/{aid}", "dimensions_mm": info.get("dimensions"),
                 "polycount": info.get("polycount"), "resolution": "2k", "gltf": Path(g["url"]).name}


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
    with ThreadPoolExecutor(8) as ex:
        jobs = [ex.submit(model, a) for a in MODELS] + [ex.submit(texture, a) for a in TEXTURES]
        for j in jobs:
            try:
                aid, rec = j.result(); manifest[aid] = rec; print("ok", aid, flush=True)
            except Exception as e:
                print("FAILED", e, file=sys.stderr, flush=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
