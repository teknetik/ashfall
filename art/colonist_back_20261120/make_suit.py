#!/usr/bin/env python3
"""Colonist back pass (20 Nov 2026): new flight-suit base colour + detail normal, synthesised in the suit's own UV
layout from the surface bakes of blender/bake_suit.py (object-space position/normal, AO, body region, pointiness).

Why: the shipped suit_base.png is a Meshy retexture whose atlas is a patchwork of unrelated fragments: high-contrast
knit/moire weaves, white cross-stitches and pink skin-coloured pieces laid at random. Seen from the conversation
camera they read as speckled camouflage. This replaces it with one olive Nomex-like twill that follows the body:
low-frequency fading, sun-bleach on top surfaces, wear on convex edges, elbows and knees, sand ground into the knees,
seat and lower legs, sweat at the collar, the concept's crash repairs (tan/grey canvas patches with stitched hems,
a re-stitched tear on the right upper sleeve), a back yoke and centre-back seam. Light is NOT baked in (AO enters at
30 % as cavity dirt only). The existing 4k normal map (folds from the 595k source) is kept and the seams, patch hems
and stitches are added to it as height detail.

Run: ~/.local/state/ward-programme/heavy.sh uv run --with numpy --with pillow --with scipy python \
         art/colonist_back_20261120/make_suit.py
Writes tex/suit_base.png (4096², sRGB), tex/suit_normal.png (4096², tangent space, +Y up as glTF) and previews."""
import json, numpy as np
from PIL import Image
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None
H = '/home/teknetik/code/ao2/art/colonist_back_20261120/'
B = H + 'bake/'
OLD_N = H + 'inspect/colonist/5_player_normal_4k.png'
NORMAL_SCALE = 0.55          # glTF normalTexture.scale of PlayerJumpsuit (fix round: 0.42 -> 0.55, set by patch_glb --mat)
rng_seed = 1120

P4 = np.load(B + 'position.npy'); R = P4.shape[0]
mask = np.abs(P4[..., :3]).sum(-1) > 1e-6       # baked texels incl. the 24 px margin
P = P4[..., :3][mask].astype(np.float64); del P4
N = np.load(B + 'normal.npy')[..., :3][mask].astype(np.float32)
N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-6
AO = np.load(B + 'ao.npy')[..., 0][mask].astype(np.float32)
REG = np.load(B + 'region.npy')[..., :3][mask].astype(np.float32)
K = np.load(B + 'pointiness.npy')[..., 0]
K = ndimage.gaussian_filter(K, 2.0)[mask].astype(np.float32)
cov = np.load(B + 'coverage.npy')[..., 0] > 0.5
J = {k: np.array(v[:3]) for k, v in json.load(open(B + 'joints.json')).items()}
HEMS = json.load(open(H + 'work/hem_report.json'))['hems']     # edit_suit_mesh.py: hem axes, old and new profiles
n = len(P); print('texels', n)

