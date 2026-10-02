"""Salvage shop props: Unity maps (1 Oct 2026). Run after prepare.py:
    uv run --with pillow --with numpy python textures.py

* URP Lit mask per prop from the Meshy glTF metal-rough map (R metallic = B x metal_scale, G occlusion 1, B 0,
  A smoothness = 1 - G), written next to the prop's models; a 512 px metallic/roughness preview stays in <src>/maps/.
* SS_FabScreen: the workbench's status display (original art, no text or symbols from real products): dark glass, a
  part schematic with a deposition ring, a layer-progress grid, a segmented bar and a flux trace, in restrained cyan
  with one amber status mark. Drawn at the overlay quad's aspect and stored at 2048 x 512 (power of two); the quad's
  UVs stretch it back.
"""
import json, math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Props"
MATS = ROOT / "unity/AthenHill/Assets/AthenHill/Art/SalvageShop/Materials"
man = json.loads((PROPS / "salvage-shop-props.json").read_text())

for uid, e in man.items():
    src = ROOT / e["maps"]["MetalRoughSource"]
    x = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    rough, metal = x[..., 1], x[..., 2]
    ms = e.get("metal_scale", 1.0)
    m = np.stack([np.clip(metal * ms, 0, 1), np.ones_like(metal), np.zeros_like(metal), 1 - rough], -1)
    Image.fromarray((m * 255 + 0.5).astype(np.uint8), "RGBA").save(PROPS / uid / e["maps"]["Mask"])
    prev = np.concatenate([metal, rough], 1)
    Image.fromarray((prev * 255).astype(np.uint8), "L").resize((1024, 512)).save(src.parent / "metallic_roughness_preview.png")
    e["mask_stats"] = {"metallic_mean": round(float(metal.mean() * ms), 4), "metallic_over_half": round(float((metal * ms > 0.5).mean()), 4),
                       "smoothness_mean": round(float(1 - rough.mean()), 4)}
    print(uid, e["mask_stats"], flush=True)

