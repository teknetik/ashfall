#!/usr/bin/env python3
"""Warden training range textures (1 Oct 2026): weathered timber, sand fill, stencilled range signs, lane and distance
numbers, and URP decal maps (painted firing line, trodden ground, paint overspray, impact scars, hit-zone ring).

Inputs: CC0 Poly Haven scans (polyhaven/textures here and art/west_gate_20260926/polyhaven/textures) and the OFL stencil
fonts in art/west_gate_20260926/fonts (not redistributed; lettering is rasterised into the maps). The helpers follow
art/west_gate_20260926/make_textures.py (that module is not imported: it writes the West Gate maps at import).
Outputs: unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Textures/<Name>_BaseMap/_Normal/_Mask (URP Lit mask:
R metallic, G occlusion, A smoothness) and TR_Decal*.png (RGBA), plus Textures/materials.json read by
Editor/TrainingRangePass.cs (tile size in metres per repeat, tint, smoothness, flags).
Run: $O/heavy.sh uv run --with pillow --with numpy python make_textures.py
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
WG = HERE.parent / "west_gate_20260926"
PHT = [HERE / "polyhaven/textures", WG / "polyhaven/textures"]
FONTS = WG / "fonts"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/TrainingRange/Textures"
OUT.mkdir(parents=True, exist_ok=True)
STENCIL = str(FONTS / "stardosstencil__StardosStencil-Bold.ttf")
STENCIL2 = str(FONTS / "allertastencil__AllertaStencil-Regular.ttf")
COND = str(FONTS / "barlowcondensed__BarlowCondensed-SemiBold.ttf")
BONE = np.array([.80, .76, .64]); OLIVE = np.array([.25, .27, .19]); RUST = np.array([.45, .19, .12]); RED = np.array([.55, .12, .08])
MATS = {}


def load(name, kind, size=None):
    for root in PHT:
        p = root / name / f"{name}_{kind}_2k.jpg"
        if p.exists():
            im = Image.open(p).convert("RGB")
            if size: im = im.resize(size, Image.LANCZOS)
            return np.asarray(im, dtype=np.float32) / 255
    raise FileNotFoundError(name + " " + kind)


def lum(a): return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def save_rgb(a, name, q=92):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(OUT / name, quality=q)


def save_rgba(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / name)


def mask_from(arm, metal=0.0):
    m = np.full(arm.shape[:2], metal, np.float32)
    return np.dstack([m, arm[..., 0], np.zeros_like(m), 1 - arm[..., 1]])


def noise(shape, scale, octaves=4, seed=0):
    r = np.random.default_rng(seed); h, w = shape; out = np.zeros(shape, np.float32); amp = 1; tot = 0
    for o in range(octaves):
        sy, sx = max(2, int(scale * 2 ** o * h / max(h, w))), max(2, int(scale * 2 ** o * w / max(h, w)))
        g = r.random((sy + 1, sx + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


def retint(diff, target, keep=.35):
    l = lum(diff)[..., None]; mean = l.mean()
    return np.clip(target * (l / mean) * (1 - keep) + diff * keep * (target.mean() / diff.mean()), 0, 1)


def mat(name, **spec):
    base = f"Assets/AthenHill/Art/TrainingRange/Textures/{name}"
    rec = {"base": base + "_BaseMap.jpg", "normal": base + "_Normal.jpg", "mask": base + "_Mask.png"}
    rec.update(spec)
    MATS[name] = rec


# ------------------------------------------------------------------ timber (rough_wood: weathered, checked, nail holes)
wd, wn, wa = load("rough_wood", "diff"), load("rough_wood", "nor_gl"), load("rough_wood", "arm")
# sun-bleached grey-brown (posts, rails, planks)
t = wd * np.array([1.04, 1.0, .94])
save_rgb(t, "TR_Timber_BaseMap.jpg"); save_rgb(wn, "TR_Timber_Normal.jpg", 95)
arm = wa.copy(); arm[..., 1] = np.clip(arm[..., 1] + .06, 0, 1); save_rgba(mask_from(arm), "TR_Timber_Mask.png")
mat("TR_Timber", tile=1.2, smoothness=.85)
# creosote-dark railway sleepers (revetment, crib walls): darker, browner, a little oily in the grain
d = retint(wd, np.array([.27, .21, .15]), .35)          # weathered creosote: sun-greyed brown, not black (reads in shade)
oil = np.clip((noise(d.shape[:2], 6, 4, 11) - .55) * 3, 0, 1)[..., None]
d = d * (1 - oil * .25)
save_rgb(d, "TR_TimberDark_BaseMap.jpg")
arm2 = wa.copy(); arm2[..., 1] = np.clip(arm2[..., 1] - .08 * oil[..., 0], 0, 1); save_rgba(mask_from(arm2), "TR_TimberDark_Mask.png")
save_rgb(wn, "TR_TimberDark_Normal.jpg", 95)
mat("TR_TimberDark", tile=1.2, smoothness=.9)
# newer replacement timber (fresh cuts, still yellow-brown)
f = retint(wd, np.array([.56, .42, .27]), .45)
save_rgb(f, "TR_TimberFresh_BaseMap.jpg"); save_rgb(wn, "TR_TimberFresh_Normal.jpg", 95); save_rgba(mask_from(wa), "TR_TimberFresh_Mask.png")
mat("TR_TimberFresh", tile=1.2, smoothness=.8)

# ------------------------------------------------------------------ sand fill (bag spill, gaps behind shot sleepers)
sd, sn, sa = load("dense_sand", "diff"), load("dense_sand", "nor_gl"), load("dense_sand", "arm")
save_rgb(sd * np.array([1.02, .98, .92]), "TR_SandFill_BaseMap.jpg"); save_rgb(sn, "TR_SandFill_Normal.jpg", 95); save_rgba(mask_from(sa), "TR_SandFill_Mask.png")
mat("TR_SandFill", tile=1.6, smoothness=.6)


# ------------------------------------------------------------------ lettering helpers (stencil spray, wear, grime)
def text_mask(size, lines, pad=.06):
    W, H = size; im = Image.new("L", size, 0); d = ImageDraw.Draw(im)
    for text, font, rh, yc, *rest in lines:
        align = rest[0] if rest else "c"
        fs = int(H * rh); fnt = ImageFont.truetype(font, fs)
        while True:
            bb = d.textbbox((0, 0), text, font=fnt)
            if bb[2] - bb[0] <= W * (1 - 2 * pad) or fs < 8: break
            fs = int(fs * .95); fnt = ImageFont.truetype(font, fs)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = (W - tw) / 2 - bb[0] if align == "c" else W * pad - bb[0]
        d.text((x, H * yc - th / 2 - bb[1]), text, font=fnt, fill=255)
    return np.asarray(im, np.float32) / 255


def spray(base, mask, color, wear, strength=.95, seed=1):
    h, w = mask.shape
    soft = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1, w / 1400))), np.float32) / 255
    over = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w / 220)), np.float32) / 255
    n = noise((h, w), 24, 4, seed)
    cover = np.clip(soft * strength * (1 - np.clip((wear - .45) * 3, 0, 1)) * (0.82 + .18 * n), 0, 1) + over * .10 * n
    cover = np.clip(cover, 0, 1)[..., None]
    shade = (lum(base) / max(lum(base).mean(), 1e-3))[..., None] ** .6
    return base * (1 - cover) + color * shade * cover


def grime(base, strength=.25, seed=3):
    h, w = base.shape[:2]
    n = noise((h, w), 6, 5, seed)
    g = base * (1 - strength * n[..., None] * .6)
    dust = np.clip(np.linspace(-.2, .6, h)[:, None] * noise((h, w), 10, 4, seed + 7), 0, 1)[..., None]
    return g * (1 - dust * .35) + np.array([.62, .52, .40]) * dust * .35


def board(size, src="plywood", color=None, keep=.4):
    """Painted or bare board face at the sign's aspect (wood grain kept)."""
    W, H = size
    diff, nor, arm = load(src, "diff", (W, H)), load(src, "nor_gl", (W, H)), load(src, "arm", (W, H))
    base = retint(diff, color, keep) if color is not None else diff
    wear = np.clip(arm[..., 1] * 1.2 - .25 + (noise((H, W), 12, 4, 5) - .5) * .5, 0, 1)
    return base, nor, arm, wear