def ss(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
def hash3(i, j, k, seed):
    h = np.sin(i * 127.1 + j * 311.7 + k * 74.7 + seed * 19.19) * 43758.5453
    return h - np.floor(h)
def vnoise(p, f, seed=0):
    q = p * f; i = np.floor(q); t = q - i; t = t * t * (3 - 2 * t)
    i0, j0, k0 = i[:, 0], i[:, 1], i[:, 2]; out = 0
    for dx in (0, 1):
        wx = t[:, 0] if dx else 1 - t[:, 0]
        for dy in (0, 1):
            wy = t[:, 1] if dy else 1 - t[:, 1]
            for dz in (0, 1):
                wz = t[:, 2] if dz else 1 - t[:, 2]
                out = out + wx * wy * wz * hash3(i0 + dx, j0 + dy, k0 + dz, seed)
    return (out * 2 - 1).astype(np.float32)
def fbm(p, f, oct=4, seed=0):
    s = 0; a = 1; tot = 0
    for o in range(oct):
        s = s + a * vnoise(p, f * 2 ** o, seed + o * 7); tot += a; a *= 0.5
    return s / tot

def srgb(c): return np.array(c, np.float32) / 255.0
OLIVE = srgb((86, 79, 56)); OLIVE_B = srgb((93, 82, 58)); FADED = srgb((124, 116, 92))   # concept olive-brown
DUST = srgb((170, 148, 113)); GRIME = srgb((52, 46, 34)); THREAD = srgb((118, 110, 82))

def texels(P, N, AO, REG, K):
    n = len(P); x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ARMS, LEGS, TORSO = REG[:, 0], REG[:, 1], REG[:, 2]
    # ---- base cloth -------------------------------------------------------------------------------------------------
    low = fbm(P, 3.0, 4, 1)                       # panel-scale tone drift (~30 cm)
    mid = fbm(P, 14.0, 3, 2)                      # handling marks (~7 cm)
    col = OLIVE[None] * (1 + 0.06 * low[:, None] + 0.025 * mid[:, None])
    col = col + (OLIVE_B - OLIVE)[None] * ss(-0.2, 0.6, fbm(P, 2.0, 3, 3))[:, None]
    # plain weave, 1.6 mm repeat (warp x weft), triplanar: +-1.5 % in colour and a 15 micron relief in the normal map
    # (the v1 2.2 mm diagonal at 60 microns moired in the specular); fibre noise at ~1.5 mm
    ax = np.argmax(np.abs(N), axis=1)
    u = np.where(ax == 0, y, x); v = np.where(ax == 2, y, z)
    weave = (np.sin(2 * np.pi * u / 0.0016) * np.sin(2 * np.pi * v / 0.0016)).astype(np.float32)
    fibre = vnoise(P, 650.0, 5)
    col *= (1 + 0.015 * weave + 0.03 * fibre)[:, None]
    height = (0.000015 * weave).astype(np.float32)

    # ---- sun bleach on upward and upper-back surfaces ---------------------------------------------------------------
    shoulders = np.clip(ss(0.16, 0.05, np.linalg.norm(P - (J['LeftArm'] + [0, 0, 0.05])[None], axis=1)) +
                        ss(0.16, 0.05, np.linalg.norm(P - (J['RightArm'] + [0, 0, 0.05])[None], axis=1)), 0, 1)
    bleach = np.clip(N[:, 2], 0, 1) * 0.55 + ss(1.15, 1.45, z) * np.clip(N[:, 1] + 0.3, 0, 1) * 0.35 + 0.5 * shoulders * np.clip(N[:, 2] + 0.5, 0, 1)
    bleach = np.clip(bleach * (0.75 + 0.25 * fbm(P, 6.0, 3, 9)), 0, 1)
    col = col + (FADED - col) * (0.30 * bleach)[:, None]

    # ---- cavity dirt from AO (not lighting: 30 %) -----------------------------------------------------------------------
    col *= (1 - 0.30 * (1 - AO))[:, None]

    # ---- edge wear on convex creases (pointiness) ---------------------------------------------------------------------
    edge = ss(0.515, 0.56, K) * ss(-0.1, 0.5, fbm(P, 40.0, 3, 11))
    col = col + (FADED * 1.12 - col) * (0.45 * edge)[:, None]

    def near(j, r): return ss(r, r * 0.35, np.linalg.norm(P - J[j][None], axis=1))
    breakup = ss(-0.35, 0.45, fbm(P, 22.0, 4, 13))
    # elbows (back of the elbow faces +Y in the rest pose) and knees (front, -Y)
    elbow = (near('LeftForeArm', 0.08) + near('RightForeArm', 0.08)) * ARMS * np.clip(N[:, 1] + 0.4, 0, 1)
    knee = (near('LeftLeg', 0.10) + near('RightLeg', 0.10)) * LEGS * np.clip(-N[:, 1] + 0.3, 0, 1)
    seat = ss(0.0, 0.07, y) * ss(0.72, 0.80, z) * ss(1.02, 0.94, z) * np.clip(N[:, 1], 0, 1)
    shin = LEGS * ss(0.58, 0.12, z)
    dust = np.clip(0.55 * knee + 0.45 * seat + 0.55 * shin + 0.20 * elbow, 0, 1) * breakup
    col = col + (FADED * 1.08 - col) * (0.35 * np.clip(elbow + knee, 0, 1) * breakup)[:, None]
    col = col + (DUST - col) * (0.55 * dust)[:, None]
    # sweat and grime at the collar
    collar = ss(0.15, 0.06, np.linalg.norm(P - J['neck'][None], axis=1)) * ss(1.38, 1.47, z)
    col = col + (GRIME - col) * (0.35 * collar * (0.6 + 0.4 * ss(-0.3, 0.4, fbm(P, 30.0, 3, 17))))[:, None]

    # ---- seams: back yoke (shallow V) and centre back ------------------------------------------------------------------
    back = np.clip(N[:, 1] * 2.0, 0, 1) * (TORSO + 0.5 * ARMS).clip(0, 1) * (y > -0.02)
    yoke_z = 1.355 - 0.045 * np.clip(1 - np.abs(x) / 0.17, 0, 1)
    def seam(dist, along, w=0.0007, row=0.0032, dash=0.0030, amt=1.0):
        groove = ss(w * 1.8, w * 0.4, np.abs(dist))
        st = (ss(0.0011, 0.0004, np.abs(np.abs(dist) - row)) * (np.mod(along, dash * 1.5) < dash))
        return groove * amt, st * amt
    gy, sy = seam(z - yoke_z, x, amt=back * (np.abs(x) < 0.24))
    gc, sc = seam(x, z, amt=back * (z < yoke_z - 0.004) * (z > 0.98))
    # set-in sleeves (the 50 % arm-weight contour, ~8 cm per unit weight), torso side seams, leg outseams, shoulder seams
    ga, sa = seam((ARMS - 0.5) * 0.08, z + x, amt=(z > 1.12).astype(np.float32))
    side = TORSO * (np.abs(N[:, 0]) > 0.45) * (z > 0.98) * (z < 1.36)
    gs, ss_ = seam(y + 0.03, z, amt=side)
    outer = LEGS * (np.sign(x) * N[:, 0] > 0.45) * (z < 0.95)
    gl, sl = seam(y + 0.02, z, amt=outer)
    top = (TORSO + ARMS).clip(0, 1) * (N[:, 2] > 0.45) * (z > 1.36) * (np.abs(x) > 0.07)
    gt, st_ = seam(y + 0.005, x, amt=top)
    groove = np.clip(gy + gc + ga + gs + gl + gt, 0, 1); stitch = np.clip(sy + sc + sa + ss_ + sl + st_, 0, 1)
    # panel breakup: the yoke a shade lighter, the torso side panels a shade darker; wear along every seam
    col *= (1 + 0.035 * back * ss(yoke_z - 0.003, yoke_z + 0.003, z) - 0.035 * side * np.clip(np.abs(N[:, 0]) * 1.5 - 0.6, 0, 1))[:, None]
    nearseam = ss(0.008, 0.002, np.minimum.reduce([np.abs(z - yoke_z) + (1 - back) , np.abs(x) + (1 - back) + (z > yoke_z) ,
                                                    np.abs((ARMS - 0.5) * 0.08) + (z < 1.12), np.abs(y + 0.03) + (1 - side), np.abs(y + 0.02) + (1 - outer)]))
    col = col + (FADED * 1.05 - col) * (0.30 * nearseam * ss(-0.3, 0.5, fbm(P, 60.0, 3, 21)))[:, None]

    # ---- hems after edit_suit_mesh.py: rolled cuffs on the sleeves, a stitched collar band ---------------------------
    G = np.stack([x, z, -y], 1)                       # Blender (Z up) -> glTF mesh space (Y up), as the hem report
    cuff = np.zeros(n, np.float32); cband = np.zeros(n, np.float32); hemedge = np.zeros(n, np.float32)
    cfold = np.zeros(n, np.float32); cstitch = np.zeros(n, np.float32)
    for name, h in HEMS.items():
        o = np.array(h['origin']); a_ = np.array(h['axis']); r1 = np.array(h['ref']); r2 = np.array(h['ref2'])
        d = G - o; t = d @ a_; th = np.arctan2(d @ r2, d @ r1)
        rad = np.linalg.norm(d - np.outer(t, a_), axis=1)
        nb = len(h['target']); k = ((th + np.pi) / (2 * np.pi) * nb).astype(int) % nb
        e = np.array(h['suit']['edge'])[k]; tg = np.array(h['target'])[k]; lo = np.minimum(e, tg) - h['suit']['L']
        tn = np.where(t > lo, np.where(t <= e, lo + (t - lo) * (tg - lo) / np.maximum(e - lo, 1e-6), tg), t)   # as edit_suit_mesh.move
        dist = np.where(rad < h['rmax'], tg - tn, 9.0)
        if name == 'collar':
            cband = np.maximum(cband, ss(0.030, 0.026, dist) * (dist > -0.01))
            cstitch = np.maximum(cstitch, ss(0.0012, 0.0004, np.abs(dist - 0.005)) * (np.mod(th * 0.07, 0.0045) < 0.003))
            cfold = np.maximum(cfold, ss(0.0018, 0.0004, np.abs(dist - 0.028)))
        else:
            cuff = np.maximum(cuff, ss(0.038, 0.033, dist) * (dist > -0.01))
            cfold = np.maximum(cfold, ss(0.0022, 0.0005, np.abs(dist - 0.035)) + ss(0.0016, 0.0004, np.abs(dist - 0.017)) * 0.6)
        hemedge = np.maximum(hemedge, ss(0.004, 0.0, dist) * (dist > -0.01))
    col = col + (FADED * 0.98 - col) * (0.35 * cuff)[:, None]          # the rolled cuff shows the less-faded inside
    col *= (1 - 0.08 * cband - 0.30 * cfold - 0.25 * hemedge)[:, None]
    col = col + (THREAD - col) * (0.5 * cstitch)[:, None]
    groove = np.clip(groove + cfold, 0, 1)
    height += (0.0009 * cuff + 0.0003 * cband - 0.0004 * hemedge - 0.0002 * cstitch).astype(np.float32)

    # ---- crash repairs: canvas patches with folded hems and coarse stitching -----------------------------------------
    TAN = srgb((150, 127, 90)); GREY = srgb((108, 105, 95)); POCKET = OLIVE * 0.93
    PATCHES = [  # centre, outward dir, up, half width, half height, colour, rotation (deg)
        ((0.175, 0.075, 1.405), (0.25, 1.0, 0.55), (0, 0, 1), 0.050, 0.042, TAN, 8),     # left shoulder, back
        ((0.178, -0.07, 1.40), (0.25, -1.0, 0.45), (0, 0, 1), 0.045, 0.040, TAN, -6),    # left shoulder, front
        ((-0.075, 0.105, 0.87), (0, 1, 0), (0, 0, 1), 0.065, 0.060, TAN, -5),            # seat, right
        ((-0.170, -0.105, 0.515), (0, -1, 0), (0, 0, 1), 0.055, 0.068, GREY, 4),          # right knee
        ((0.140, -0.115, 0.72), (0, -1, 0), (0, 0, 1), 0.050, 0.060, TAN, -3),             # left thigh
        ((0.165, 0.075, 0.40), (0, 1, 0), (0, 0, 1), 0.048, 0.055, GREY, 6),               # left calf, back
        ((-0.080, 0.110, 1.22), (0, 1, 0.1), (0, 0, 1), 0.045, 0.038, TAN, 10),            # fix round: upper back, right
        ((0.235, 0.060, 1.27), (0.3, 1, 0), (0, 0, 1), 0.030, 0.038, GREY, -8),            # fix round: left sleeve, back
        ((0.195, -0.010, 0.66), (1, 0, 0), (0, 0, 1), 0.060, 0.075, POCKET, 0),             # cargo pocket, left thigh
        ((-0.195, -0.010, 0.66), (-1, 0, 0), (0, 0, 1), 0.060, 0.075, POCKET, 0),           # cargo pocket, right thigh
        ((0.232, -0.020, 1.27), (1, -0.35, 0), (0, 0, 1), 0.028, 0.052, POCKET, 0),         # pen pocket, left sleeve
    ]
    flap = np.zeros(n, np.float32)
    patch_amt = np.zeros(n, np.float32); patch_col = np.zeros((n, 3), np.float32)
    hem = np.zeros(n, np.float32); pstitch = np.zeros(n, np.float32)
    for i, (c, d, up, hw, hh, pc, rot) in enumerate(PATCHES):
        c = np.array(c); d = np.array(d, float); d /= np.linalg.norm(d)
        vax = np.array(up, float) - d * np.dot(up, d); vax /= np.linalg.norm(vax); uax = np.cross(vax, d)
        a = np.radians(rot); uax, vax = uax * np.cos(a) + vax * np.sin(a), -uax * np.sin(a) + vax * np.cos(a)
        L = P - c[None]; depth = L @ d; pu = L @ uax; pv = L @ vax
        ok = (np.abs(depth) < 0.07) & ((N @ d.astype(np.float32)) > 0.15)
        wob = 0.0025 * vnoise(P, 90.0, 40 + i)
        qx = np.abs(pu) - hw; qy = np.abs(pv) - hh; r = 0.008
        sdf = np.hypot(np.maximum(qx + r, 0), np.maximum(qy + r, 0)) + np.minimum(np.maximum(qx + r, qy + r), 0) - r + wob
        inside = ok & (sdf < 0)
        if not inside.any(): continue
        tone = 1 + 0.07 * fbm(P, 30.0, 3, 50 + i) + 0.02 * np.sin(2 * np.pi * (pu - pv) / 0.0026)
        if pc is POCKET:     # pocket: straight edges, a flap over the top third with its own edge line
            tone = 1 + 0.03 * fbm(P, 30.0, 3, 50 + i)
            flap = np.maximum(flap, (ok & (np.abs(pv - hh * 0.33) < 0.0012) & (np.abs(pu) < hw)).astype(np.float32))
        patch_amt = np.where(inside, 1.0, patch_amt)
        patch_col = np.where(inside[:, None], pc[None] * tone[:, None], patch_col)
        hem = np.maximum(hem, (ok & (sdf < 0) & (sdf > -0.0045)).astype(np.float32))
        along = np.where(np.abs(qx) < np.abs(qy), pv, pu)     # roughly along the nearest edge
        pstitch = np.maximum(pstitch, (ok & (np.abs(sdf + 0.0065) < 0.0010) & (np.mod(along, 0.0060) < 0.0038)).astype(np.float32))
    # re-stitched tear on the right upper sleeve (back): a dark seam with cross-stitches
    a0 = np.array([-0.215, 0.05, 1.335]); a1 = np.array([-0.245, 0.045, 1.215])
    t = np.clip(((P - a0) @ (a1 - a0)) / np.dot(a1 - a0, a1 - a0), 0, 1)
    dtear = np.linalg.norm(P - (a0[None] + t[:, None] * (a1 - a0)[None]), axis=1) + 0.0012 * vnoise(P, 200.0, 77)
    tear_ok = ARMS * (N[:, 1] > 0.1)
    tear = ss(0.0014, 0.0005, dtear) * tear_ok
    seglen = np.linalg.norm(a1 - a0); along_t = t * seglen
    cross = (dtear < 0.0045) * (np.mod(along_t, 0.007) < 0.0012) * tear_ok
    patch_col = np.where(patch_amt[:, None] > 0, patch_col, col)
    col = col * (1 - patch_amt[:, None]) + patch_col * patch_amt[:, None]
    col *= (1 - 0.22 * hem)[:, None]
    col *= (1 - 0.35 * groove)[:, None]
    col = col + (THREAD - col) * (0.55 * stitch)[:, None]
    col = col + (srgb((70, 62, 46)) - col) * (0.75 * pstitch)[:, None]
    col *= (1 - 0.55 * tear)[:, None]
    col = col + (srgb((64, 58, 44)) - col) * (0.7 * cross)[:, None]
    col *= (1 - 0.40 * flap)[:, None]
    height += (-0.0006 * flap + 0.0007 * patch_amt + 0.0004 * hem - 0.0005 * groove + 0.00025 * stitch - 0.0003 * pstitch
               - 0.0006 * tear + 0.0003 * cross).astype(np.float32)
    col = np.clip(col, 0, 1)
    return col.astype(np.float32), height.astype(np.float32)

CH = 600000
col = np.zeros((n, 3), np.float32); height = np.zeros(n, np.float32)
for s0 in range(0, n, CH):
    sl = slice(s0, s0 + CH)
    col[sl], height[sl] = texels(P[sl], N[sl], AO[sl], REG[sl], K[sl])
print('texels done')


# ---- write base colour ----------------------------------------------------------------------------------------------
img = np.zeros((R, R, 3), np.float32); img[mask] = col
# fill anything outside the margin with the nearest baked texel (no black gutters for the low mips)
idx = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
img = img[idx[0], idx[1]]
Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(H + 'tex/suit_base.png', optimize=True)
print('WROTE suit_base.png')
small = Image.fromarray((img * 255 + 0.5).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS); small.save(H + 'tex/suit_base_preview.jpg')

del idx, img
# ---- detail normal from height, combined with the kept fold normal map ---------------------------------------------
Hm = np.zeros((R, R), np.float32); Hm[mask] = height
Pf = np.zeros((R, R, 3), np.float32); Pf[mask] = P.astype(np.float32)
def slope(axis):
    hp = np.roll(Hm, -1, axis); hm = np.roll(Hm, 1, axis)
    pp = np.roll(Pf, -1, axis); pm = np.roll(Pf, 1, axis)
    cp = np.roll(cov, -1, axis) & np.roll(cov, 1, axis) & cov
    d = np.linalg.norm(pp - pm, axis=2)
    ok = cp & (d > 1e-6) & (d < 0.004)
    return np.where(ok, (hp - hm) / np.maximum(d, 1e-6), 0).astype(np.float32)
du = slope(1)          # +u = +column
dv = -slope(0)         # +v = up = -row
gain = 1.0 / NORMAL_SCALE
old = np.asarray(Image.open(OLD_N).convert('RGB'), np.float32) / 127.5 - 1
nx = old[..., 0] - du * gain; ny = old[..., 1] - dv * gain; nz = old[..., 2]
ln = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
nm = np.stack([nx / ln, ny / ln, nz / ln], -1)
Image.fromarray(((nm * 0.5 + 0.5) * 255 + 0.5).clip(0, 255).astype(np.uint8)).save(H + 'tex/suit_normal.png', optimize=True)
print('WROTE suit_normal.png')
