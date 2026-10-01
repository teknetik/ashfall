"""Mission terminal emission map (1 Oct 2026), derived from the Meshy albedo (pattern: art/hill_20260930/prepare_prop_maps.py).
Run: uv run --with pillow --with numpy python prepare_terminal_emission.py
The albedo itself is unchanged. Emission is the albedo where the terminal carries lit surfaces:
  * the MISSIONS display (dark teal glass with cyan graphics): the whole glass area glows faintly, the graphics brightly;
  * the white badge sign above the kiosk (backlit panel with the dark Free Column diamond);
  * the small cyan status button on the head.
Regions are found from the albedo itself inside generous search windows (2k atlas pixels), then feathered.
Writes Assets/AthenHill/Art/NightLife/Terminal/MissionTerminal_Emission.png (2048², sRGB) and a review preview."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = ROOT / "unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/MissionTerminal/Albedo.jpg"
OUT = ROOT / "unity/AthenHill/Assets/AthenHill/Art/NightLife/Terminal"
OUT.mkdir(parents=True, exist_ok=True)

alb = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float32) / 255
H, W, _ = alb.shape
r, g, b = alb[..., 0], alb[..., 1], alb[..., 2]
em = np.zeros_like(alb)
report = {}


def box_from(mask, win):
    """Bounding box of mask pixels inside the window (x0, y0, x1, y1), at 2k scale."""
    x0, y0, x1, y1 = win
    sub = mask[y0:y1, x0:x1]
    ys, xs = np.nonzero(sub)
    if len(xs) < 50:
        raise SystemExit(f"region not found in {win}")
    # robust extent (ignore stray pixels)
    return (x0 + int(np.percentile(xs, 0.5)), y0 + int(np.percentile(ys, 0.5)), x0 + int(np.percentile(xs, 99.5)) + 1, y0 + int(np.percentile(ys, 99.5)) + 1)


def feather(x0, y0, x1, y1, inset=4, soft=5):
    m = np.zeros((H, W), np.float32)
    m[y0 + inset:y1 - inset, x0 + inset:x1 - inset] = 1
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(soft))).astype(np.float32) / 255


# 1. the display: dark teal glass (blue-green over red, not grey stone) in the window around (790-1120, 164-490)
teal = ((g + b) / 2 - r > 0.03) & (np.maximum(g, b) < 0.95)
scr = box_from(teal, (760, 130, 1150, 520))
m_scr = feather(*scr, inset=6, soft=4)
# glass glows faintly everywhere (backlight), graphics strongly (they are already bright in the albedo)
cyan = np.clip(((g + b) / 2 - r - 0.10) / 0.25, 0, 1) * np.clip((np.maximum(g, b) - 0.30) / 0.35, 0, 1)
screen = alb * (0.55 + 1.45 * cyan)[..., None]
em += screen * m_scr[..., None]
report["screen_box"] = scr

# 2. the badge: near-white backlit panel in the window around (200-330, 300-500)
white = (np.minimum(np.minimum(r, g), b) > 0.62)
bdg = box_from(white, (180, 280, 340, 510))
m_bdg = feather(*bdg, inset=3, soft=3)
em += alb * 0.85 * m_bdg[..., None]
report["badge_box"] = bdg

# 3. the cyan status button on the head (window around (335-390, 136-196))
btn_mask = np.clip(((g + b) / 2 - r - 0.15) / 0.2, 0, 1) * np.clip((b - 0.45) / 0.2, 0, 1)
win = np.zeros((H, W), np.float32); win[120:210, 320:405] = 1
em += alb * (btn_mask * win)[..., None] * 1.2
report["button_pixels"] = int(((btn_mask * win) > 0.2).sum())

em = np.clip(em, 0, 1)
img = Image.fromarray((em * 255 + 0.5).astype(np.uint8), "RGB")
img.save(OUT / "MissionTerminal_Emission.png")
report["emissive_fraction"] = float((em.max(-1) > 0.03).mean())
(HERE / "review").mkdir(exist_ok=True)
prev = Image.fromarray((np.clip(alb * 0.25 + em, 0, 1) * 255).astype(np.uint8)).crop((150, 100, 1200, 560))
prev.save(HERE / "review/terminal_emission_preview.png")
(HERE / "terminal-emission.json").write_text(json.dumps(report, indent=1))
print(report)
