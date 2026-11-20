"""Hero base: final texture set (Blender 5.2 Python, numpy only; no rendering).
Usage: blender.sh finish_textures.py
In:  face/out/diffuse_v1.png (face repaint + tone match), face/out/mask_v1.png (where the repaint went),
     rodin/tex/texture_normal.png, rodin/tex/texture_metallic-texture_roughness.png, rodin/tex/texture_diffuse.png
Out: build/tex/hero_base.png (4096), hero_normal.png (4096), hero_rough.png (2048, glTF order: G roughness, B metallic)
  * colour: the small text-like tag on the shirt hem is painted out with the fabric beside it;
  * normal: flattened 75 % where the face was repainted (Rodin's map has a groove across the forehead and the painted
    detail now carries the face) and 35 % on the rest of the skin (the map reads as goose bumps on arms and hands);
  * roughness: skin a little smoother (x 0.82), metallic forced to 0 on skin."""
import bpy, json
import numpy as np
from pathlib import Path
H = Path('/home/teknetik/code/ao2/art/hero_base_20261120'); OUT = H / 'build/tex'; OUT.mkdir(parents=True, exist_ok=True)


def load(p, non_color=False):
    im = bpy.data.images.load(str(p)); im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(im.size[1], im.size[0], 4)[..., :3].copy(); bpy.data.images.remove(im); return a      # bottom row first


def save(a, p, non_color=False):
    h, w = a.shape[:2]; im = bpy.data.images.new('o', w, h, alpha=False); im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    b = np.ones((h, w, 4), np.float32); b[..., :3] = a; im.pixels.foreach_set(np.clip(b, 0, 1).ravel())
    im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)


def blur(a, r):
    k = 2 * r + 1; c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0))), axis=0); a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r))), axis=1); return (c[:, k:] - c[:, :-k]) / k


def hsv(c):
    mx = c.max(-1); mn = c.min(-1); df = mx - mn + 1e-6; r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / df) % 6, np.where(mx == g, (b - r) / df + 2, (r - g) / df + 4)) / 6.0
    return h, df / (mx + 1e-6), mx


rec = {}
base = load(H / 'face/out/diffuse_v1.png'); R = base.shape[0]
# ---- hem tag (top-left origin x 690..815, y 1235..1295): replace with the fabric 70 px below, feathered
x0, x1, y0, y1, dy = 690, 815, 1235, 1295, 70
top = base[::-1]                                             # view with the top row first (writes through)
patch = top[y0 + dy:y1 + dy, x0:x1].copy()
yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
f = np.minimum(np.minimum(xx, x1 - x0 - 1 - xx), np.minimum(yy, y1 - y0 - 1 - yy)) / 10.0; f = np.clip(f, 0, 1)[..., None]
top[y0:y1, x0:x1] = top[y0:y1, x0:x1] * (1 - f) + patch * f
save(base, OUT / 'hero_base.png'); rec['hem_tag'] = [x0, y0, x1, y1]

orig = load(H / 'rodin/tex/texture_diffuse.png')
hh, ss, vv = hsv(orig)
covered = (orig.max(-1) > 0.02).astype(np.float32)      # chart texels (the Rodin map's padding is filled, so this is a soft guard only)
skin = blur(((hh < .085) & (ss > .12) & (ss < .6) & (vv > .55)).astype(np.float32), 3)
face = blur(load(H / 'face/out/mask_v1.png', True)[..., 0], 3)
rec['skin_share'] = float(skin.mean()); rec['face_share'] = float(face.mean())

nrm = load(H / 'rodin/tex/texture_normal.png', True)
k = np.clip(np.maximum(.75 * face, .35 * skin), 0, 1)[..., None]
flat = np.array([.5, .5, 1.0], np.float32)
n = nrm * (1 - k) + flat * k
v = n * 2 - 1; v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6); n = v * .5 + .5
save(n, OUT / 'hero_normal.png', True)

mr = load(H / 'rodin/tex/texture_metallic-texture_roughness.png', True)
s3 = skin[..., None]
mr[..., 1] = mr[..., 1] * (1 - skin * .18)
mr[..., 2] = mr[..., 2] * (1 - skin)
rec['rough_mean'] = float(mr[..., 1].mean()); rec['metal_mean'] = float(mr[..., 2].mean()); rec['metal_max'] = float(mr[..., 2].max())
half = mr.reshape(R // 2, 2, R // 2, 2, 3).mean(axis=(1, 3))
save(half, OUT / 'hero_rough.png', True)
(OUT / 'textures.json').write_text(json.dumps(rec, indent=1)); print('TEXTURES OK', rec)
