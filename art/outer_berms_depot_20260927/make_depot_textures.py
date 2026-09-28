#!/usr/bin/env python3
"""Outer Berms depot texture kit (27 Sep 2026): URP Lit sets (<Name>_BaseMap / _Normal / _Mask: R metal,
G AO, A smoothness) from CC0 Poly Haven scans, plus stencil signs and spray-paint decals.

Reuses the West Gate texture helpers (retint, paint_set, spray, grime, sign) by executing the function part of
art/west_gate_20260926/make_textures.py with its output folder redirected; West Gate files are not touched.
Run: uv run --offline --with pillow --with numpy python make_depot_textures.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
WG = HERE.parent / "west_gate_20260926"
src = (WG / "make_textures.py").read_text()
ns = {"__file__": str(WG / "make_textures.py"), "__name__": "wg_textures"}
exec(src[:src.index("def emblem_wall_spire(")], ns)
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/OuterBermsDepot/Textures"
OUT.mkdir(parents=True, exist_ok=True)
ns["OUT"] = OUT
REC = ns["REC"]; REC.clear()
DEPOT_PH = HERE / "polyhaven/textures"


def use(name):
    """Point the helpers at whichever pool holds this scan (depot first, then West Gate)."""
    ns["PH"] = DEPOT_PH if (DEPOT_PH / name).exists() else WG / "polyhaven/textures"


def paint(name, srcname, target, keep=.3, **kw):
    use(srcname); return ns["paint_set"](name, srcname, target, keep, **kw)


# structural steel: old blue-grey primer, heavy rust (used as scanned, slightly cooled)
paint("DP_FramePaint", "rusty_metal_04", None, darken=.92)
# roof sheets: galvanised steel with rust bloom, darkened so the sun does not blow them out
paint("DP_RoofSheet", "rusty_metal_02", None, darken=.7)
# wall cladding: faded industrial teal paint with rust runoff streaks
paint("DP_WallSheet", "rusty_painted_metal", np.array([.27, .35, .32]), .06, rust_from="rough")
# cast concrete (walls, plinth, footings): formwork panels, warmed toward the sandstone dust
paint("DP_Concrete", "concrete_wall_004", np.array([.60, .56, .49]), .5, metal=0)
# yard apron slabs: stained, oil-darkened floor concrete
paint("DP_ApronConcrete", "concrete_floor_damaged_01", np.array([.58, .53, .45]), .55, metal=0)
# conveyor belt rubber, sun-greyed
paint("DP_Belt", "rubberized_track", np.array([.10, .10, .095]), .1, metal=0, rough_add=.08)

# ---- signs (painted into the plate's albedo, eroded by its own wear)
ns["PH"] = WG / "polyhaven/textures"
STENCIL, STENCIL2 = ns["STENCIL"], ns["STENCIL2"]
BONE, HAZ = ns["BONE"], ns["HAZ"]
ns["sign"]("DP_SignHall", (2048, 512), [("PROCESSING HALL 3", STENCIL, .44, .38), ("DRONE SERVICE  ·  AUTHORISED UNITS ONLY", STENCIL2, .13, .80)],
           plate="rusty_painted_metal", plate_color=np.array([.30, .36, .34]), ink=BONE * .92, seed=61)
ns["sign"]("DP_SignVoltage", (1024, 768), [("DANGER", STENCIL, .26, .26), ("HIGH VOLTAGE", STENCIL, .2, .55), ("CHARGE CRADLES LIVE", STENCIL2, .1, .82)],
           plate="metal_plate_02", plate_color=HAZ * .95, ink=np.array([.07, .07, .065]), seed=63)


# ---- spray-painted Warden warning (decal, alpha = paint coverage)
def spray_decal(name, size, lines, color, seed):
    W, H = size
    m = ns["text_mask"](size, lines, pad=.05)
    # hand-sprayed: wobble, soft overspray, drips below the strokes
    im = Image.fromarray((m * 255).astype(np.uint8))
    im = im.transform(size, Image.AFFINE, (1, .04, -W * .01, -.02, 1, H * .02), resample=Image.BILINEAR)
    core = np.asarray(im.filter(ImageFilter.GaussianBlur(W / 900)), np.float32) / 255
    over = np.asarray(im.filter(ImageFilter.GaussianBlur(W / 180)), np.float32) / 255
    rng = np.random.default_rng(seed)
    drips = np.zeros((H, W), np.float32)
    ys, xs = np.nonzero(core > .6)
    for i in rng.choice(len(xs), size=min(60, len(xs)), replace=False):
        x, y = xs[i], ys[i]; L = int(rng.uniform(.03, .16) * H)
        drips[y:min(H, y + L), max(0, x - 1):x + 2] = np.linspace(.9, 0, min(H, y + L) - y)[:, None]
    n = ns["noise"]((H, W), 30, 4, seed)
    a = np.clip(core * (.75 + .25 * n) + over * .18 + drips * .8, 0, 1)
    rgba = np.dstack([np.broadcast_to(color, (H, W, 3)) * (.85 + .15 * n[..., None]), a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")
    REC[name] = {"text": [l[0] for l in lines], "kind": "spray decal"}


spray_decal("DP_DecalSprayKeepOut", (2048, 1024), [("FERAL CLUSTER", STENCIL2, .26, .3), ("KEEP OUT", STENCIL2, .34, .7)], np.array([.62, .08, .05]), 71)
spray_decal("DP_DecalSprayCount", (1024, 512), [("7 DOWN  ·  W.", STENCIL2, .36, .5)], np.array([.85, .82, .72]), 73)


# ---- oil pool / scorch decals (alpha)
def blot(name, size, seed, color, soft=.25, rings=False):
    W, H = size; n = ns["noise"]((H, W), 5, 5, seed); n2 = ns["noise"]((H, W), 20, 3, seed + 1)
    yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    base = np.clip((1 - r) * 1.4 + (n - .5) * 1.2, 0, 1)
    a = np.clip((base - .25) / soft, 0, 1) * (.75 + .25 * n2)
    if rings:
        a = np.maximum(a * .6, np.clip(1 - np.abs(base - .35) * 12, 0, 1) * .5)
    rgba = np.dstack([np.broadcast_to(color, (H, W, 3)) * (.8 + .4 * n2[..., None]), a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")
    REC[name] = {"kind": "blot decal"}


blot("DP_DecalOilPool", (1024, 1024), 81, np.array([.035, .03, .025]), .3, rings=True)
blot("DP_DecalScorch", (1024, 1024), 83, np.array([.03, .028, .026]), .5)

(OUT / "textures.json").write_text(json.dumps(REC, indent=1, default=str))
print("written", sorted(REC))