def finish_sign(name, base, nor, arm, smooth=.55, **spec):
    save_rgb(base, f"{name}_BaseMap.jpg"); save_rgb(nor, f"{name}_Normal.jpg", 95); save_rgba(mask_from(arm), f"{name}_Mask.png")
    mat(name, tile=0, smoothness=smooth, **spec)


# RANGE ORDERS board (1.4 x 0.95 m), original text
W_, H_ = 1536, 1024
b, n_, a_, wear = board((W_, H_), "plywood", BONE * .92, .3)
title = text_mask((W_, H_), [("RANGE ORDERS", STENCIL, .13, .095)])
rule = np.zeros((H_, W_), np.float32); rule[int(H_ * .175):int(H_ * .185), int(W_ * .05):int(W_ * .95)] = 1
body = [("1  The range is live while the red flag flies and the red lamp burns.", COND, .052, .25, "l"),
        ("2  Draw only on the firing line. Muzzles down range, always.", COND, .052, .33, "l"),
        ("3  Fire on the range officer's word. CEASE FIRE: stop, holster, step back.", COND, .052, .41, "l"),
        ("4  Nobody forward of the line until the officer calls the range clear.", COND, .052, .49, "l"),
        ("5  Reset the plates from the range control only.", COND, .052, .57, "l"),
        ("6  Spent cells go in the bin, not the sand.", COND, .052, .65, "l"),
        ("7  Machine lane: tethered drills only. Live machines never cross the berm.", COND, .052, .73, "l")]
