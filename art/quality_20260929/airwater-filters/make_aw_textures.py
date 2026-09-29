"""Original deterministic PBR maps for the Air + Water filter-bank fittings (29 Sep 2026, task t_bd3d9fe3).

    env -i HOME=$HOME PATH=/usr/bin:/bin /usr/bin/python3 make_aw_textures.py [AW_Name ...]

numpy only. Helper functions (noise, painted steel, bare steel, rubber) come unchanged from the Basic General / Tool Exchange packages
(aw_textures_base.py); bronze, mineral scale, the label atlas and the gauge dial are new here.
  *_BaseColor.png   sRGB albedo
  *_Normal.png      tangent-space OpenGL (+Y up), linear
  *_MetalSmooth.png R metallic, A smoothness (1 - roughness), G/B zero  (URP Lit metallic-gloss map)
Tiling maps are 2048x2048. Unique maps: AW_Labels 4096x512 at 6000 px/m (plates 0.17 x 0.06 m = 1020 x 360 px), AW_Dial 1024x1024 for the
0.0576 m gauge face (17,800 px/m).  Lettering is rasterised from Liberation Sans Bold (SIL OFL 1.1) by ImageMagick, so it is real text, not
generated imagery.  Every word is functional (FILTER 1/2/3, ISOLATE, SHUT, OPEN, BAR, numerals); nothing is lore.
"""
import sys, json, subprocess, os
from pathlib import Path
import numpy as np
import aw_textures_base as B
from aw_textures_base import (fbm, vnoise, blur, stretch, normal_from_height, scratches, pack_metal_smooth, srgb8, emit, painted,
                              bare_steel, rubber, N, OUT, MANIFEST)

B.VARIANTS.clear()
ONLY = set(sys.argv[1:])
MAGICK = '/usr/sbin/magick'
FONT = '/usr/share/fonts/liberation/LiberationSans-Bold.ttf'
TMP = Path(os.environ.get('TMPDIR', '/tmp'))


def want(k):
    return not ONLY or k in ONLY


def bronze(name, seed, tile_m, note):
    """Cast/forged bronze fittings: warm orange-brown, dark tarnish, green verdigris gathered in crevices, bright polished wear on ridges."""
    rng = np.random.default_rng(seed)
    g = fbm(rng, N, N, [500, 1100, 2000], [1, 1, .8])
    lowf = fbm(rng, N, N, [5, 17, 60], [1, .7, .5])
    brushed = vnoise(rng, N, N, 1500, 5) * .6 + vnoise(rng, N, N, 900, 3) * .4
    tarn = stretch(fbm(rng, N, N, [8, 30, 110, 400], [1, .8, .6, .5]), .50, .74)
    verd = stretch(fbm(rng, N, N, [7, 26, 90, 330], [1, .8, .6, .5]), .64, .80)
    bright = stretch(fbm(rng, N, N, [10, 40, 160], [1, .8, .6]), .60, .80)
    pit = stretch(vnoise(rng, N, N, 320, 320), .90, .975)
    sc = np.clip(scratches(rng, N, N, 200, 400, .0, .1, .9), 0, 1)
    cu = np.array((.60, .34, .16), np.float32)[None, None, :]
    dark = np.array((.20, .105, .05), np.float32)[None, None, :]
    green = np.array((.16, .34, .27), np.float32)[None, None, :]
    pol = np.array((.78, .55, .27), np.float32)[None, None, :]
    c = cu * (.80 + .3 * brushed[..., None]) * (.92 + .16 * lowf[..., None])
    c = c * (1 - tarn[..., None] * .62) + dark * tarn[..., None] * .62
    c = c * (1 - verd[..., None] * .70) + green * verd[..., None] * .70
    c = c * (1 - bright[..., None] * .35) + pol * bright[..., None] * .35
    c = c * (1 - pit[..., None] * .4) + sc[..., None] * .05
    h = (brushed - .5) * .003 + (g - .5) * .002 - pit * .004 + verd * .002 - sc * .0015
    metal = np.clip(1.0 - verd * .85 - tarn * .25, 0, 1)
    smooth_v = .50 + (brushed - .5) * .24 + bright * .18 - tarn * .28 - verd * .30 - pit * .15
    emit(name, srgb8(c), normal_from_height(h, 140), pack_metal_smooth(metal, smooth_v), tile_m, note)


