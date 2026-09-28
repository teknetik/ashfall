#!/usr/bin/env python3
"""West Gate texture kit (26 Sep 2026): tinted tiling paints and stencilled signs.

All inputs are CC0 Poly Haven scans (polyhaven/textures) and OFL fonts (fonts/). Outputs go to
unity/.../Art/WestGate/Textures as <Name>_BaseMap / _Normal / _Mask (URP Lit: R metal, G AO, A smoothness).
Lettering is painted into the albedo, eroded by the plate's own wear, never floating geometry.
"""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
PH = HERE / "polyhaven/textures"
FONTS = HERE / "fonts"
OUT = HERE.parents[1] / "unity/AthenHill/Assets/AthenHill/Art/WestGate/Textures"
rng = np.random.default_rng(2609)
REC = {}

STENCIL = str(FONTS / "stardosstencil__StardosStencil-Bold.ttf")
STENCIL2 = str(FONTS / "allertastencil__AllertaStencil-Regular.ttf")
COND = str(FONTS / "barlowcondensed__BarlowCondensed-SemiBold.ttf")
BONE = np.array([.80, .76, .64]); OLIVE = np.array([.25, .27, .19]); RUST = np.array([.45, .19, .12])
CYAN = np.array([.32, .78, .80]); HAZ = np.array([.78, .60, .12])


def load(name, kind, size=None):
    p = PH / name / f"{name}_{kind}_2k.jpg"
    im = Image.open(p).convert("RGB" if kind != "disp" else "L")
    if size: im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255


def lum(a): return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def save_rgb(a, name, q=92):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(OUT / name, quality=q)


def save_rgba(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / name)


def mask_from(arm, metal=None):
    m = arm[..., 2] if metal is None else np.full(arm.shape[:2], metal, np.float32)
    return np.dstack([m, arm[..., 0], np.zeros_like(m), 1 - arm[..., 1]])


def retint(diff, target, keep=.35):
    """Re-colour a painted scan: keep luminance variation, move mean colour to target."""
    l = lum(diff)[..., None]; mean = l.mean()
    return np.clip(target * (l / mean) * (1 - keep) + diff * keep * (target.mean() / diff.mean()), 0, 1)


def paint_set(name, src, target, keep=.3, metal=None, rough_add=0.0, rust_from="hue", darken=1.0):
    diff, nor, arm = load(src, "diff"), load(src, "nor_gl"), load(src, "arm")
    diff = diff * darken
    if target is not None:
        # rust/bare patches survive the repaint: by hue on non-red paints, by metal mask on red paint
        if rust_from == "hue":
            rustiness = np.clip((diff[..., 0] - diff[..., 1]) * 4 - .15, 0, 1)[..., None]
        else:
            rustiness = np.clip((arm[..., 1] - .72) * 5, 0, 1)[..., None] * .8
        diff = retint(diff, target, keep) * (1 - rustiness) + diff * rustiness
    arm = arm.copy(); arm[..., 1] = np.clip(arm[..., 1] + rough_add, 0, 1)
    save_rgb(diff, f"{name}_BaseMap.jpg"); save_rgb(nor, f"{name}_Normal.jpg", 95); save_rgba(mask_from(arm, metal), f"{name}_Mask.png")
    REC[name] = {"source": src, "tint": None if target is None else list(map(float, target))}
    return diff, nor, arm


def noise(shape, scale, octaves=4, seed=0):
    r = np.random.default_rng(seed); h, w = shape; out = np.zeros(shape, np.float32); amp = 1; tot = 0
    for o in range(octaves):
        s = max(2, int(scale * 2 ** o))
        g = r.random((s + 1, s + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


def text_mask(size, lines, pad=.06):
    """lines: [(text, font, rel_height, y_center_rel)] -> float mask."""
    W, H = size; im = Image.new("L", size, 0); d = ImageDraw.Draw(im)
    for text, font, rh, yc, *rest in lines:
        align = rest[0] if rest else "c"
        fs = int(H * rh); f = ImageFont.truetype(font, fs)
        while True:
            bb = d.textbbox((0, 0), text, font=f)
            if bb[2] - bb[0] <= W * (1 - 2 * pad) or fs < 8: break
            fs = int(fs * .95); f = ImageFont.truetype(font, fs)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        x = (W - tw) / 2 - bb[0] if align == "c" else W * pad - bb[0]
        d.text((x, H * yc - th / 2 - bb[1]), text, font=f, fill=255)
    return np.asarray(im, np.float32) / 255


def spray(base, mask, color, wear, strength=.95, seed=1):
    """Stencil spray: slightly soft edge, faint overspray, eroded by wear (0..1, 1=bare)."""
    h, w = mask.shape
    soft = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(max(1, w / 1400))), np.float32) / 255
    over = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(w / 220)), np.float32) / 255
    n = noise((h, w), 24, 4, seed)
    cover = np.clip(soft * strength * (1 - np.clip((wear - .45) * 3, 0, 1)) * (0.82 + .18 * n), 0, 1) + over * .10 * n
    cover = np.clip(cover, 0, 1)[..., None]
    shade = (lum(base) / max(lum(base).mean(), 1e-3))[..., None] ** .6
    return base * (1 - cover) + color * shade * cover


