"""Unity texture sets for the hill planting and soils (30 Sep 2026), from the CC0 Poly Haven sources in polyhaven/.
Run: uv run --with pillow --with numpy python prepare_hill_textures.py
* <name>_BaseMap.png  diffuse (+ the separate alpha map in A for cut-out foliage)
* <name>_Mask.png     URP Lit metallic/smoothness: R metallic (ARM b), G occlusion (ARM r), B 0, A smoothness (1 - ARM g)
* <name>_Normal.jpg   OpenGL normal map, copied unchanged
Plants -> Art/WardHill/Plants/Textures, soils -> Art/WardHill/Textures."""
import json, shutil
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
UNITY = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WardHill"
PLANTS = ["grass_medium_01", "grass_medium_02", "cheiridopsis_succulent", "crystalline_iceplant", "celandine_01", "weed_plant_02",
          "othonna_cerarioides", "namaqualand_stones_01", "namaqualand_boulder_05", "bark_debris_01", "dry_branches_medium_01"]
SOILS = {"WH_BedSoil": "sparse_grass", "WH_RingLitter": "dry_decay_leaves"}


def mask_from_arm(arm):
    a = np.asarray(Image.open(arm).convert("RGB")).astype(np.float32) / 255
    m = np.stack([a[..., 2], a[..., 0], np.zeros_like(a[..., 0]), 1 - a[..., 1]], -1)
    return Image.fromarray((m * 255 + 0.5).astype(np.uint8), "RGBA")


report = {}
out = UNITY / "Plants/Textures"
out.mkdir(parents=True, exist_ok=True)
for m in PLANTS:
    t = HERE / "polyhaven/models" / m / "textures"
    diff = t / f"{m}_diff_2k.jpg"
    base = Image.open(diff).convert("RGB")
    alpha = t / f"{m}_alpha_2k.png"
    if alpha.exists():
        a = Image.open(alpha).convert("L").resize(base.size)
        base = base.copy()
        base.putalpha(a)
    base.save(out / f"{m}_BaseMap.png")
    mask_from_arm(t / f"{m}_arm_2k.jpg").save(out / f"{m}_Mask.png")
    shutil.copyfile(t / f"{m}_nor_gl_2k.jpg", out / f"{m}_Normal.jpg")
    report[m] = {"alpha": alpha.exists(), "diffuse": diff.name}
out = UNITY / "Textures"
out.mkdir(parents=True, exist_ok=True)
for name, src in SOILS.items():
    t = HERE / "polyhaven/textures" / src
    diff = next(t.glob("*_diff*_2k.jpg"))
    shutil.copyfile(diff, out / f"{name}_BaseMap.jpg")
    shutil.copyfile(next(t.glob("*_nor_gl_2k.jpg")), out / f"{name}_Normal.jpg")
    mask_from_arm(next(t.glob("*_arm_2k.jpg"))).save(out / f"{name}_Mask.png")
    report[name] = {"source": src}
(UNITY / "Plants/textures.json").write_text(json.dumps(report, indent=1))
print(report)
