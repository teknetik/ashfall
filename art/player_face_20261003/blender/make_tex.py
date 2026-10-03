"""player_face_20261003: runtime skin textures from the chosen Meshy retexture (skin_mv_v1) + the hair/beard shell texture.
Outputs art/player_face_20261003/tex/:
  skin_base.png 4k   Meshy base colour, slightly warmer/saturated toward the concept (no relighting)
  skin_normal.png 4k Meshy tangent-space normal (OpenGL +Y, as glTF wants), unchanged
  skin_rough.png 2k  Meshy roughness x0.92 (it averages 0.69; the face reads chalky in sun otherwise)
  hair_mask.png 2k   where the painted texture is scalp hair / beard / brows (dark, clumped), eyes and lips excluded
  hair_shell.png 2k  RGBA for the alpha-clipped shell layers: RGB = painted hair colour, A = strand pattern x mask
Usage: blender.sh make_tex.py [-- SRC_DIR]"""
import sys, bpy, numpy as np
from pathlib import Path
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = Path(args[0]) if args else Path('/home/teknetik/code/ao2/meshy/player-face-20261003/skin_mv_v1')
PF = Path('/home/teknetik/code/ao2/art/player_face_20261003'); T = PF / 'tex'; T.mkdir(exist_ok=True)

def load(p, non_color=False):
    im = bpy.data.images.load(str(p));
    if non_color: im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; a = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)            # Blender pixel order: row 0 = bottom (UV v = 0)

def save(a, p, non_color=False):
    h, w = a.shape[:2]
    im = bpy.data.images.new(p.stem, w, h, alpha=True, float_buffer=False)
    if non_color: im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel()); im.filepath_raw = str(p); im.file_format = 'PNG'
    im.save(); bpy.data.images.remove(im)

def down2(a): return (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2]) / 4

def blur(m, r):
    """box blur radius r (separable, repeated twice ~ gaussian)"""
    for _ in range(2):
        for ax in (0, 1):
            c = np.cumsum(np.pad(m, [(r + 1, r) if i == ax else (0, 0) for i in range(2)], mode='edge'), axis=ax)
            m = (np.take(c, range(2 * r + 1, c.shape[ax]), axis=ax) - np.take(c, range(0, c.shape[ax] - 2 * r - 1), axis=ax)) / (2 * r + 1)
    return m

base = load(SRC / 'tex0_base_color.png')                      # byte image: pixels are the stored sRGB values
rgb = base[..., :3]
# gentle grade toward the concept: +10 % saturation, a touch warmer
lum = (rgb * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
rgb = np.clip(lum + (rgb - lum) * 1.10, 0, 1) * [1.035, 1.0, 0.965]
out = base.copy(); out[..., :3] = np.clip(rgb, 0, 1); out[..., 3] = 1
save(out, T / 'skin_base.png')
nrm = load(SRC / 'tex0_normal.png', True); nrm[..., 3] = 1; save(nrm, T / 'skin_normal.png', True)
rough = load(SRC / 'tex0_roughness.png', True); r = np.clip(rough[..., 1] * 0.92, 0, 1)
rr = np.stack([r, r, r, np.ones_like(r)], -1); save(rr, T / 'skin_rough.png', True)

# ---- hair mask (2k). UV regions from inspect_skin.json: the head island spans u 0.64-0.99, v 0.13-0.82; the scalp island
# u 0.76-0.92 v 0.0-0.12. Eyes were packed into u 0.24-0.44 v 0.40-0.50 for Meshy (not skin). Lips: dark-red, excluded by hue.
b2 = down2(out[..., :3]); H, W = b2.shape[:2]
srgb = b2
L = (srgb * [0.2126, 0.7152, 0.0722]).sum(-1)
red = srgb[..., 0] - srgb[..., 2]
skinL = np.median(L[(L > 0.35) & (L < 0.8)])
dark = np.clip((skinL * 0.72 - L) / (skinL * 0.25), 0, 1) * np.clip(1 - (red - 0.16) / 0.08, 0, 1)
v, u = np.mgrid[0:H, 0:W]; u = (u + .5) / W; v = (v + .5) / H
head = ((u > 0.63) & (u < 0.995) & (v > 0.12) & (v < 0.83)) | ((u > 0.75) & (u < 0.93) & (v < 0.125))
dark *= head
# clumped regions only: remove thin dark lines (eyelid creases, mouth line, brow-only specks stay if dense)
m = blur(dark, 6); m = np.clip((m - 0.35) / 0.3, 0, 1); m = blur(m, 3)
save(np.stack([m, m, m, np.ones_like(m)], -1), T / 'hair_mask.png', True)
# ---- shell texture: the strands follow the painted hair. Alpha = how much darker a texel is than its neighbourhood (the
# painted comb strokes and beard curls) plus fine noise, so stacked shells extrude the painted strands, not a random screen.
rng = np.random.default_rng(7)
n1 = rng.random((H, W)).astype(np.float32)
local = blur(L, 4)
contrast = np.clip((local - L) / 0.06 + 0.5, 0, 1)
strand = np.clip(0.55 * contrast + 0.45 * n1, 0, 1)
alpha = np.clip(strand * (0.45 + 0.6 * m), 0, 1) * (m > 0.05)
alpha = np.clip(blur(alpha, 1) * 1.15, 0, 1) * (m > 0.05)            # strands 2-3 texels wide: clumps, not single-texel speckle
col = np.clip(b2 * (0.78 + 0.25 * n1[..., None]), 0, 1)             # per-strand brightness jitter, never lighter than paint
save(np.concatenate([col, alpha[..., None]], -1), T / 'hair_shell.png')
# ---- eyes: MPFB brown_eye.png has a red iris (reads as bloodshot red in sun); keep its fibre detail (luminance) and
# re-tint the iris a dark neutral brown, sclera a touch less white/pink
EYE = Path('/home/teknetik/.config/blender/5.2/extensions/.user/user_default/mpfb/data/eyes/materials/brown_eye.png')
eye = load(EYE); e = eye[..., :3]
el = (e * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
sat = e.max(-1, keepdims=True) - e.min(-1, keepdims=True)
iris = np.clip((sat - 0.18) / 0.15, 0, 1)
brown = np.clip(el * 1.2 * np.array([1.45, 0.95, 0.6]), 0, 1)
sclera = np.clip(el * np.array([1.0, 0.98, 0.94]) * 0.92, 0, 1)
e2 = brown * iris + sclera * (1 - iris)
eye[..., :3] = e2; eye[..., 3] = 1
save(eye, T / 'eye_brown.png')
print('TEX done skinL', float(skinL), 'mask cover', float((m > 0.5).mean()))
