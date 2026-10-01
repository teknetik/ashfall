"""Ward rooftops: the two small tiling maps the roof kit needs (1 Oct 2026). Original, procedural.
  RT_DewNet_Base.png    512 px RGBA, one tile = 0.25 m of knitted shade/fog net (Raschel-style, ~28 % cover),
                        weathered dark green with dust in the knots. Alpha-clipped, double-sided in Unity.
  RT_SolarCell_Base.png 512 px RGB, one tile = 6 x 6 monocrystalline cells (156 mm) with busbars, the white backsheet
                        showing at the cell corners and between cells, a faint dust film towards the lower edge.
Run: uv run --with pillow --with numpy python make_textures.py
Out: unity/AthenHill/Assets/AthenHill/Art/Rooftops/Textures/"""
import numpy as np
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "unity/AthenHill/Assets/AthenHill/Art/Rooftops/Textures"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)
N = 512

# ---------------------------------------------------------------- dew / fog net (diamond knit, 16 cells per tile)
y, x = np.mgrid[0:N, 0:N] / N
cells = 12
u = (x + y) * cells
v = (x - y) * cells
du = np.abs(((u + 0.5) % 1.0) - 0.5)          # distance to the nearest strand (0 on the strand)
dv = np.abs(((v + 0.5) % 1.0) - 0.5)
w = 0.06                                       # strand half width in cell units (~28 % cover with the knots)
strand = np.clip((w - np.minimum(du, dv)) / 0.03 + 0.5, 0, 1)
knot = np.clip((0.11 - np.hypot(du, dv)) / 0.04 + 0.5, 0, 1)
alpha = np.clip(np.maximum(strand, knot) * 1.0, 0, 1)
base = np.array([0.34, 0.37, 0.32])            # weathered dark-green knitted HDPE
noise = rng.normal(0, 0.04, (N, N))
dust = np.clip(0.06 + 0.1 * knot + noise, 0, 0.3)
rgb = base[None, None, :] * (1 - dust[..., None]) + np.array([0.66, 0.56, 0.42])[None, None, :] * dust[..., None]
img = np.dstack([rgb, alpha]) * 255
Image.fromarray(img.astype(np.uint8), "RGBA").save(OUT / "RT_DewNet_Base.png")

# ---------------------------------------------------------------- PV cells (6 x 6 per tile)
c = 6
cy, cx = (y * c) % 1.0, (x * c) % 1.0
gap = 0.013                                     # backsheet between cells (cell units)
inside = (cx > gap) & (cx < 1 - gap) & (cy > gap) & (cy < 1 - gap)
corner = (np.minimum(cx, 1 - cx) + np.minimum(cy, 1 - cy)) < 0.12           # pseudo-square corners
cell = inside & ~corner
col = np.zeros((N, N, 3))
col[...] = np.array([0.86, 0.86, 0.84])                                     # backsheet
cell_col = np.array([0.035, 0.045, 0.085]) + rng.normal(0, 0.006, (N, N, 1))
col[cell] = cell_col[cell]
# fingers (fine horizontal) and three busbars (vertical)
fing = (np.abs(((cy * 40) % 1.0) - 0.5) > 0.46) & cell
col[fing] = col[fing] * 0.6 + 0.4 * np.array([0.35, 0.36, 0.4])
for bx in (0.25, 0.5, 0.75):
    bus = (np.abs(cx - bx) < 0.008) & cell
    col[bus] = np.array([0.62, 0.62, 0.64])
# dust film, stronger at the bottom of each tile (panels shed it downhill), plus speckle
film = (0.05 + 0.08 * y)[..., None] * (0.6 + 0.4 * rng.random((N, N, 1)))
col = col * (1 - film) + np.array([0.62, 0.52, 0.4]) * film
Image.fromarray(np.clip(col * 255, 0, 255).astype(np.uint8), "RGB").save(OUT / "RT_SolarCell_Base.png")
print("wrote", OUT)
