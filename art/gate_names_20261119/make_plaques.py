#!/usr/bin/env python3
"""Gate name plaque texture (19 Nov 2026): the "— EAST GATE —" iron plate that covers the baked "— WEST GATE —"
plaques on the two Meshy District gate arches at the +X spawn.

Matched to the baked plaque (measured by measure_plaques.py from the Meshy atlas): dark iron plate (albedo about
0.20/0.17/0.14, metallic, smoothness about 0.2), ivory lettering (about 0.75/0.69/0.62) in a bold sans, cap height
55 % of the plate, the name filling 62 % of its width between two dashes, worn bright edges, a bolt in each corner.

    uv run --with pillow --with numpy python make_plaques.py

To rename the gate again, change GATE_NAME and re-run; the Unity pass only reads the textures.
Outputs (unity/.../Art/GateNames/Textures): GN_Plaque_BaseMap.jpg, GN_Plaque_Normal.jpg, GN_Plaque_Mask.png (URP Lit:
R metallic, G occlusion, A smoothness), and review/plaque_preview.png.

Texture layout (2048 x 512): rows 0..PLATE_H-1 are the plate's front face (UV v from 1 down to 1 - PLATE_H/512);
rows EDGE0..511 are plain worn iron used by the plate's sides and back (UV v 0 .. 1 - EDGE0/512).
Sources: Poly Haven metal_plate_02 and rusty_metal_02 (CC0, art/west_gate_20260926/polyhaven), Noto Sans Bold (OFL,
art/hall_district_20260930/fonts). Procedural; no generated imagery.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

GATE_NAME = "EAST GATE"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PH = ROOT / "art/west_gate_20260926/polyhaven/textures"
FONT = ROOT / "art/hall_district_20260930/fonts/NotoSans-Bold.ttf"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/GateNames/Textures"
W, H = 2048, 512
PLATE_H = 435          # front face rows: 2048 / 435 = 4.71, the plate's 4.54 x 0.965 m aspect
EDGE0 = 452            # side/back strip rows
PLATE = np.array([.20, .17, .14])
IVORY = np.array([.745, .686, .62])
EDGE = np.array([.42, .39, .35])
RUST = np.array([.36, .18, .10])


def load(name, kind):
    im = Image.open(PH / name / f"{name}_{kind}_2k.jpg").convert("RGB")
    return np.asarray(im, np.float32) / 255


def lum(a):
    return a[..., 0] * .3 + a[..., 1] * .59 + a[..., 2] * .11


def noise(shape, scale, octaves=4, seed=0):
    r = np.random.default_rng(seed); h, w = shape; out = np.zeros(shape, np.float32); amp = 1; tot = 0
    for _ in range(octaves):
        s = max(2, int(scale)); scale *= 2
        g = r.random((s + 1, int(s * w / h) + 1)).astype(np.float32)
        out += np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 * amp
        tot += amp; amp *= .5
    return out / tot


def blur(m, r):
    return np.asarray(Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255


# Physical layout measured on the baked plaque (4.465 x 0.90 m): cap height 0.50 m, name 2.79 m wide, dashes 0.375 m
# long and 0.045 m thick, centred 0.40 m in from the baked plate's ends. The new plate is PLATE_M (a little larger).
PLATE_M = (4.54, 0.965)
BAKED_M = (4.465, 0.90)


def text_mask(h, w):
    """'—  EAST GATE  —' laid out at the baked plaque's physical sizes on the slightly larger plate."""
    pw, ph = PLATE_M; mx = (pw - BAKED_M[0]) / 2
    big = 4  # draw large then scale into the box (the baked lettering is a plain bold sans)
    f = ImageFont.truetype(str(FONT), 400)
    probe = Image.new("L", (10, 10)); d = ImageDraw.Draw(probe)
    bb = d.textbbox((0, 0), GATE_NAME, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    im = Image.new("L", (tw + 40, th + 40), 0); ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), GATE_NAME, font=f, fill=255)
    im = im.crop((20, 20, 20 + tw, 20 + th))
    cap_h = int(round(.50 / ph * h)); box_w = int(round(2.79 / pw * w))
    natural_w = tw * cap_h / th
    sx = box_w / natural_w
    im = im.resize((box_w, cap_h), Image.LANCZOS)
    m = Image.new("L", (w, h), 0)
    m.paste(im, ((w - box_w) // 2, (h - cap_h) // 2))
    dd = ImageDraw.Draw(m)
    dl, dt = .375 / pw * w, .045 / ph * h
    for cx in ((mx + .40) / pw * w, w - (mx + .40) / pw * w):
        dd.rectangle([cx - dl / 2, h * .5 - dt / 2, cx + dl / 2, h * .5 + dt / 2], fill=255)
    return np.asarray(m, np.float32) / 255, sx


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (HERE / "review").mkdir(exist_ok=True)
    diff, nor, arm = load("metal_plate_02", "diff"), load("metal_plate_02", "nor_gl"), load("metal_plate_02", "arm")
    rdiff = load("rusty_metal_02", "diff")
    # 2k sources: take a 2048 x 512 window (keeps the scan's texel scale, about 450 px/m on a 4.5 m plate)
    y0 = 700
    diff, nor, arm, rdiff = (a[y0:y0 + H, :W] for a in (diff, nor, arm, rdiff))
    # flatten the scan's own panel seams: keep only fine detail of its normal map
    low = np.asarray(Image.fromarray((nor * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)), np.float32) / 255
    nx, ny = (nor[..., 0] - low[..., 0]) * .7, (nor[..., 1] - low[..., 1]) * .7

    l = lum(diff); base = PLATE * (l / l.mean())[..., None] ** .55
    base = base * (.9 + .2 * noise((H, W), 3, 4, 3))[..., None]
    rust = np.clip((noise((H, W), 4, 5, 11) - .58) * 3.5, 0, 1)
    vert = np.clip(np.linspace(-.2, .5, H)[:, None] * noise((H, W), 2, 3, 12) * 1.6, 0, 1)  # run-off below bolts/top
    rust = np.clip(rust + vert * .5, 0, 1) * .7
    base = base * (1 - rust[..., None]) + RUST * (lum(rdiff) / lum(rdiff).mean())[..., None] * rust[..., None]

    # front face edges: worn bright arris all round, a thin shadowed line inside it
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.minimum.reduce([xx, W - 1 - xx, yy, PLATE_H - 1 - yy]).astype(np.float32)
    n_e = noise((H, W), 10, 3, 21)
    arris = np.clip(1 - dist / (3 + 4 * n_e), 0, 1) * (dist >= 0)
    inner = np.exp(-((dist - 11) / 3) ** 2) * .25
    base = base * (1 - arris[..., None] * .8) + EDGE * arris[..., None] * .8
    base = base * (1 - inner[..., None])

    # corner bolts: domed heads with a bright worn crown
    bolts = np.zeros((H, W), np.float32); hx = np.zeros((H, W), np.float32); hy = np.zeros((H, W), np.float32)
    R = 11
    for cx, cy in ((26, 26), (W - 27, 26), (26, PLATE_H - 27), (W - 27, PLATE_H - 27)):
        dx, dy = xx - cx, yy - cy; rr = np.sqrt(dx * dx + dy * dy)
        dome = np.clip(1 - (rr / R) ** 2, 0, 1)
        bolts = np.maximum(bolts, (rr < R).astype(np.float32))
        hx += np.where(rr < R, dx / R, 0) * .8; hy += np.where(rr < R, dy / R, 0) * .8
        ring = np.exp(-((rr - R - 2) / 1.5) ** 2) * .5
        base = base * (1 - ring[..., None])
        inside = (rr < R)[..., None].astype(np.float32)
        head = PLATE * 1.3 * (.5 + .5 * dome[..., None]) + EDGE * .5 * dome[..., None] ** 3
        base = base * (1 - inside) + head * inside

    # lettering: sprayed ivory paint, softly eroded (matches the baked plaque's grainy letters)
    front = np.zeros((H, W), np.float32)
    tm, sx = text_mask(PLATE_H, W)
    front[:PLATE_H] = tm
    soft = blur(front, 1.2)
    wear = np.clip((noise((H, W), 30, 3, 31) - .62) * 4, 0, 1) * .55 + np.clip((noise((H, W), 6, 4, 32) - .7) * 3, 0, 1) * .5
    grain = np.random.default_rng(33).random((H, W)).astype(np.float32)
    cover = np.clip(soft * (1 - wear) * (.86 + .14 * grain), 0, 1)
    shade = (l / l.mean())[..., None] ** .35
    base = base * (1 - cover[..., None]) + IVORY * shade * cover[..., None]

    # dust settling on the upper half of the plate and in the letters' lower edges
    dust = np.clip(noise((H, W), 5, 4, 41) - .45, 0, 1) * np.clip(1 - yy / PLATE_H, 0, 1) * .35
    base = base * (1 - dust[..., None]) + np.array([.55, .46, .35]) * dust[..., None]

    # side / back strip: plain worn iron, no lettering, no bolts
    strip = PLATE * (l / l.mean())[..., None] ** .55 * (1 - rust[..., None] * .5) + RUST * rust[..., None] * .5
    base[PLATE_H:] = strip[PLATE_H:]
    base[PLATE_H:EDGE0] = base[PLATE_H:EDGE0] * .8  # gutter between the regions (never sampled)

    # normal map: fine scan detail + bolt domes + a hair of paint relief
    paint_h = blur(cover, 1.0)
    gy, gx = np.gradient(paint_h)
    nx2 = nx * (1 - bolts) + hx - gx * 2
    ny2 = ny * (1 - bolts) - hy + gy * 2   # OpenGL convention (green up): image rows grow downwards
    nz = np.ones_like(nx2)
    norm = np.sqrt(nx2 ** 2 + ny2 ** 2 + nz ** 2)
    nmap = np.dstack([nx2 / norm * .5 + .5, ny2 / norm * .5 + .5, nz / norm * .5 + .5])

    metal = .9 * (1 - rust * .7) * (1 - cover * .5)
    smooth = .2 * (1 - rust * .5) + cover * .03 + bolts * .1 + arris * .1
    ao = 1 - inner * .6
    mask = np.dstack([metal, ao, np.zeros_like(metal), smooth])

    Image.fromarray((np.clip(base, 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(OUT / "GN_Plaque_BaseMap.jpg", quality=93)
    Image.fromarray((np.clip(nmap, 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(OUT / "GN_Plaque_Normal.jpg", quality=95)
    Image.fromarray((np.clip(mask, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(OUT / "GN_Plaque_Mask.png")
    Image.fromarray((np.clip(base[:PLATE_H], 0, 1) * 255 + .5).astype(np.uint8), "RGB").save(HERE / "review/plaque_preview.png")
    rec = {"gate_name": GATE_NAME, "size": [W, H], "plate_rows": PLATE_H, "edge_rows_from": EDGE0,
           "uv_front_v": [round(1 - PLATE_H / H, 5), 1.0], "uv_edge_v": [0.0, round(1 - EDGE0 / H, 5)],
           "letter_horizontal_scale": round(float(sx), 3),
           "albedo": {"plate": PLATE.tolist(), "letters": IVORY.tolist()}}
    (HERE / "plaque_texture.json").write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec))


if __name__ == "__main__":
    main()
