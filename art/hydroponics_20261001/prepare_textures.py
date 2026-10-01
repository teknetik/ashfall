#!/usr/bin/env python3
"""Unity maps and material specs for the Ward hydroponics pass (1 Oct 2026).
Run: $O/heavy.sh uv run --with pillow --with numpy --with scipy python prepare_textures.py

* Crop kit (make_textures.py): HY_CropAtlas (RGBA, alpha-clipped leaves), its normal map, HY_PVC, HY_ShadeCloth copied.
* Polycarbonate film for the retrofit skin (HY_PolyFilm): light dust, condensation runs and drops, alpha 0.12 .. 0.42
  so the skin stays clear enough to read the crops.
* Tiling Poly Haven textures (weathered planks, farm soil, wood-chip mulch, worn concrete): base and OpenGL normal copied
  (1k for small-area use), the ARM map packed into a URP Lit mask (R metallic = ARM B, G occlusion = ARM R,
  A smoothness = 1 - ARM G).
* Poly Haven props: the same per glTF material (1k for hand-sized props, 2k for the trolley and ladder).
Writes unity/AthenHill/Assets/AthenHill/Art/Hydroponics/Textures/... and Textures/materials.json (material specs read by
Editor/HydroponicsPass.cs).
"""
import json, shutil, glob
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven"
UNITY = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/Hydroponics"
TEX = UNITY / "Textures"
TEX.mkdir(parents=True, exist_ok=True)
ASSET = "Assets/AthenHill/Art/Hydroponics/Textures/"


def mask_from_arm(src, dst, size):
    a = Image.open(src).convert("RGB")
    if size and a.size[0] > size:
        a = a.resize((size, size), Image.LANCZOS)
    x = np.asarray(a).astype(np.float32) / 255
    occ, rough, metal = x[..., 0], x[..., 1], x[..., 2]
    m = np.stack([metal, occ, np.zeros_like(metal), 1 - rough], -1)
    Image.fromarray((m * 255 + .5).astype(np.uint8), "RGBA").save(dst)


def copy(src, dst, size=None):
    if size:
        im = Image.open(src)
        if im.size[0] > size:
            im = im.resize((size, size), Image.LANCZOS)
            im.save(dst, quality=95) if str(dst).endswith(".jpg") else im.save(dst)
            return
    shutil.copyfile(src, dst)


M = {}

# ------------------------------------------------------------------ crop kit and cloth
for f in ("HY_CropAtlas.png", "HY_CropAtlas_Normal.png", "HY_PVC.png", "HY_ShadeCloth.png"):
    shutil.copyfile(HERE / "textures" / f, TEX / f)
M["HY_Crop"] = dict(shader="groundcover", base=ASSET + "HY_CropAtlas.png", normal=ASSET + "HY_CropAtlas_Normal.png", normalScale=.6,
                    alphaClip=True, cutoff=.45, smoothness=.38, translucency=.28, indirectTranslucency=.12)
M["HY_PVC"] = dict(base=ASSET + "HY_PVC.png", smoothness=.45)
M["HY_ShadeCloth"] = dict(base=ASSET + "HY_ShadeCloth.png", alphaClip=True, cutoff=.4, smoothness=.1, tint=[1.2, 1.2, 1.2])

# polycarbonate film (one tile per 1.5 m bay along u, a third of the arch along v): light dust, a few condensation
# runs and drops; alpha stays low (0.12 .. 0.42) so the crops read through the skin, a little dustier where runs dried
from scipy import ndimage
frng = np.random.default_rng(1001)
P = 1024
dust = ndimage.gaussian_filter(frng.random((P, P)), 26, mode="wrap")
dust = (dust - dust.min()) / (dust.max() - dust.min())
runs = np.zeros((P, P), np.float32)
for _ in range(110):
    cx = frng.uniform(0, P); ln = frng.uniform(.06, .35) * P; y0 = frng.uniform(0, P)
    ys = (np.arange(int(ln)) + y0).astype(int) % P
    xs = (cx + np.cumsum(frng.normal(0, .3, len(ys)))).astype(int) % P
    runs[ys, xs] = frng.uniform(.3, .8)
runs = np.clip(ndimage.gaussian_filter(runs, (2.5, 1.4), mode="wrap") * 5, 0, 1)
drops = (ndimage.gaussian_filter(frng.random((P, P)), 1.4, mode="wrap") > .585).astype(np.float32)
a = np.clip(.12 + .16 * dust ** 1.5 + .12 * runs + .05 * drops, 0, 1)
rgb = np.dstack([.86 + .06 * dust, .87 + .05 * dust, .82 + .04 * dust])
Image.fromarray((np.dstack([rgb, a]) * 255 + .5).astype(np.uint8), "RGBA").resize((512, 512), Image.LANCZOS).save(TEX / "HY_PolyFilm.png")
M["HY_Polycarbonate"] = dict(shader="transparent", base=ASSET + "HY_PolyFilm.png", tint=[.66, .68, .64], smoothness=.85, castShadows=False, specularHighlights=False)

