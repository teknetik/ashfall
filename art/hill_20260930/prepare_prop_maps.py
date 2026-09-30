"""Unity maps for the prepared Meshy props (30 Sep 2026). Run with: uv run --with pillow --with numpy python prepare_prop_maps.py
* <prop>_Mask.png   URP Lit metallic/smoothness map: R metallic (glTF B), G occlusion 1, B 0, A smoothness (1 - glTF G roughness)
* <prop>_Emission.png emissive colour where the base colour carries lit screens / LEDs / lens (derived from the albedo;
  the albedo itself is unchanged). Source maps stay as supplied (source_*.jpg)."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
P = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/HillProps"
report = {}
for prop in ("Terminal", "Floodlight"):
    d = P / prop
    mr = np.asarray(Image.open(d / "source_MetalRough.jpg").convert("RGB")).astype(np.float32) / 255
    rough, metal = mr[..., 1], mr[..., 2]
    mask = np.stack([metal, np.ones_like(metal), np.zeros_like(metal), 1 - rough], -1)
    Image.fromarray((mask * 255 + 0.5).astype(np.uint8), "RGBA").save(d / f"{prop}_Mask.png")
    alb = np.asarray(Image.open(d / "source_BaseColor.jpg").convert("RGB")).astype(np.float32) / 255
    r, g, b = alb[..., 0], alb[..., 1], alb[..., 2]
    if prop == "Terminal":
        # lit cyan graphics: bright and strongly blue-green over red (the verdigris patina is dull teal and stays off)
        cy = np.clip(((g + b) / 2 - r - 0.22) / 0.25, 0, 1) * np.clip((np.maximum(g, b) - 0.55) / 0.2, 0, 1)
        em = alb * cy[..., None]
    else:
        # the lens face (near-white) and the thin cyan accent bands
        white = np.clip((np.minimum(np.minimum(r, g), b) - 0.78) / 0.12, 0, 1)
        cy = np.clip(((g + b) / 2 - r - 0.12) / 0.2, 0, 1) * np.clip((b - 0.5) / 0.2, 0, 1)
        em = alb * np.maximum(white, cy)[..., None]
    img = Image.fromarray((np.clip(em, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB").filter(ImageFilter.GaussianBlur(0.6))
    img.save(d / f"{prop}_Emission.png")
    report[prop] = {"emissive_fraction": float((em.max(-1) > 0.05).mean()), "metal_mean": float(metal.mean()), "rough_mean": float(rough.mean())}
(P / "maps.json").write_text(json.dumps(report, indent=1))
print(report)
