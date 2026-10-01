#!/usr/bin/env python3
"""Unity maps for this pass's CC0 Poly Haven props (after prepare_ph_props.py, 1 Oct 2026).
Base colour and OpenGL normal maps are copied (resized to 1k for hand-sized props); the ARM map becomes a URP Lit mask
(R metallic = ARM B, G occlusion = ARM R, A smoothness = 1 - ARM G). Glass parts become a separate transparent
material; the caged lamp keeps its emission map (night only, through the Ward light clock). Records are merged into
Art/TrainingRange/Textures/materials.json under the Poly Haven material names.
Run: $O/heavy.sh uv run --with pillow --with numpy python prepare_prop_textures.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven/models"
UNITY = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange"
OUT = UNITY / "Props/Textures"; OUT.mkdir(parents=True, exist_ok=True)
ASSET = "Assets/AthenHill/Art/TrainingRange/Props/Textures/"
props = json.loads((UNITY / "Props/tr-props.json").read_text())
mats_path = UNITY / "Textures/materials.json"
mats = json.loads(mats_path.read_text())


def img(path, size):
    im = Image.open(path)
    if im.size[0] > size:
        im = im.resize((size, size), Image.LANCZOS)
    return im


done = set()
for pid, e in props.items():
    size = 2048 if max(e["size"]) > 1.15 else 1024
    for mname, spec in e["materials"].items():
        model = spec["model"]; key = mname.split(".")[0]
        if key in done:
            continue
        done.add(key)
        if key.endswith("_glass"):
            mats[key] = {"color": [.55, .6, .58], "alpha": .3, "transparent": True, "smoothness": .92}
            continue
        src = PH / model
        base = f"{model}_BaseMap.jpg"; nor = f"{model}_Normal.jpg"; mask = f"{model}_Mask.png"
        img(src / spec["base"], size).convert("RGB").save(OUT / base, quality=92)
        img(src / spec["normal"], size).convert("RGB").save(OUT / nor, quality=95)
        a = np.asarray(img(src / spec["arm"], size).convert("RGB"), np.float32) / 255
        m = np.dstack([a[..., 2], a[..., 0], np.zeros_like(a[..., 0]), 1 - a[..., 1]])
        Image.fromarray((m * 255 + .5).astype(np.uint8), "RGBA").save(OUT / mask)
        rec = {"base": ASSET + base, "normal": ASSET + nor, "mask": ASSET + mask, "tile": 0, "smoothness": .9, "prop": True,
               "twoSided": bool(spec.get("doubleSided"))}
        em = src / "textures" / f"{model}_emissive_2k.jpg"
        if em.exists():
            img(em, size).convert("RGB").save(OUT / f"{model}_Emission.jpg", quality=92)
            rec["emissionMap"] = ASSET + f"{model}_Emission.jpg"; rec["emission"] = [1.0, .85, .62]; rec["emissionIntensity"] = 2.5
        mats[key] = rec
mats_path.write_text(json.dumps(mats, indent=1))
print(len(done), "prop materials")