def mineral(name, seed, tile_m, note):
    """Hard-water scale / calcite crust: off-white to tan terraces, iron-oxide tide lines, gritty and matte. Non-metal."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    g = fbm(rng, N, N, [400, 900, 1700], [1, 1, .8])
    lowf = fbm(rng, N, N, [4, 13, 45], [1, .7, .5])
    warp = fbm(rng, N, N, [3, 9, 30], [1, .6, .3])
    terr = .5 + .5 * np.sin((y * 34 + warp * 6.0) * 2 * np.pi)           # growth terraces run along U
    terr = terr ** 1.6
    iron = stretch(fbm(rng, N, N, [5, 19, 70, 260], [1, .8, .6, .4]), .58, .78) * (.4 + .6 * terr)
    tan = stretch(fbm(rng, N, N, [6, 22, 80], [1, .8, .6]), .45, .70)
    blob = stretch(vnoise(rng, N, N, 130, 130), .82, .96)
    white = np.array((.80, .77, .69), np.float32)[None, None, :]
    tanc = np.array((.62, .54, .40), np.float32)[None, None, :]
    rust = np.array((.42, .21, .10), np.float32)[None, None, :]
    c = white * (.80 + .28 * g[..., None]) * (.92 + .16 * lowf[..., None]) * (.88 + .16 * terr[..., None])
    c = c * (1 - tan[..., None] * .55) + tanc * tan[..., None] * .55
    c = c * (1 - iron[..., None] * .70) + rust * iron[..., None] * .70
    c = c * (1 - blob[..., None] * .16)
    h = terr * .008 + (g - .5) * .006 + blob * .004 + (lowf - .5) * .006
    smooth_v = .10 + terr * .07 + iron * .06 - (g - .5) * .06
    emit(name, srgb8(c), normal_from_height(h, 160), pack_metal_smooth(np.zeros((N, N), np.float32), smooth_v), tile_m, note)


# ------------------------------------------------------------------------------------------- lettering helpers
def text_mask(text, w, h, pt, gravity='center', extra=()):
    """Render `text` white-on-black at w x h with Liberation Sans Bold; returns float mask 0..1 (h, w)."""
    raw = TMP / 'aw_text.gray'
    cmd = [MAGICK, '-size', f'{w}x{h}', 'xc:black', '-fill', 'white', '-font', FONT, '-pointsize', str(pt), '-gravity', gravity,
           '-kerning', '2', *extra, '-annotate', '+0+0', text, '-depth', '8', '-colorspace', 'Gray', f'gray:{raw}']
    subprocess.run(cmd, check=True)
    return np.fromfile(raw, np.uint8).reshape(h, w).astype(np.float32) / 255.0


PPM_L = 6000
ATL = {'FILTER 1': (0, 0, 1020, 360), 'FILTER 2': (1032, 0, 1020, 360), 'FILTER 3': (2064, 0, 1020, 360), 'ISOLATE': (3096, 0, 720, 480)}


def labels():
    W, H = 4096, 512
    rng = np.random.default_rng(929501)
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    base = np.zeros((H, W, 3), np.float32) + np.array((.02, .02, .02), np.float32)
    hgt = np.zeros((H, W), np.float32)
    metal = np.zeros((H, W), np.float32)
    smooth_v = np.full((H, W), .25, np.float32)
    mott = fbm(rng, H, W, [4, 14, 60, 240], [1, .8, .6, .4])
    grain = fbm(rng, H, W, [500, 1000, 1800], [1, 1, .8])
    layout = {}
    for k, (x0, y0, w, h) in ATL.items():
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        lx = (x[sl] - x0); ly = (y[sl] - y0)
        edge = np.minimum(np.minimum(lx, w - 1 - lx), np.minimum(ly, h - 1 - ly))
        # rolled rim + inner rule
        rim = np.clip((16 - edge) / 2.0, 0, 1)
        rule = np.clip(1 - np.abs(edge - 34) / 3.0, 0, 1)
        if k == 'ISOLATE':
            t1 = np.roll(text_mask('ISOLATE', w, h, 138, 'center'), -78, 0)
            t2 = np.roll(text_mask('SHUT  |  OPEN', w, h, 76, 'center'), 92, 0)
            txt = np.maximum(t1, t2)
        else:
            txt = text_mask(k, w, h, 205)
        enam = np.array((.055, .10, .17), np.float32)[None, None, :] * (.85 + .3 * mott[sl][..., None])
        cream = np.array((.86, .80, .62), np.float32)[None, None, :] * (.9 + .2 * grain[sl][..., None])
        steel = np.array((.44, .44, .43), np.float32)[None, None, :] * (.85 + .3 * grain[sl][..., None])
        rust = np.array((.30, .155, .075), np.float32)[None, None, :]
        soil = np.array((.56, .46, .32), np.float32)[None, None, :]
        wear = stretch(fbm(rng, h, w, [10, 40, 160, 600], [1, .8, .6, .4]), .60, .82) * (.25 + .9 * np.clip(1 - edge / 120.0, 0, 1))
        chip = stretch(.5 * fbm(rng, h, w, [30, 90, 300], [1, .8, .6]) + .5 * fbm(rng, h, w, [500, 900], [1, 1]), .90, .93)
        sc = np.clip(scratches(rng, h, w, 90, 260, .05, .5, 1.1), 0, 1)
        dust = stretch(fbm(rng, h, w, [8, 30, 110], [1, .8, .6]), .52, .78) * (.35 + .65 * (ly / h))
        c = enam * (1 - txt[..., None]) + cream * txt[..., None] * (1 - .35 * wear[..., None])
        c = c * (1 - rule[..., None] * .95) + cream * rule[..., None] * .95 * (1 - .35 * wear[..., None])
        c = c * (1 - rim[..., None]) + steel * rim[..., None]
        c = c * (1 - chip[..., None]) + rust * chip[..., None] * .8 + steel * chip[..., None] * .2
        c = c * (1 - sc[..., None] * .30) + steel * sc[..., None] * .30
        c = c * (1 - dust[..., None] * .38) + soil * dust[..., None] * .38
        base[sl] = c
        hgt[sl] = txt * .0004 + rule * .0003 - rim * .0006 - chip * .0006 + (grain[sl] - .5) * .0004
        metal[sl] = np.clip(rim * .9 + chip * .8 + sc * .3, 0, 1) * (1 - dust * .7)
        smooth_v[sl] = np.clip(.72 - .45 * wear - .35 * dust - .1 * txt, .06, .85)
        layout[k] = dict(px=[x0, y0, w, h], uv=[x0 / W, 1 - (y0 + h) / H, (x0 + w) / W, 1 - y0 / H], metres=[w / PPM_L, h / PPM_L])
    emit('AW_Labels', srgb8(base), normal_from_height(hgt, 500), pack_metal_smooth(metal, smooth_v), None,
         'Unique 4096x512 at 6000 px/m: four enamel service plates (FILTER 1, FILTER 2, FILTER 3, ISOLATE / SHUT | OPEN) with rolled steel rim, raised cream '
         'lettering (Liberation Sans Bold, SIL OFL 1.1), chips, rust, dust. Region rectangles in layout.json (uv = [u0, v0, u1, v1], v up).', PPM_L)
    return layout


def dial():
    S = 1024
    cx = cy = S / 2
    R = S / 2 - 6
    rng = np.random.default_rng(929502)
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    dx, dy = x - cx, y - cy
    r = np.hypot(dx, dy) / R
    ang = np.degrees(np.arctan2(dx, -dy))                 # 0 = up, clockwise positive
    bar = (ang + 135.0) / 270.0 * 6.0                     # 0..6 bar over the 270 degree sweep
    inside = (r < 1.0)
    face = np.array((.86, .82, .70), np.float32)[None, None, :]
    mott = fbm(rng, S, S, [4, 14, 60, 240], [1, .8, .6, .4])
    grain = fbm(rng, S, S, [300, 700], [1, 1])
    c = face * (.92 + .16 * mott[..., None]) * (.97 + .06 * grain[..., None])
    ink = np.array((.06, .06, .055), np.float32)[None, None, :]
    arc_ok = (bar >= 0) & (bar <= 6)
    band_g = (r > .70) & (r < .80) & arc_ok & (bar >= 1.0) & (bar <= 3.5)
    band_a = (r > .70) & (r < .80) & arc_ok & (bar > 3.5) & (bar <= 4.5)
    band_r = (r > .70) & (r < .80) & arc_ok & (bar > 4.5)
    for m, col in ((band_g, (.10, .36, .16)), (band_a, (.72, .46, .08)), (band_r, (.62, .07, .05))):
        c = np.where(m[..., None], np.array(col, np.float32)[None, None, :], c)
    # ticks: 6 major + minor every 0.2 bar
    tk = np.zeros((S, S), np.float32)
    for i in range(0, 31):
        b = i * .2
        a = -135 + 270 * b / 6
        major = (i % 5 == 0)
        half = .011 if major else .005
        d = np.abs(((ang - a + 180) % 360) - 180) * np.pi / 180 * r        # arc-length distance in units of R
        rr0 = .58 if major else .64
        tk = np.maximum(tk, ((d < half) & (r > rr0) & (r < .68)).astype(np.float32))
    c = np.where((tk > .5)[..., None], ink, c)
    # numerals 0..6 and 'BAR'
    for b in range(0, 7):
        a = np.radians(-135 + 270 * b / 6)
        px_, py_ = cx + np.sin(a) * R * .44, cy - np.cos(a) * R * .44
        t = text_mask(str(b), 96, 96, 84)
        x0, y0 = int(px_ - 48), int(py_ - 48)
        c[y0:y0 + 96, x0:x0 + 96] = c[y0:y0 + 96, x0:x0 + 96] * (1 - t[..., None]) + ink * t[..., None]
    t = text_mask('BAR', 220, 90, 78)
    x0, y0 = int(cx - 110), int(cy + R * .52 - 45)
    c[y0:y0 + 90, x0:x0 + 220] = c[y0:y0 + 90, x0:x0 + 220] * (1 - t[..., None]) + ink * t[..., None]
    # hub circle (needle pivots on it) and wear
    hub = (r < .07)
    c = np.where(hub[..., None], np.array((.12, .12, .11), np.float32)[None, None, :], c)
    dust = stretch(fbm(rng, S, S, [6, 24, 90, 320], [1, .8, .6, .4]), .50, .74) * (.3 + .7 * (r))
    c = c * (1 - dust[..., None] * .35) + np.array((.55, .46, .32), np.float32)[None, None, :] * dust[..., None] * .35
    edge = stretch(r - .90, 0, .10)
    c = c * (1 - edge[..., None] * .3)
    c = np.where(inside[..., None], c, np.array((.05, .05, .05), np.float32)[None, None, :])
    h = tk * .0001 + (grain - .5) * .0001
    smooth_v = np.clip(.62 - dust * .35, .1, .8)
    emit('AW_Dial', srgb8(c), normal_from_height(h, 80), pack_metal_smooth(np.zeros((S, S), np.float32), smooth_v), None,
         'Unique 1024x1024 gauge face, 0..6 BAR over a 270 degree sweep starting at 7:30 (-135 deg from 12 o clock, clockwise positive): green 1.0-3.5, '
         'amber 3.5-4.5, red 4.5-6.0. Face circle spans the full texture, centre (0.5, 0.5), radius 0.494. Numerals and BAR from Liberation Sans Bold.', 17800)


if __name__ == '__main__':
    layout = {}
    if want('AW_PaintSlate'):
        painted('AW_PaintSlate', 929511, (.155, .195, .185), .55, .10, .50, 200, .50,
                'Dark slate-green enamel over steel (vessel and bracket paint): orange-rust halos at chips, scratches; matches the existing canister colour.', orange_peel=.8)
    if want('AW_ValveRed'):
        painted('AW_ValveRed', 929512, (.50, .085, .065), .42, .07, .28, 120, .40,
                'Red enamel valve lever and gauge set-pointer flag: chipped to bare steel at the grip, rust halos.', orange_peel=.6)
    if want('AW_BareSteel'):
        bare_steel('AW_BareSteel', 929513, .50, 'Zinc-plated / bare steel bolts, nuts, washers, straps: brushed, patchy rust and dark staining.')
    if want('AW_Rubber'):
        rubber('AW_Rubber', 929514, .30, 'Black rubber seals, gasket rings, lever grip: fine grain, crazing, dust bloom.')
    if want('AW_Bronze'):
        bronze('AW_Bronze', 929515, .50, 'Bronze unions, flanges, valve body: tarnish, verdigris in crevices, bright wear on ridges.')
    if want('AW_Mineral'):
        mineral('AW_Mineral', 929516, .30, 'Hard-water scale crust and iron-stained tide lines at wet joints; matte, non-metal.')
    if want('AW_Labels'):
        layout['labels'] = labels()
    if want('AW_Dial'):
        dial()
    old = json.loads((OUT / 'manifest.json').read_text())['materials'] if ONLY and (OUT / 'manifest.json').exists() else []
    done = {m['material'] for m in MANIFEST}
    MANIFEST.extend(m for m in old if m['material'] not in done)
    prev = json.loads((OUT / 'layout.json').read_text()) if ONLY and (OUT / 'layout.json').exists() else {}
    prev.update(layout)
    (OUT / 'layout.json').write_text(json.dumps(prev, indent=2))
    (OUT / 'manifest.json').write_text(json.dumps({
        'author': 'Original deterministic Ward material synthesis (numpy), Air + Water filter-bank fittings', 'date': '2026-09-29',
        'licence': 'Project original; no third-party source imagery; no generative-model output. Lettering rasterised from Liberation Sans Bold (SIL OFL 1.1).',
        'seed': 'per-material seeds 929501-929516 in make_aw_textures.py', 'normal': 'OpenGL +Y tangent space',
        'packed': 'R metallic; A smoothness; G/B zero', 'colourSpace': 'BaseColor sRGB; Normal + MetalSmooth linear', 'materials': MANIFEST}, indent=2))
    print('done', len(MANIFEST), 'materials')
