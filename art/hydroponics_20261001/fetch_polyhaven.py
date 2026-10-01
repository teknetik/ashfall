#!/usr/bin/env python3
"""Fetch CC0 Poly Haven sources for the Ward hydroponics pass (1 Oct 2026).

Leaf sources (photographed leaves with alpha, cut into the crop atlas by make_textures.py): nettle (tomato leaflets),
dandelion (rocket/endive leaves), weed plant 02 (broad leaves with a red midrib: chard, cos lettuce), sorrel (runner
bean leaflets, flowers). Yard props where a scan beats hand modelling: cell seed tray, wall hose reel, trowel, spade,
rubber boots, a work hat. Textures: weathered planks (benches, compost bays, pallets), farm soil and wood-chip mulch
(compost, potting soil), worn concrete (greenhouse floor). Only unbranded assets. Same pattern as
art/street_dressing_20260930/fetch_polyhaven.py; polyhaven/manifest.json records names, authors, licence, source URLs.
"""
import hashlib, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
MODELS = {aid: "2k" for aid in [
    "nettle_plant", "dandelion_01", "weed_plant_02", "shrub_sorrel_01",
    "seeding_tray_01", "garden_hose_wall_mounted_01", "trowel_01", "rusted_spade_01", "rubber_boots", "fishermans_hat",
    # restart 1 Oct: plain nutrient-concentrate jugs, a steel trolley for the dosing kit, a step ladder, onions for a crate
    "plastic_bottle_gallon", "industrial_storage_cart", "wooden_ladder", "yellow_onion"]}
TEXTURES = {"weathered_planks": "2k", "farm_soil": "1k", "wood_chip_path": "1k", "gravel_concrete_03": "2k"}


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
    for key in ("Alpha", "translucency"):   # maps the glTF does not reference separately
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
    with ThreadPoolExecutor(4) as ex:
        man = dict(ex.map(model, MODELS))
        man.update(dict(ex.map(texture, TEXTURES)))
    ROOT.mkdir(exist_ok=True)
    (ROOT / "manifest.json").write_text(json.dumps(man, indent=1))
    for k, v in man.items():
        print(k, v["kind"], v.get("polycount"), v["dimensions_mm"])