def grime(base, strength=.25, streak=True, seed=3):
    h, w = base.shape[:2]
    n = noise((h, w), 6, 5, seed)
    g = base * (1 - strength * n[..., None] * .6)
    if streak:
        s = np.asarray(Image.fromarray((rng.random((1, w)) * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255
        v = np.linspace(0, 1, h)[:, None] ** 1.5
        g = g * (1 - (s * v * strength * .5)[..., None])
    dust = np.clip(np.linspace(-.2, .6, h)[:, None] * noise((h, w), 10, 4, seed + 7), 0, 1)[..., None]
    return g * (1 - dust * .35) + np.array([.62, .52, .40]) * dust * .35


def sign(name, size_px, lines, plate="metal_plate_02", plate_color=OLIVE, ink=BONE, emblem=None, stripe=None, border=True, seed=5):
    W, H = size_px
    diff = load(plate, "diff", size_px); nor = load(plate, "nor_gl", size_px); arm = load(plate, "arm", size_px)
    base = retint(diff, plate_color, .25)
    wear = np.clip(arm[..., 1] * 1.2 - .25 + (noise((H, W), 12, 4, seed) - .5) * .5, 0, 1)
    if stripe is not None:
        m = np.zeros((H, W), np.float32); y0, y1 = int(H * stripe[0]), int(H * stripe[1]); m[y0:y1] = 1
        base = spray(base, m, stripe[2], wear, .9, seed + 1)
    if border:
        m = np.zeros((H, W), np.float32); b = int(min(W, H) * .035)
        m[b:b + max(3, b // 3)] = 1; m[H - b - max(3, b // 3):H - b] = 1; m[:, b:b + max(3, b // 3)] = 1; m[:, W - b - max(3, b // 3):W - b] = 1
        base = spray(base, m, ink, wear, .85, seed + 2)
    tm = text_mask(size_px, lines)
    if emblem is not None:
        tm = np.maximum(tm, emblem(W, H))
    base = spray(base, tm, ink, wear, .97, seed + 3)
    base = grime(base, .22, True, seed + 4)
    save_rgb(base, f"{name}_BaseMap.jpg"); save_rgb(nor, f"{name}_Normal.jpg", 95); save_rgba(mask_from(arm), f"{name}_Mask.png")
    REC[name] = {"plate": plate, "size_px": size_px, "text": [l[0] for l in lines]}


def emblem_wall_spire(cx, cy, s):
    """Warden wall-and-spire mark (matches the district banner): crenellated wall with a spire."""
    def draw(W, H):
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); X, Y, S = cx * W, cy * H, s * H
        d.rectangle([X - S * .9, Y + S * .05, X + S * .9, Y + S * .45], fill=255)
        for k in (-.9, -.45, .27, .72):
            d.rectangle([X + S * k, Y - S * .2, X + S * (k + .18), Y + S * .05], fill=255)
        d.polygon([(X - S * .2, Y + S * .05), (X - S * .2, Y - S * .8), (X, Y - S * 1.2), (X + S * .2, Y - S * .8), (X + S * .2, Y + S * .05)], fill=255)
        return np.asarray(im, np.float32) / 255
    return draw


def arrow(cx, cy, s, right=True):
    def draw(W, H):
        im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); X, Y, S = cx * W, cy * H, s * H; k = 1 if right else -1
        d.polygon([(X - k * S, Y - S * .18), (X + k * S * .3, Y - S * .18), (X + k * S * .3, Y - S * .45), (X + k * S, Y), (X + k * S * .3, Y + S * .45), (X + k * S * .3, Y + S * .18), (X - k * S, Y + S * .18)], fill=255)
        return np.asarray(im, np.float32) / 255
    return draw


def both(*fs):
    return lambda W, H: np.maximum.reduce([f(W, H) for f in fs])


# ---- tiling paints (UV in metres; Unity tiling = 1 / tile size) ----
paint_set("WG_OlivePaint", "green_metal_rust", np.array([.30, .30, .22]), .12)                 # Warden olive drab (1 m)
paint_set("WG_BonePaint", "rusty_painted_metal", BONE * .95, .03, rust_from="rough")                  # bone-white trims (2.2 m)
paint_set("WG_SandPaint", "rusty_painted_metal", np.array([.60, .50, .36]), .03, rust_from="rough")  # sun-bleached sand paint (2.2 m)
paint_set("WG_RustSteel", "rusty_metal_02", None, darken=.72)                               # raw rusted steel (1 m)
paint_set("WG_PlateSteel", "metal_plate_02", np.array([.36, .35, .31]), .45)    # riveted plating (2 m)
paint_set("WG_ShutterPaint", "painted_metal_shutter", np.array([.30, .30, .22]), .15)          # roller shutter slats (2 m)
paint_set("WG_Concrete", "concrete_floor_damaged_01", np.array([.64, .58, .49]), .45, metal=0)  # 5 m
paint_set("WG_Plywood", "plywood", None, metal=0)                               # 0.5 m
paint_set("WG_Hessian", "hessian_230", np.array([.55, .47, .34]), .35, metal=0, rough_add=.05)  # sandbag burlap (0.27 m)
paint_set("WG_ShadeCloth", "hessian_230", np.array([.50, .45, .33]), .5, metal=0)

# hazard stripes on worn paint (2.2 m)
d, n, a = load("rusty_painted_metal", "diff"), load("rusty_painted_metal", "nor_gl"), load("rusty_painted_metal", "arm")
H, W = d.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
stripes = (((xx + yy) // (W // 6)) % 2 == 0).astype(np.float32)
wear = np.clip(a[..., 1] * 1.3 - .3, 0, 1)
blackish = retint(d, np.array([.07, .07, .065]), .3)
haz = spray(blackish, stripes, HAZ * 1.18, wear * .7, .98, 11)
haz = grime(haz, .1, True, 12)
save_rgb(haz, "WG_Hazard_BaseMap.jpg"); save_rgb(n, "WG_Hazard_Normal.jpg", 95); save_rgba(mask_from(a), "WG_Hazard_Mask.png"); REC["WG_Hazard"] = {"source": "rusty_painted_metal"}

# ---- signs (atlas-free, one material each; aspect = physical size) ----
sign("WG_SignGateInner", (2048, 512), [("WEST GATE", STENCIL, .46, .36), ("OUTER BERMS  ·  REPORT TO THE WARDEN POST", STENCIL2, .13, .78)],
     emblem=None, stripe=(.60, .63, RUST), seed=21)
sign("WG_SignGateOuter", (2048, 512), [("WARD", STENCIL, .50, .36), ("WEST GATE  ·  WEAPONS HOLSTER INSIDE THE WALLS", STENCIL2, .12, .80)],
     emblem=None, stripe=(.63, .66, RUST), seed=23)
sign("WG_SignPost", (2048, 512), [("WARDEN POST", STENCIL, .40, .38), ("WEST GATE WATCH  ·  WG-07", STENCIL2, .15, .78)], plate="container_side",
     plate_color=OLIVE * 1.15, border=False, seed=25)
sign("WG_SignArms", (1024, 512), [("ARMS", STENCIL, .48, .34), ("ISSUE  ·  SCRAP PISTOL  ·  NANO CHARGE", STENCIL2, .11, .78)], plate_color=OLIVE * .95,
     stripe=(.58, .61, CYAN * .8), seed=27)
sign("WG_SignRange", (2048, 1024), [("WARDEN", STENCIL2, .11, .17), ("TRAINING RANGE", STENCIL, .22, .40), ("3 STEEL PLATES  ·  FIRE FROM THE LINE", STENCIL2, .085, .66)],
     plate_color=np.array([.55, .20, .13]), ink=BONE, emblem=arrow(.5, .86, .13), seed=29)
sign("WG_SignFiringLine", (1024, 256), [("FIRING LINE", STENCIL, .62, .5)], plate_color=np.array([.08, .08, .075]), ink=HAZ, border=False, seed=31)
sign("WG_SignLiveFire", (1024, 768), [("LIVE FIRE", STENCIL, .26, .3), ("KEEP CLEAR OF THE RANGE", STENCIL2, .1, .62), ("WHEN THE FLAG IS UP", STENCIL2, .1, .78)],
     plate_color=np.array([.62, .50, .14]), ink=np.array([.07, .07, .06]), border=True, seed=33)
sign("WG_SignRangeControl", (1024, 512), [("RANGE CONTROL", STENCIL, .26, .32), ("E  ·  RESET THE PLATES", STENCIL2, .14, .72)],
     plate="metal_plate_02", plate_color=OLIVE * .9, stripe=(.52, .55, CYAN * .8), seed=35)
sign("WG_SignBriefing", (1024, 256), [("FIELD BRIEFING", STENCIL, .56, .5)], plate_color=OLIVE, border=False, seed=37)

# ---- Warden banner: olive cloth, bone wall-and-spire, rust band, frayed hem (alpha) ----
BW, BH = 1024, 2048
cloth = load("hessian_230", "diff", (BW, BH)); cn = load("hessian_230", "nor_gl", (BW, BH)); ca = load("hessian_230", "arm", (BW, BH))
# fine weave repeats: tile 4x4 to keep thread scale on a 0.9 x 1.8 m banner
def tile(a, k):
    h, w = a.shape[:2]; small = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((w // k, h // k), Image.LANCZOS), np.float32) / 255
    return np.tile(small, (k, k, 1) if a.ndim == 3 else (k, k))
cloth, cn, ca = tile(cloth, 4), tile(cn, 4), tile(ca, 4)
ban = retint(cloth, OLIVE * 1.05, .15)
band = np.zeros((BH, BW), np.float32); band[int(BH * .70):int(BH * .74)] = 1
wear = np.clip(noise((BH, BW), 10, 4, 41) - .1, 0, 1)
ban = spray(ban, band, RUST * 1.1, wear * .6, .95, 42)
ban = spray(ban, emblem_wall_spire(.5, .38, .17)(BW, BH), BONE, wear * .7, .95, 43)
ban = grime(ban, .3, True, 44)
fade = np.linspace(0, 1, BH)[:, None, None] ** 3; ban = ban * (1 - fade * .25) + np.array([.6, .5, .38]) * fade * .25
hem = np.ones((BH, BW), np.float32); edge = BH * (.965 + .02 * noise((1, BW), 40, 3, 45)[0]); yy = np.arange(BH)[:, None]
hem = (yy < edge[None, :]).astype(np.float32)
Image.fromarray((np.dstack([np.clip(ban, 0, 1), hem]) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "WG_Banner_BaseMap.png")
save_rgb(cn, "WG_Banner_Normal.jpg", 95); save_rgba(mask_from(ca, 0), "WG_Banner_Mask.png"); REC["WG_Banner"] = {"source": "hessian_230", "alpha": "hem"}

(OUT / "textures.json").write_text(json.dumps(REC, indent=1))
print("written", len(REC))


# ---- pinned papers for the field briefing board (hand-drawn map, notice, roster) ----
def paper(size, seed):
    W, H = size; n = noise((H, W), 8, 5, seed); f = noise((H, W), 60, 2, seed + 1)
    base = np.array([.86, .82, .70]) * (0.9 + .1 * n[..., None]) * (0.97 + .03 * f[..., None])
    # fold lines and a sun-faded top edge
    for x in (W // 2,):
        base[:, max(0, x - 2):x + 2] *= .9
    base[:H // 12] *= np.linspace(.92, 1, H // 12)[:, None, None]
    stain = np.clip((noise((H, W), 3, 3, seed + 2) - .62) * 4, 0, 1)[..., None]
    return base * (1 - stain * .18) + np.array([.55, .42, .25]) * stain * .18


def ink(base, draw_fn, color=(.12, .12, .14), blur=1.0):
    H, W = base.shape[:2]; im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); draw_fn(d, W, H)
    m = np.asarray(im.filter(ImageFilter.GaussianBlur(blur)), np.float32)[..., None] / 255
    return base * (1 - m * .92) + np.array(color) * m * .92


def paper_set(name, size, draw_fn, seed, accent=None):
    b = paper(size, seed); b = ink(b, draw_fn)
    if accent: b = ink(b, accent, (.55, .12, .08), 1.2)
    save_rgb(np.clip(b, 0, 1), f"{name}_BaseMap.jpg")
    flat = np.zeros(b.shape[:2] + (3,), np.float32); flat[..., 0] = .5; flat[..., 1] = .5; flat[..., 2] = 1
    save_rgb(flat, f"{name}_Normal.jpg", 95)
    m = np.dstack([np.zeros(b.shape[:2]), np.ones(b.shape[:2]), np.zeros(b.shape[:2]), np.full(b.shape[:2], .12)])
    save_rgba(m, f"{name}_Mask.png"); REC[name] = {"source": "procedural paper, OFL fonts"}


def map_draw(d, W, H):
    f = ImageFont.truetype(COND, 34); fs = ImageFont.truetype(COND, 24)
    d.text((40, 24), "WEST GATE — OUTER BERMS  (sketch, not to scale)", font=f, fill=255)
    d.line([(W - 60, 90), (W - 60, H - 40)], fill=255, width=8)                        # the wall
    d.text((W - 190, 100), "WARD", font=f, fill=255)
    d.rectangle([W - 70, H * .42, W - 50, H * .52], fill=0)                                # gate gap
    d.text((W - 250, H * .44), "GATE ▶", font=fs, fill=255)
    pts = [(W - 70, H * .47), (W * .70, H * .48), (W * .52, H * .52), (W * .38, H * .64), (W * .33, H * .82), (W * .36, H * .95)]
    d.line(pts, fill=255, width=5, joint="curve")
    d.text((W * .40, H * .56), "service road", font=fs, fill=255)
    d.rectangle([W * .52, H * .58, W * .62, H * .64], outline=255, width=4); d.text((W * .50, H * .65), "POST", font=fs, fill=255)
    for i, (x, y) in enumerate(((W * .30, H * .30), (W * .24, H * .22), (W * .31, H * .14))):
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=255, width=4); d.text((x + 14, y - 14), str(i + 1), font=fs, fill=255)
    d.line([(W * .68, H * .30), (W * .34, H * .24)], fill=255, width=2)
    d.text((W * .52, H * .20), "RANGE", font=fs, fill=255)
    d.text((W * .12, H * .88), "MACHINE DEPOT", font=f, fill=255)


def map_accent(d, W, H):
    x, y = W * .36, H * .95; d.line([(x - 26, y - 26), (x + 26, y + 26)], fill=255, width=7); d.line([(x - 26, y + 26), (x + 26, y - 26)], fill=255, width=7)
    d.text((W * .40, H * .90), "NEST — do not approach alone", font=ImageFont.truetype(COND, 26), fill=255)
    d.ellipse([W * .45, H * .70, W * .60, H * .80], outline=255, width=4); d.text((W * .62, H * .73), "drone seen", font=ImageFont.truetype(COND, 24), fill=255)


def notice_draw(d, W, H):
    t = ImageFont.truetype(STENCIL, 64); f = ImageFont.truetype(COND, 34)
    d.text((40, 30), "NOTICE", font=t, fill=255)
    lines = ["Feral machines active on", "the old service road.", "", "Draw arms at the post before", "passing the boom.", "", "If hurt: break contact,", "fall back to the post.", "", "— Warden Ossa, West Gate watch"]
    for i, l in enumerate(lines): d.text((40, 130 + i * 44), l, font=f, fill=255)


def roster_draw(d, W, H):
    t = ImageFont.truetype(COND, 44); f = ImageFont.truetype(COND, 30)
    d.text((30, 26), "WEST GATE WATCH — ROSTER", font=t, fill=255)
    rows = [("DAWN", "Ossa / Rell"), ("NOON", "Ossa / Deyne"), ("DUSK", "Rell / Maro"), ("NIGHT", "Tavi / Kesh"), ("RANGE", "Ossa — plates 1–3"), ("DEPOT", "patrol: 2 min reset")]
    for i, (a, b) in enumerate(rows):
        y = 110 + i * 64; d.line([(30, y + 50), (W - 30, y + 50)], fill=255, width=2); d.text((36, y), a, font=f, fill=255); d.text((220, y), b, font=f, fill=255)


paper_set("WG_PaperMap", (1024, 768), map_draw, 61, map_accent)
paper_set("WG_PaperNotice", (512, 768), notice_draw, 62)
paper_set("WG_PaperRoster", (768, 768), roster_draw, 63)
(OUT / "textures.json").write_text(json.dumps(REC, indent=1))
print("papers written")