tm = text_mask((W_, H_), body, pad=.05)
foot = text_mask((W_, H_), [("WARDEN RANGE  ·  WEST GATE WATCH  ·  WG-07", STENCIL2, .05, .88)])
b = spray(b, np.maximum(title, rule), RED * 1.1, wear * .6, .97, 41)
b = spray(b, tm, np.array([.09, .09, .085]), wear * .5, .96, 42)
b = spray(b, foot, OLIVE * .8, wear * .6, .9, 43)
b = grime(b, .2, 44)
finish_sign("TR_RangeOrders", b, n_, a_, .45)

# MACHINE LANE board (1.26 x 0.42 m, both faces)
W_, H_ = 1536, 512
b, n_, a_, wear = board((W_, H_), "metal_plate_02", np.array([.62, .50, .14]), .25)
stripe = np.zeros((H_, W_), np.float32); stripe[:int(H_ * .1)] = 1; stripe[int(H_ * .9):] = 1
b = spray(b, stripe, np.array([.07, .07, .06]), wear, .9, 51)
tm = text_mask((W_, H_), [("MACHINE LANE  4", STENCIL, .42, .43), ("TETHERED DRILLS ONLY  ·  STAND CLEAR OF THE GANTRY", STENCIL2, .1, .77)])
b = spray(b, tm, np.array([.07, .07, .06]), wear, .97, 52)
b = grime(b, .25, 53)
finish_sign("TR_LaneSign", b, n_, a_, .5)

# Lane number boards 1-4 (atlas of four 0.42 m squares): bone stencil numerals on olive board
W_, H_ = 2048, 512
b, n_, a_, wear = board((W_, H_), "plywood", OLIVE * .95, .35)
im = Image.new("L", (W_, H_), 0); dr = ImageDraw.Draw(im); fnt = ImageFont.truetype(STENCIL, int(H_ * .78))
for k in range(4):
    s = str(k + 1); bb = dr.textbbox((0, 0), s, font=fnt)
    dr.text((k * 512 + 256 - (bb[2] - bb[0]) / 2 - bb[0], H_ / 2 - (bb[3] - bb[1]) / 2 - bb[1]), s, font=fnt, fill=255)
    dr.rectangle([k * 512 + 26, 26, k * 512 + 486, 486], outline=255, width=14)
