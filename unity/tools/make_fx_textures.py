"""Procedural combat FX textures for Ward (deterministic, CC0 by construction).

  uv run --offline --with numpy --with pillow python unity/tools/make_fx_textures.py OUT_DIR

Writes:
  FX_SmokeFlipbook.png  2048x2048, 8x8 frames of a billowing puff (RGB = lit density, A = density), evolving over time
  FX_FireFlipbook.png   1024x1024, 4x4 frames of a flickering flame tongue (greyscale heat in RGB, A = mask)
  FX_Spark.png          128x32 soft hot streak (additive)
  FX_Glow.png           128x128 soft radial glow (additive)
  FX_Scorch.png         512x512 radial scorch/soot decal (A = soot)
The smoke puff is self-shadowed toward +Y/-X so it reads as a lit volume under a high sun.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

RNG = np.random.default_rng(1729)


def fbm3(x, y, z, octaves=5, seed=0):
    """Value-noise FBM on a lattice with smooth interpolation (vectorised)."""
    rng = np.random.default_rng(seed)
    perm = rng.permutation(256)
    perm = np.concatenate([perm, perm])
    vals = rng.random(256)

    def noise(px, py, pz):
        xi, yi, zi = np.floor(px).astype(int) & 255, np.floor(py).astype(int) & 255, np.floor(pz).astype(int) & 255
        xf, yf, zf = px - np.floor(px), py - np.floor(py), pz - np.floor(pz)
        u, v, w = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf), zf * zf * (3 - 2 * zf)

        def h(a, b, c):
            return vals[perm[perm[perm[a] + b] + c]]
        x1, y1, z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
        c000, c100, c010, c110 = h(xi, yi, zi), h(x1, yi, zi), h(xi, y1, zi), h(x1, y1, zi)
        c001, c101, c011, c111 = h(xi, yi, z1), h(x1, yi, z1), h(xi, y1, z1), h(x1, y1, z1)
        x00 = c000 + u * (c100 - c000); x10 = c010 + u * (c110 - c010)
        x01 = c001 + u * (c101 - c001); x11 = c011 + u * (c111 - c011)
        y0 = x00 + v * (x10 - x00); y1_ = x01 + v * (x11 - x01)
        return y0 + w * (y1_ - y0)

    total, amp, freq, norm = 0, 1.0, 1.0, 0
    for _ in range(octaves):
        total = total + amp * noise(x * freq, y * freq, z * freq)
        norm += amp; amp *= .5; freq *= 2.03
    return total / norm


def smoke(size=256, frames=64):
    sheet = np.zeros((size * 8, size * 8, 4), np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size * 2 - 1
    for f in range(frames):
        t = f / (frames - 1)
        r = np.sqrt(xx ** 2 + (yy * 1.05) ** 2)
        grow = .74 + .2 * t
        lobes = fbm3(xx * 1.25 + 4, yy * 1.25 - 2, t * .9, 3, seed=7)  # large billows
        n = fbm3(xx * 2.6 + 7, yy * 2.6 + 3, t * 1.6, 6, seed=11)
        n2 = fbm3(xx * 6.1 + 1, yy * 6.1 - 4, t * 2.4 + 9, 4, seed=23)
        edge = grow - r + (lobes - .5) * .9 + (n - .5) * .55 + (n2 - .5) * .2
        density = np.clip(edge * 2.6, 0, 1) ** 1.1
        density *= (1 - t * .5)  # thins as it expands
        density *= np.clip((1 - r) / .28, 0, 1) ** 1.5  # radial window: zero before the frame edge, so no card borders
        # self-shadow toward a high light (+Y is up in the image's top rows): accumulate density below-right
        occl = sum(np.roll(np.roll(density, k * 6, axis=0), -k * 3, axis=1) for k in range(1, 6)) / 5
        light = np.clip(1 - occl * .95, .12, 1)
        lit = np.clip(.3 + .7 * light * (.8 + .4 * n2) - .15 * (yy > 0) * yy, 0, 1)
        tile = np.dstack([lit, lit * .98, lit * .95, density])
        row, col = divmod(f, 8)
        sheet[row * size:(row + 1) * size, col * size:(col + 1) * size] = tile
    return Image.fromarray((sheet * 255).astype(np.uint8), 'RGBA')


def fire(size=256, frames=16):
    sheet = np.zeros((size * 4, size * 4, 4), np.float32)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    for f in range(frames):
        t = f / frames
        u = (xx - .5) * 2
        v = 1 - yy  # 0 at the bottom
        n = fbm3(u * 3 + 2, v * 4 - t * 6, t * 2, 5, seed=5)
        width = .75 * (1 - v) ** .55 + .08
        shape = np.clip(1 - np.abs(u + (n - .5) * .5 * v) / width, 0, 1)
        heat = np.clip(shape * (1.2 - v * 1.1) + (n - .5) * .6 * v, 0, 1) ** 1.6
        heat *= np.clip(v * 8, 0, 1)
        tile = np.dstack([heat, heat, heat, np.clip(heat * 1.4, 0, 1)])
        row, col = divmod(f, 4)
        sheet[row * size:(row + 1) * size, col * size:(col + 1) * size] = tile
    return Image.fromarray((sheet * 255).astype(np.uint8), 'RGBA')


def spark():
    yy, xx = np.mgrid[0:32, 0:128].astype(np.float32)
    u, v = xx / 127, (yy - 15.5) / 16
    core = np.exp(-(v ** 2) * 18) * np.clip(np.sin(np.pi * u), 0, 1) ** .6 * (0.35 + .65 * u)
    img = np.dstack([core, core * .85, core * .6, core])
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), 'RGBA')


def glow():
    yy, xx = np.mgrid[0:128, 0:128].astype(np.float32) / 127 * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    g = np.clip(1 - r, 0, 1) ** 2.2
    return Image.fromarray((np.dstack([g, g, g, g]) * 255).astype(np.uint8), 'RGBA')


def scorch():
    yy, xx = np.mgrid[0:512, 0:512].astype(np.float32) / 511 * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    n = fbm3(xx * 3, yy * 3, 0.5, 6, seed=31)
    a = np.clip((1 - r * 1.15) + (n - .5) * .7, 0, 1) ** 1.4
    rgb = np.clip(.08 + .06 * n, 0, 1)
    return Image.fromarray((np.dstack([rgb, rgb * .95, rgb * .9, a]) * 255).astype(np.uint8), 'RGBA')


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    smoke().save(out / 'FX_SmokeFlipbook.png')
    fire().save(out / 'FX_FireFlipbook.png')
    spark().save(out / 'FX_Spark.png')
    glow().save(out / 'FX_Glow.png')
    scorch().save(out / 'FX_Scorch.png')
    print('wrote', sorted(p.name for p in out.glob('FX_*.png')))


if __name__ == '__main__':
    main()
