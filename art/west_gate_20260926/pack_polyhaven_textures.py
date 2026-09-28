#!/usr/bin/env python3
"""Write URP Lit texture sets for the converted Poly Haven props.

For every material used by polyhaven-conversion.json:
  PH_<mat>_BaseMap.<ext>   base colour (alpha kept for cut-out foliage)
  PH_<mat>_Normal.jpg      OpenGL normal (Unity convention)
  PH_<mat>_Mask.png        URP Lit metallic/smoothness map: R metallic, G occlusion, A smoothness
materials.json records alpha mode, double-sidedness and factors for the Unity material builder.
"""
import json, shutil
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / "polyhaven/models"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Props/Textures"
conv = json.loads((HERE / "polyhaven-conversion.json").read_text())
wanted = {m for r in conv.values() for m in r["materials"]}
records = {}
for asset in sorted({r["asset"] for r in conv.values()}):
    gpath = next((SRC / asset).glob("*.gltf")); g = json.loads(gpath.read_text())
    def img(tex_index):
        return SRC / asset / g["images"][g["textures"][tex_index]["source"]]["uri"]
    for m in g.get("materials", []):
        name = "PH_" + m["name"]
        if name not in wanted or name in records:
            continue
        pbr = m.get("pbrMetallicRoughness", {})
        rec = {"alphaMode": m.get("alphaMode", "OPAQUE"), "alphaCutoff": m.get("alphaCutoff", .5),
               "doubleSided": m.get("doubleSided", False), "baseColorFactor": pbr.get("baseColorFactor", [1, 1, 1, 1]),
               "metallicFactor": pbr.get("metallicFactor", 1), "roughnessFactor": pbr.get("roughnessFactor", 1),
               "emissiveFactor": m.get("emissiveFactor", [0, 0, 0]), "transmission": "KHR_materials_transmission" in m.get("extensions", {})}
        if "baseColorTexture" in pbr:
            src = img(pbr["baseColorTexture"]["index"]); dst = OUT / f"{name}_BaseMap{src.suffix}"
            shutil.copyfile(src, dst); rec["baseMap"] = dst.name
        if "normalTexture" in m:
            src = img(m["normalTexture"]["index"]); dst = OUT / f"{name}_Normal{src.suffix}"
            shutil.copyfile(src, dst); rec["normalMap"] = dst.name
        mr = pbr.get("metallicRoughnessTexture"); oc = m.get("occlusionTexture")
        if mr or oc:
            ref = Image.open(img((mr or oc)["index"])).convert("RGB")
            a = np.asarray(ref, dtype=np.float32) / 255
            rough = a[..., 1] * rec["roughnessFactor"] if mr else np.full(a.shape[:2], rec["roughnessFactor"], np.float32)
            metal = a[..., 2] * rec["metallicFactor"] if mr else np.full(a.shape[:2], rec["metallicFactor"], np.float32)
            if oc:
                o = np.asarray(Image.open(img(oc["index"])).convert("RGB").resize(ref.size), dtype=np.float32)[..., 0] / 255
            else:
                o = np.ones(a.shape[:2], np.float32)
            mask = np.dstack([metal, o, np.zeros_like(o), 1 - rough])
            Image.fromarray((np.clip(mask, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}_Mask.png")
            rec["maskMap"] = f"{name}_Mask.png"; rec["metallicMean"] = float(metal.mean()); rec["smoothnessMean"] = float(1 - rough.mean())
        records[name] = rec
        print(name, rec.get("alphaMode"), rec.get("baseMap"), flush=True)
missing = wanted - set(records)
(OUT / "materials.json").write_text(json.dumps(records, indent=1, sort_keys=True))
print("materials", len(records), "missing", sorted(missing))

# Namaqualand granite scans are pink; recolour toward Tir sandstone (keep luminance detail, move hue).
from PIL import Image as _I
for mat in ("PH_namaqualand_rocks_02", "PH_namaqualand_stones_01"):
    p = OUT / f"{mat}_BaseMap.jpg"
    if not p.exists(): continue
    a = np.asarray(_I.open(p).convert("RGB"), np.float32) / 255
    l = (a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11)[..., None]
    target = np.array([.62, .50, .37]) / .52
    out = np.clip(l * target * .75 + a * .25 * np.array([.8, .95, .9]), 0, 1)
    _I.fromarray((out * 255 + .5).astype(np.uint8)).save(p, quality=93)
    print("recoloured", mat)
