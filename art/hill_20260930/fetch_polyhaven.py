#!/usr/bin/env python3
"""Fetch CC0 Poly Haven sources for the hill and hero-tree pass (30 Sep 2026).
Models (glTF + textures) go to polyhaven/models/<id>/, textures to polyhaven/textures/<id>/, and
polyhaven/manifest.json records names, authors, licence and source URLs."""
import hashlib, json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "polyhaven"
MODELS = {  # id: resolution
    "grass_medium_01": "2k", "grass_medium_02": "2k", "grass_bermuda_01": "2k",
    "cheiridopsis_succulent": "2k", "crystalline_iceplant": "2k", "othonna_cerarioides": "2k",
    "shrub_sorrel_01": "2k", "wild_rooibos_bush": "2k", "weed_plant_02": "2k", "celandine_01": "2k",
    "namaqualand_stones_01": "2k", "namaqualand_boulder_02": "2k", "namaqualand_boulder_03": "2k",
    "namaqualand_boulder_05": "2k", "sand_rocks_small_01": "2k",
    "root_cluster_01": "2k", "root_cluster_02": "2k", "single_root": "2k",
    "bark_debris_01": "2k", "dry_branches_medium_01": "2k", "dry_quiver_leaf": "2k", "moss_01": "2k",
}
TEXTURES = {"brown_mud_leaves_01": "2k", "dry_decay_leaves": "2k", "forest_leaves_02": "2k", "roots": "2k",
            "farm_soil": "2k", "dry_ground_01": "2k", "flower_scattered_dirt": "2k", "leaf_scattered_gravel": "2k",
            "sparse_grass": "2k", "leafy_grass": "2k", "grass_ground": "2k"}


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