# ------------------------------------------------------------------ tiling textures
TILING = {"HY_Wood": ("weathered_planks", 1024, [1, 1, 1]), "HY_Soil": ("farm_soil", 1024, [.9, .85, .8]),
          "HY_Compost": ("wood_chip_path", 1024, [.8, .72, .62]), "HY_Floor": ("gravel_concrete_03", 1024, [1, 1, 1])}
for name, (tid, size, tint) in TILING.items():
    d = TEX / tid; d.mkdir(exist_ok=True)
    src = PH / "textures" / tid
    diff = next(src.glob("*_diff_*.jpg")); nor = next(src.glob("*_nor_gl_*.jpg")); arm = next(src.glob("*_arm_*.jpg"))
    copy(diff, d / f"{tid}_diff.jpg", size); copy(nor, d / f"{tid}_nor_gl.jpg", size)
    mask_from_arm(arm, d / f"{tid}_mask.png", size)
    M[name] = dict(base=ASSET + f"{tid}/{tid}_diff.jpg", normal=ASSET + f"{tid}/{tid}_nor_gl.jpg", mask=ASSET + f"{tid}/{tid}_mask.png",
                   tint=tint, smoothness=.9)

# ------------------------------------------------------------------ flat authored materials (no maps)
FLAT = {
    "HY_BlackPlastic": dict(color=[.035, .037, .04], smoothness=.5),
    "HY_Galv": dict(color=[.6, .61, .6], smoothness=.55, metallic=.75),
    "HY_Alu": dict(color=[.66, .67, .69], smoothness=.62, metallic=.8),
    "HY_LED": dict(color=[.95, .8, .95], smoothness=.6, emission=[1.0, .42, .88], emissionIntensity=4.0, circuit=True),
    "HY_LEDProp": dict(color=[.95, .93, 1.0], smoothness=.6, emission=[.92, .86, 1.0], emissionIntensity=1.6),
    "HY_Twine": dict(color=[.66, .58, .42], smoothness=.1),
    "HY_Rockwool": dict(color=[.55, .5, .38], smoothness=.05),
    "HY_GrowBag": dict(color=[.82, .82, .79], smoothness=.4),
    "HY_WeedMat": dict(color=[.045, .045, .042], smoothness=.15),
    "HY_IBC": dict(color=[.82, .81, .75], smoothness=.45),
    "HY_Steel": dict(color=[.25, .24, .22], smoothness=.45, metallic=.7),
    "HY_CrateBlue": dict(color=[.08, .22, .42], smoothness=.4),
    "HY_CrateGreen": dict(color=[.16, .34, .14], smoothness=.4),
    "HY_Rubber": dict(color=[.03, .03, .028], smoothness=.2),
    "HY_Hose": dict(color=[.08, .26, .13], smoothness=.55),
    "HY_Water": dict(color=[.2, .24, .17], smoothness=.6),
}
M.update(FLAT)

# ------------------------------------------------------------------ Poly Haven props
PROPS = {"garden_hose_wall_mounted_01": 1024, "trowel_01": 1024, "rusted_spade_01": 1024, "rubber_boots": 1024, "fishermans_hat": 1024,
         "plastic_bottle_gallon": 1024, "industrial_storage_cart": 2048, "wooden_ladder": 2048, "yellow_onion": 512}
for model, size in PROPS.items():
    g = json.loads(next((PH / "models" / model).glob("*.gltf")).read_text())
    imgs = [i["uri"] for i in g["images"]]
    T = lambda i: imgs[g["textures"][i]["source"]] if i is not None else None
    d = TEX / model; d.mkdir(exist_ok=True)
    for mat in g["materials"]:
        pbr = mat.get("pbrMetallicRoughness", {})
        b, n, mr = T(pbr.get("baseColorTexture", {}).get("index")), T(mat.get("normalTexture", {}).get("index")), T(pbr.get("metallicRoughnessTexture", {}).get("index"))
        name = mat["name"]
        stem = Path(b).stem.replace("_diff_2k", "")
        copy(PH / "models" / model / b, d / f"{stem}_diff.jpg", size)
        copy(PH / "models" / model / n, d / f"{stem}_nor_gl.jpg", size)
        mask_from_arm(PH / "models" / model / mr, d / f"{stem}_mask.png", size)
        M[name] = dict(base=ASSET + f"{model}/{stem}_diff.jpg", normal=ASSET + f"{model}/{stem}_nor_gl.jpg", mask=ASSET + f"{model}/{stem}_mask.png",
                       smoothness=.9, doubleSided=bool(mat.get("doubleSided")))

(TEX / "materials.json").write_text(json.dumps(M, indent=1))
print(len(M), "materials;", sum(1 for _ in TEX.rglob("*.*")), "files")