b = spray(b, np.asarray(im, np.float32) / 255, BONE, wear, .97, 61)
b = grime(b, .25, 62)
finish_sign("TR_LaneNumbers", b, n_, a_, .45)

# Distance marker boards "5 M" "10 M" "15 M" "20 M" (atlas of four 0.36 x 0.24 m plates): black on bone
W_, H_ = 2048, 340
b, n_, a_, wear = board((W_, H_), "rusty_painted_metal", BONE * .95, .05)
im = Image.new("L", (W_, H_), 0); dr = ImageDraw.Draw(im); fnt = ImageFont.truetype(STENCIL, int(H_ * .62))
for k, s in enumerate(["5 M", "10 M", "15 M", "20 M"]):
    bb = dr.textbbox((0, 0), s, font=fnt)
    dr.text((k * 512 + 256 - (bb[2] - bb[0]) / 2 - bb[0], H_ / 2 - (bb[3] - bb[1]) / 2 - bb[1]), s, font=fnt, fill=255)
b = spray(b, np.asarray(im, np.float32) / 255, np.array([.07, .07, .06]), wear * .7, .97, 71)
b = grime(b, .25, 72)
finish_sign("TR_DistanceNumbers", b, n_, a_, .4)

# Lane numbers painted on the revetment sleepers (alpha-clipped quads over the timber): bone paint with runs
W_, H_ = 2048, 512
im = Image.new("L", (W_, H_), 0); dr = ImageDraw.Draw(im); fnt = ImageFont.truetype(STENCIL, int(H_ * .72))
for k in range(4):
    s = str(k + 1); bb = dr.textbbox((0, 0), s, font=fnt)
    x0 = k * 512 + 256 - (bb[2] - bb[0]) / 2 - bb[0]; y0 = H_ * .44 - (bb[3] - bb[1]) / 2 - bb[1]
    dr.text((x0, y0), s, font=fnt, fill=255)
