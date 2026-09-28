#!/usr/bin/env python3
"""URP Lit texture sets for the Outer Berms robots (27 Sep 2026 robot pass).

The worker droid in Unity only had its 2k base colour, wired to emission (glTF emissiveFactor 1): flat, self-lit.
Its Meshy refine model carries normal + metallic/roughness maps on the same UV atlas as the rigged mesh (identical
UV bounds and triangle count), so they are restored here. The scrap drone keeps its own maps but gets a weathered,
less toy-like base colour. Emission maps are restricted to the optics: triangles within a small radius of each lens
centre (found from the bright lens texels on the mesh) are rasterised into UV space, so only the lenses glow and
FeralDroid can drive their intensity as the attack telegraph.

Run: uv run --offline --with numpy --with pillow python art/outer_berms_depot_20260927/make_robot_textures.py
Writes Assets/AthenHill/Art/OuterBerms/Textures/{WorkerDroid,ScrapDrone}_{BaseMap,Normal,Mask,Emission}.png
"""
import io, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "tools"))
from glbread import GLB  # noqa: E402

OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/OuterBerms/Textures"
OUT.mkdir(parents=True, exist_ok=True)
MESHY = ROOT / "meshy/outer-berms-20260926"


def img_of(glb, index):
    data, _ = glb.image(index)
    return Image.open(io.BytesIO(data))


def mesh(glb):
    pr = glb.j["meshes"][0]["primitives"][0]
    P = glb.acc(pr["attributes"]["POSITION"]).astype(np.float64)
    UV = glb.acc(pr["attributes"]["TEXCOORD_0"]).astype(np.float64)
    I = glb.acc(pr["indices"]).reshape(-1, 3).astype(np.int64)
    return P, UV, I


def raster_mask(UV, I, tris, size):
    """Rasterise the given triangles (UV space, glTF v down = image row) into a float mask."""
    m = np.zeros((size, size), np.float32)
    for t in tris:
        uv = UV[I[t]] * size
        x0, y0 = np.floor(uv.min(0)).astype(int) - 1
        x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, size - 1), min(y1, size - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        a, b, c = uv
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-12:
            continue
        l1 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= -.02) & (l2 >= -.02) & (l3 >= -.02)
        m[y0:y1 + 1, x0:x1 + 1] = np.maximum(m[y0:y1 + 1, x0:x1 + 1], inside.astype(np.float32))
    # dilate 1 px only: the Meshy atlas packs unrelated islands edge to edge, and a wider dilation lit specks of the
    # neighbouring islands (visible as embers on the drone's pods in the first native captures)
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    return np.asarray(im, np.float32) / 255


def save_rgb(a, path):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(path)


def mask_from_mr(mr, smooth_scale):
    a = np.asarray(mr.convert("RGB"), np.float32) / 255
    metal, rough = a[..., 2], a[..., 1]
    m = np.dstack([metal, np.ones_like(metal), np.zeros_like(metal), (1 - rough) * smooth_scale])
    return Image.fromarray((np.clip(m, 0, 1) * 255 + .5).astype(np.uint8), "RGBA")


def emission(base, UV, I, P, lenses, size, lum_gate=None):
    C = P[I].mean(1)
    tris = []
    for centre, radius, extra in lenses:
        d = np.linalg.norm(C - np.asarray(centre), axis=1)
        sel = d < radius
        if extra is not None:
            sel &= extra(C)
        tris.extend(np.flatnonzero(sel).tolist())
    m = raster_mask(UV, I, tris, size)
    b = np.asarray(base.convert("RGB").resize((size, size)), np.float32) / 255
    lum = b @ np.array([.3, .59, .11], np.float32)
    if lum_gate:   # keep only the bright lens texels (worker optics are painted as glowing yellow-orange discs)
        lo, hi = lum_gate; g = m * np.clip((lum - lo) / (hi - lo), 0, 1)
    else:
        g = m * (.35 + .65 * np.clip(lum / max(float(np.percentile(lum[m > .5], 90)) if (m > .5).any() else 1, 1e-3), 0, 1))
    return Image.fromarray((np.clip(g, 0, 1) * 255 + .5).astype(np.uint8), "L"), len(tris)


record = {}

# ---------------------------------------------------------------- worker droid
refine = GLB(MESHY / "worker-droid/model.glb")
rigged = GLB(ROOT / "unity/AthenHill/Assets/AthenHill/Art/OuterBerms/WorkerDroid.glb")
P, UV, I = mesh(rigged)
base = img_of(rigged, 0).convert("RGB")          # the rigged export's base colour (matches the rigged UVs)
base.save(OUT / "WorkerDroid_BaseMap.png")
img_of(refine, 2).convert("RGB").save(OUT / "WorkerDroid_Normal.png")
mask_from_mr(img_of(refine, 1), .82).save(OUT / "WorkerDroid_Mask.png")   # dust-dulled paint
# lens centres in mesh space (m): head optic and chest core, from the brightest yellow-orange texels on the mesh
em, n = emission(base, UV, I, P, [((0, 1.58, .244), .043, None), ((0, 1.384, .249), .038, None)], 2048, lum_gate=(.42, .7))
em.save(OUT / "WorkerDroid_Emission.png")
record["WorkerDroid"] = {"emissive_triangles": n, "smoothness_scale": .82, "source_maps": "refine model.glb normal + MR"}

# ---------------------------------------------------------------- scrap drone
drone = GLB(MESHY / "scrap-drone/model.glb")
P, UV, I = mesh(drone)
b = np.asarray(img_of(drone, 0).convert("RGB"), np.float32) / 255
# weather the toy-bright orange: pull saturation toward luminance, darken slightly, warm dust in the lights
lum = (b @ np.array([.3, .59, .11], np.float32))[..., None]
sat = b.max(-1, keepdims=True) - b.min(-1, keepdims=True)
w = np.clip((sat - .25) * 2.5, 0, 1)             # only the saturated paint is affected; dark metal stays
dusty = lum * np.array([1.08, .98, .86], np.float32)
b2 = b * (1 - .38 * w) + dusty * (.38 * w)
b2 *= .9
save_rgb(b2, OUT / "ScrapDrone_BaseMap.png")
img_of(drone, 2).convert("RGB").save(OUT / "ScrapDrone_Normal.png")
mask_from_mr(img_of(drone, 1), .8).save(OUT / "ScrapDrone_Mask.png")
em, n = emission(Image.fromarray((b * 255).astype(np.uint8)), UV, I, P,
                 [((0, 0, .30), .072, lambda C: C[:, 2] > .262)], 2048)   # the lens glass dome only (faces glTF +z)
em.save(OUT / "ScrapDrone_Emission.png")
record["ScrapDrone"] = {"emissive_triangles": n, "smoothness_scale": .8, "base": "saturation -38% on painted areas, -10% value"}

(HERE / "robot-textures.json").write_text(json.dumps(record, indent=1))
print(json.dumps(record))