# ------------------------------------------------------------------ fabricator screen
wb = man.get("SS_Workbench")
if wb and "screen" in wb:
    INSET = (0.93, 0.84)                                   # bezel: the plate's corner bolts stay visible
    pw, ph = wb["screen"]["panel_size"]
    qw, qh = pw * INSET[0], ph * INSET[1]
    wb["screen"]["quad_size"] = [round(qw, 4), round(qh, 4)]
    H = 512
    W = int(round(H * qw / qh))
    rng = random.Random(20261001)
    CY = (70, 225, 240); DIM = (18, 70, 78); FAINT = (10, 34, 38); AMBER = (235, 165, 60)
    bg = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.45 * (((xx / W - 0.5) * 1.6) ** 2 + ((yy / H - 0.5) * 1.9) ** 2)
    bg[:] = np.array([5, 11, 13], np.float32)
    bg *= vig[..., None].clip(0.4, 1)
    img = Image.fromarray(bg.clip(0, 255).astype(np.uint8))
    glow = Image.new("RGB", (W, H))                        # bright strokes, blurred and added for a soft phosphor bleed
    d, g = ImageDraw.Draw(img), ImageDraw.Draw(glow)

    def both(fn, *a, **k):
        fn(d)(*a, **k); fn(g)(*a, **k)
    for x in range(0, W, 32):
        d.line([(x, 0), (x, H)], fill=FAINT, width=1)
    for y in range(0, H, 32):
        d.line([(0, y), (W, y)], fill=FAINT, width=1)
    m = 22
    # corner brackets and panel separators
    for (x0, y0, sx, sy) in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x0, y0), (x0 + 40 * sx, y0)], fill=DIM, width=3); d.line([(x0, y0), (x0, y0 + 40 * sy)], fill=DIM, width=3)
    s1, s2 = int(W * 0.30), int(W * 0.66)
    for sx in (s1, s2):
        d.line([(sx, m + 30), (sx, H - m - 30)], fill=DIM, width=2)
    # left: part schematic (flanged bracket) with a deposition progress ring
    cx, cy, R = s1 // 2 + 4, H // 2 + 6, int(min(s1, H) * 0.34)
    d.ellipse([cx - R - 22, cy - R - 22, cx + R + 22, cy + R + 22], outline=DIM, width=4)
    both(lambda dr: dr.arc, [cx - R - 22, cy - R - 22, cx + R + 22, cy + R + 22], -90, -90 + 252, fill=CY, width=6)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=CY, width=3)
    d.ellipse([cx - R * 0.42, cy - R * 0.42, cx + R * 0.42, cy + R * 0.42], outline=CY, width=3)
    for k in range(6):
        a = k * math.pi / 3 + math.pi / 6
        bx, by, br = cx + math.cos(a) * R * 0.72, cy + math.sin(a) * R * 0.72, R * 0.09
        d.ellipse([bx - br, by - br, bx + br, by + br], outline=CY, width=2)
    d.line([(cx - R - 40, cy), (cx + R + 40, cy)], fill=DIM, width=1); d.line([(cx, cy - R - 40), (cx, cy + R + 40)], fill=DIM, width=1)
    # tool path: a hatched sector being deposited
    for k in range(14):
        a0 = math.radians(-90 + k * 18)
        r0, r1 = R * 0.46, R * 0.94
        if k < 10:
            both(lambda dr: dr.line, [(cx + math.cos(a0) * r0, cy + math.sin(a0) * r0), (cx + math.cos(a0) * r1, cy + math.sin(a0) * r1)], fill=CY if k == 9 else DIM, width=2)
    # middle: layer grid and segmented bar
    gx0, gx1 = s1 + 46, s2 - 46
    gy0, gy1 = m + 54, int(H * 0.66)
    cols, rows = 12, 6
    cw, ch = (gx1 - gx0) / cols, (gy1 - gy0) / rows
    lit = 47
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            x0, y0 = gx0 + c * cw + 4, gy0 + r * ch + 4
            box = [x0, y0, x0 + cw - 8, y0 + ch - 8]
            if i < lit:
                d.rectangle(box, fill=(14, 62 + rng.randint(0, 18), 70 + rng.randint(0, 18)))
            elif i == lit:
                both(lambda dr: dr.rectangle, box, fill=CY)
            else:
                d.rectangle(box, outline=FAINT, width=2)
    by0 = int(H * 0.76)
    segs = 24
    sw = (gx1 - gx0) / segs
    for k in range(segs):
        box = [gx0 + k * sw + 3, by0, gx0 + (k + 1) * sw - 3, by0 + 34]
        if k < 17:
            both(lambda dr: dr.rectangle, box, fill=CY if k == 16 else (40, 160, 175))
        else:
            d.rectangle(box, outline=DIM, width=2)
    d.rectangle([gx0, by0 + 52, gx0 + (gx1 - gx0) * 0.38, by0 + 60], fill=DIM)
    # right: flux trace with a dim fill, and five level meters (one amber)
    tx0, tx1 = s2 + 40, W - m - 36
    ty0, ty1 = m + 60, int(H * 0.56)
    for k in range(1, 4):
        y = ty0 + (ty1 - ty0) * k / 4
        d.line([(tx0, y), (tx1, y)], fill=FAINT, width=1)
    pts = []
    n = 80
    v = 0.55
    for k in range(n + 1):
        v += rng.uniform(-0.07, 0.07); v = min(0.92, max(0.18, v * 0.92 + 0.55 * 0.08))
        pts.append((tx0 + (tx1 - tx0) * k / n, ty1 - (ty1 - ty0) * v))
    d.polygon(pts + [(tx1, ty1), (tx0, ty1)], fill=(9, 30, 34))
    both(lambda dr: dr.line, pts, fill=CY, width=3)
    mx0 = tx0
    mw = (tx1 - tx0) / 5
    levels = [0.72, 0.55, 0.81, 0.38, 0.64]
    for k, lv in enumerate(levels):
        x0 = mx0 + k * mw + 10
        y0, y1 = int(H * 0.64), H - m - 40
        d.rectangle([x0, y0, x0 + mw - 20, y1], outline=DIM, width=2)
        top = y1 - (y1 - y0) * lv
        colr = AMBER if k == 3 else (40, 170, 185)
        both(lambda dr: dr.rectangle, [x0 + 5, top, x0 + mw - 25, y1 - 5], fill=colr)
    # status marks, top right
    for k, colr in enumerate((CY, CY, AMBER)):
        x = W - m - 30 - k * 34
        both(lambda dr: dr.ellipse, [x - 9, m + 22, x + 9, m + 40], fill=colr)
    out = np.asarray(img).astype(np.float32) + np.asarray(glow.filter(ImageFilter.GaussianBlur(9))).astype(np.float32) * 0.55
    out *= (0.94 + 0.06 * ((np.arange(H) % 4) < 2))[:, None, None]       # faint scanlines
    final = Image.fromarray(out.clip(0, 255).astype(np.uint8)).resize((2048, 512), Image.LANCZOS)
    MATS.mkdir(parents=True, exist_ok=True)
    final.save(MATS / "SS_FabScreen_Display.png")
    wb["screen"]["texture"] = "Assets/AthenHill/Art/SalvageShop/Materials/SS_FabScreen_Display.png"
    print("screen", W, H, "->", final.size, flush=True)

(PROPS / "salvage-shop-props.json").write_text(json.dumps(man, indent=1))