m = np.asarray(im, np.float32) / 255
rng = np.random.default_rng(81)
runs = np.zeros_like(m)
for k in range(4):                      # paint runs from the lower edge of each numeral
    cols = np.where(m[:, k * 512:(k + 1) * 512].max(0) > .5)[0]
    for c in rng.choice(cols, size=min(len(cols), 7), replace=False):
        x = k * 512 + c; ys = np.where(m[:, x] > .5)[0]
        if len(ys) == 0: continue
        y = ys.max(); L = int(rng.uniform(12, 60)); w = int(rng.integers(3, 7))
        runs[y:min(H_, y + L), max(0, x - w // 2):x + w // 2 + 1] = np.linspace(1, .2, min(H_, y + L) - y)[:, None]
m = np.clip(np.maximum(m, runs), 0, 1)
wearn = noise((H_, W_), 30, 4, 82)
alpha = np.clip(m * (1 - np.clip((wearn - .62) * 4, 0, 1)), 0, 1)
col = np.dstack([np.full((H_, W_), .82), np.full((H_, W_), .79), np.full((H_, W_), .70)]) * (0.85 + .15 * noise((H_, W_), 40, 3, 83))[..., None]
save_rgba(np.dstack([col, alpha]), "TR_LaneNumbersPaint_BaseMap.png")
flat = np.zeros((H_, W_, 3), np.float32); flat[..., :2] = .5; flat[..., 2] = 1
save_rgb(flat, "TR_LaneNumbersPaint_Normal.jpg", 95)
save_rgba(np.dstack([np.zeros((H_, W_)), np.ones((H_, W_)), np.zeros((H_, W_)), np.full((H_, W_), .35)]), "TR_LaneNumbersPaint_Mask.png")
MATS["TR_LaneNumbersPaint"] = {"base": "Assets/AthenHill/Art/TrainingRange/Textures/TR_LaneNumbersPaint_BaseMap.png",
                               "normal": None, "mask": "Assets/AthenHill/Art/TrainingRange/Textures/TR_LaneNumbersPaint_Mask.png",
                               "tile": 0, "smoothness": .35, "alphaClip": True, "cutoff": .4}

# ------------------------------------------------------------------ simple (untextured) materials
MATS["TR_Brass"] = {"color": [.62, .46, .2], "metallic": .9, "smoothness": .55}
MATS["TR_CellSteel"] = {"color": [.42, .43, .45], "metallic": .8, "smoothness": .5}
MATS["TR_CellBand"] = {"color": [.12, .45, .48], "metallic": .2, "smoothness": .5}
MATS["TR_RedLens"] = {"color": [.5, .05, .03], "emission": [1.0, .12, .05], "emissionIntensity": 3.0, "smoothness": .85}
MATS["TR_ChargeGlow"] = {"color": [.04, .2, .22], "emission": [.25, .85, .9], "emissionIntensity": 1.6, "smoothness": .8}
MATS["TR_LampGlow"] = {"color": [.6, .45, .25], "emission": [1.0, .78, .48], "emissionIntensity": 4.0, "smoothness": .5}
MATS["TR_LanternGlass"] = {"color": [.75, .72, .62], "alpha": .35, "transparent": True, "smoothness": .92}
MATS["TR_RedLead"] = {"color": [.45, .05, .04], "metallic": 0, "smoothness": .35}
MATS["TR_TargetPaint"] = {"color": [.78, .75, .66], "metallic": 0, "smoothness": .25}


# ------------------------------------------------------------------ decals (RGBA base colour + alpha)
def save_decal(name, rgb, a):
    img = np.dstack([np.broadcast_to(rgb, a.shape + (3,)) if np.ndim(rgb) == 1 else rgb, a])
    Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")


S = 1024
yy, xx = np.mgrid[0:S, 0:S] / S - .5
# painted line (long strip; U along the line): worn white paint, scuffed through where boots stand
H2, W2 = 128, 2048
n = noise((H2, W2), 40, 4, 91); edge = noise((H2, W2), 160, 2, 92)
v = np.abs(np.linspace(-1, 1, H2))[:, None]
a = np.clip((.62 - v + (edge - .5) * .18) / .08, 0, 1) * np.clip((n - .22) * 2.2, 0, 1) * .92
scuff = np.clip((noise((H2, W2), 6, 3, 93) - .62) * 3, 0, 1)
a *= 1 - scuff * .7
save_decal("TR_DecalPaintLine", np.dstack([.84 + 0 * n, .80 + 0 * n, .66 + 0 * n]), a)
# trodden ground: compacted, darker earth with overlapping boot prints
a = np.clip((.47 - np.hypot(xx, yy * 1.1) + (noise((S, S), 5, 5, 101) - .5) * .25) / .2, 0, 1) * .55
im = Image.new("L", (S, S), 0); dr = ImageDraw.Draw(im); rng = np.random.default_rng(102)
for _ in range(70):
    cx, cy = rng.normal(0, .18, 2) * S + S / 2; ang = rng.uniform(0, 6.28); L = 46; Wd = 18
    pts = [(cx + np.cos(ang) * L * u - np.sin(ang) * Wd * w, cy + np.sin(ang) * L * u + np.cos(ang) * Wd * w) for u, w in ((-1, -.8), (1, -1), (1, 1), (-1, .8))]
    dr.polygon(pts, fill=int(rng.uniform(70, 160)))
prints = np.asarray(im.filter(ImageFilter.GaussianBlur(2.2)), np.float32) / 255
a = np.clip(a + prints * .35 * np.clip(.5 - np.hypot(xx, yy) , 0, 1) * 2, 0, .8)
col = np.dstack([.36 + .05 * noise((S, S), 20, 3, 103), .29 + .04 * noise((S, S), 20, 3, 103), .21 + .03 * noise((S, S), 20, 3, 103)])
save_decal("TR_DecalTrodden", col, a)
# paint overspray round a plate's foot (repainted after every session): bone/white speckle, densest near the centre
r = np.hypot(xx, yy)
spk = (np.random.default_rng(111).random((S, S)) > .985).astype(np.float32)
spk = np.asarray(Image.fromarray((spk * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.8)), np.float32) / 255
mist = np.clip((.30 - r) / .25, 0, 1) * noise((S, S), 8, 4, 112)
a = np.clip(spk * np.clip((.48 - r) / .3, 0, 1) * 1.4 + mist * .45, 0, .95)
save_decal("TR_DecalOverspray", np.array([.86, .83, .74]), a)
# impact scars on timber/earth (vertical projection on the backstop face): pocks with splinter rays and dark cores
im = Image.new("L", (S, S), 0); core = Image.new("L", (S, S), 0); dr = ImageDraw.Draw(im); dc = ImageDraw.Draw(core)
rng = np.random.default_rng(121)
for _ in range(95):
    cx, cy = rng.normal(0, .17, 2) * S + S / 2; rad = rng.uniform(5, 15)
    dr.ellipse([cx - rad * 1.9, cy - rad * 1.6, cx + rad * 1.9, cy + rad * 1.6], fill=int(rng.uniform(90, 170)))
    for _k in range(int(rng.integers(3, 7))):
        ang = rng.uniform(0, 6.28); L = rad * rng.uniform(2, 4.5)
        dr.line([(cx, cy), (cx + np.cos(ang) * L, cy + np.sin(ang) * L)], fill=120, width=2)
    dc.ellipse([cx - rad * .6, cy - rad * .6, cx + rad * .6, cy + rad * .6], fill=255)
a1 = np.asarray(im.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
a2 = np.asarray(core.filter(ImageFilter.GaussianBlur(1.0)), np.float32) / 255
fade = np.clip((.5 - np.hypot(xx, yy * .8)) / .2, 0, 1)
a = np.clip(np.maximum(a1 * .75, a2), 0, 1) * fade
col = np.dstack([.20 * (1 - a2) + .05 * a2, .15 * (1 - a2) + .04 * a2, .10 * (1 - a2) + .03 * a2]) + np.dstack([a1 * .25, a1 * .2, a1 * .14]) * (1 - a2[..., None])
save_decal("TR_DecalImpacts", col, a)
# hit-zone ring painted on the stripped worker droid (projected onto its chest): bone ring with a cross
im = Image.new("L", (S, S), 0); dr = ImageDraw.Draw(im)
dr.ellipse([140, 140, S - 140, S - 140], outline=255, width=70); dr.ellipse([400, 400, S - 400, S - 400], fill=255)
dr.line([(S / 2, 60), (S / 2, 230)], fill=255, width=40); dr.line([(S / 2, S - 230), (S / 2, S - 60)], fill=255, width=40)
dr.line([(60, S / 2), (230, S / 2)], fill=255, width=40); dr.line([(S - 230, S / 2), (S - 60, S / 2)], fill=255, width=40)
a = np.asarray(im.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255 * np.clip((noise((S, S), 20, 4, 131) - .2) * 2, 0, 1) * .92
save_decal("TR_DecalHitZone", np.array([.82, .78, .66]), a)
# oil and coolant drips under the docks / bench (darker, glossy-looking; alpha only)
r = np.hypot(xx * 1.15, yy) + (noise((S, S), 5, 5, 141) - .5) * .3
a = np.clip((.34 - r) / .14, 0, 1) ** 1.3 * (.5 + .5 * noise((S, S), 22, 3, 142))
spots = (np.random.default_rng(143).random((S, S)) > .9975).astype(np.float32)
spots = np.asarray(Image.fromarray((spots * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
a = np.clip(np.maximum(a, spots * np.clip((.48 - r) / .2, 0, 1)), 0, .88)
save_decal("TR_DecalOil", np.array([.05, .045, .04]), a)

old = json.loads((OUT / "materials.json").read_text()) if (OUT / "materials.json").exists() else {}
old.update(MATS)                        # keeps the Poly Haven prop records written by prepare_prop_textures.py
(OUT / "materials.json").write_text(json.dumps(old, indent=1))
print("written", len(MATS), "materials and decals")
