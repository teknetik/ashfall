#!/usr/bin/env python3
"""Fetch CC0 Poly Haven sources for the Ward street dressing pass (30 Sep 2026).
Everyday street objects where a scan beats both Meshy and hand modelling (drums, jerrycans, crates, stools, broom, bins,
tyres, gas bottles, baskets); only unbranded assets (no product names or labels). Hessian and painted-steel textures for
the Blender-authored sacks, tarp and scrap cage. Models (glTF + textures) go to polyhaven/models/<id>/, textures to
polyhaven/textures/<id>/, and polyhaven/manifest.json records names, authors, licence and source URLs."""
import hashlib, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
MODELS = {aid: "2k" for aid in [
    "barrel_03", "Barrel_01", "Barrel_02", "barrel_stove", "metal_jerrycan", "metal_jerrycan_green", "metal_jug",
    "old_military_crate", "wooden_crate_01", "wooden_crate_02", "wooden_military_crate", "plastic_crate_02", "plastic_crate_03",
    "industrial_pastic_container", "cardboard_box_01", "wooden_bucket_01", "wooden_bucket_02", "watering_can_metal_01",
    "planter_box_01", "planter_box_02", "planter_pot_clay", "folding_wooden_stool", "wooden_stool_01", "wooden_stool_02",
    "painted_wooden_stool", "painted_wooden_bench", "metal_stool_02", "wooden_broom", "dustpan", "old_tyre",
    "rusted_wheel_rim_01", "rusted_wheel_rim_02", "small_lpg_tank", "metal_trash_can", "hand_truck", "worn_metal_rack",
    "metal_toolbox", "tool_cart", "oil_tin", "wicker_basket_01", "wicker_basket_02", "pot_enamel_01", "wooden_picnic_table"]}
TEXTURES = {"rough_linen": "2k", "rusty_painted_metal": "2k", "rusty_metal_grid": "2k", "green_metal_rust": "2k"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AthenHill-asset-fetch/1.0 (local game production)"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def fetch(url, dest, md5=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and md5 and hashlib.md5(dest.read_bytes()).hexdigest() == md5:
        return
    dest.write_bytes(get(url))


def info(aid):
    i = json.loads(get(f"https://api.polyhaven.com/info/{aid}"))
    return {"name": i["name"], "authors": i["authors"], "license": "CC0", "source": f"https://polyhaven.com/a/{aid}",
            "dimensions_mm": i.get("dimensions"), "polycount": i.get("polycount")}


def model(aid):
    res = MODELS[aid]
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    g = files["gltf"][res]["gltf"]
    base = ROOT / "models" / aid
    fetch(g["url"], base / Path(g["url"]).name, g.get("md5"))
    for rel, f in g.get("include", {}).items():
        fetch(f["url"], base / rel, f.get("md5"))
    extra = {}
    for key in ("Alpha", "dry_diff", "translucency"):   # maps the glTF does not reference
        if key in files and res in files[key]:
            f = files[key][res].get("png") or files[key][res].get("jpg")
            fetch(f["url"], base / "textures" / Path(f["url"]).name, f.get("md5"))
            extra[key] = Path(f["url"]).name
    return aid, dict(info(aid), kind="model", resolution=res, gltf=Path(g["url"]).name, extra_maps=extra)


def texture(aid):
    res = TEXTURES[aid]
    files = json.loads(get(f"https://api.polyhaven.com/files/{aid}"))
    got = {}
    for key in ["Diffuse", "nor_gl", "arm", "Displacement"]:
        if key in files and res in files[key]:
            f = files[key][res].get("jpg") or files[key][res].get("png")
            fetch(f["url"], ROOT / "textures" / aid / Path(f["url"]).name, f.get("md5"))
            got[key] = Path(f["url"]).name
    return aid, dict(info(aid), kind="texture", resolution=res, files=got)


if __name__ == "__main__":
    with ThreadPoolExecutor(6) as ex:
        man = dict(ex.map(model, MODELS))
        man.update(dict(ex.map(texture, TEXTURES)))
    ROOT.mkdir(exist_ok=True)
    (ROOT / "manifest.json").write_text(json.dumps(man, indent=1))
    for k, v in man.items():
        print(k, v["kind"], v.get("polycount"), v["dimensions_mm"])
