#!/usr/bin/env python3
"""Source-side preview: ray-marches the basin heightfield (old raster vs new) from the scene's review cameras with a
shader-like look (rock/scree/sand by slope, world-Y strata, Lambert sun with self-shadow inside the 150 m shadow
distance, sky access, the terrain distance haze). Not a Unity render: it judges silhouettes, landforms and haze curves.

  uv run --with numpy --with numba --with scipy --with pillow python preview.py [--cams a,b] [--hours 13,17] [--haze old|new]
Writes work/preview/<cam>-h<hour>-<old|new>.png and a side-by-side sheet.
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import numba as nb
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
WORK = HERE / 'work'
ROOT = Path('/home/teknetik/code/ao2')
CAMS = ROOT / 'unity/evidence/basin-mountains/20261001/cameras.json'
N, CELL, ORG = 1025, 1.0, -512.0

# WardDustbowl frames (hour: key euler x,y; key colour*intensity; ambient sky; fog colour; sky horizon, zenith)
FRAMES = {
    12: ((38, 140), (1, .9, .76), 2.1, (.33, .4, .52), (.7, .62, .5), (.82, .66, .45), (.15, .31, .62)),
    16: ((24, 168), (1, .78, .55), 1.8, (.28, .33, .44), (.66, .53, .4), (.86, .58, .33), (.13, .26, .55)),
    17: ((11, 230), (1, .6, .33), 1.35, (.26, .32, .45), (.52, .37, .26), (.86, .45, .2), (.13, .21, .37)),
}
AUTH_FOG = (.64, .47, .31)


def lin(c): return np.array([x ** 2.2 for x in c])


def frame(hour):
    ks = sorted(FRAMES)
    if hour <= ks[0]: return FRAMES[ks[0]]
    for a, b in zip(ks, ks[1:]):
        if a <= hour <= b:
            f = (hour - a) / (b - a); A, B = FRAMES[a], FRAMES[b]
            mix = lambda x, y: tuple(np.array(x) * (1 - f) + np.array(y) * f)
            return (mix(A[0], B[0]), mix(A[1], B[1]), A[2] * (1 - f) + B[2] * f, mix(A[3], B[3]), mix(A[4], B[4]), mix(A[5], B[5]), mix(A[6], B[6]))
    return FRAMES[ks[-1]]


@nb.njit(cache=True)
def hsample(H, x, z):
    fx = (x - ORG) / CELL; fz = (z - ORG) / CELL
    if fx < 0: fx = 0.0
    if fz < 0: fz = 0.0
    if fx > N - 1.001: fx = N - 1.001
    if fz > N - 1.001: fz = N - 1.001
    i = int(fx); j = int(fz); u = fx - i; v = fz - j
    return (H[j, i] * (1 - u) * (1 - v) + H[j, i + 1] * u * (1 - v) + H[j + 1, i] * (1 - u) * v + H[j + 1, i + 1] * u * v)


@nb.njit(parallel=True, cache=True)
def render(H, SKY, W, Hh, cp, fw, rt, up, tanh, sund, keyc, amb, hazec, hd, hfar, hfs, hhf, hzen, hhor, rock_slope, out):
    for py in nb.prange(Hh):
        for px in range(W):
            sx = (2 * (px + .5) / W - 1) * tanh * W / Hh
            sy = (1 - 2 * (py + .5) / Hh) * tanh
            d = fw + rt * sx + up * sy
            d = d / math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
            t = 0.5; hit = False; prev = 0.5
            while t < 650:
                x = cp[0] + d[0] * t; y = cp[1] + d[1] * t; z = cp[2] + d[2] * t
                if y < hsample(H, x, z):
                    hit = True; break
                prev = t
                t += max(0.2, t * 0.0035)
            if not hit:
                e = max(d[1], 0.0) ** 0.6
                for c in range(3): out[py, px, c] = hhor[c] * (1 - e) + hzen[c] * e
                continue
            lo = prev; hi = t
            for k in range(10):
                m = (lo + hi) * .5
                if cp[1] + d[1] * m < hsample(H, cp[0] + d[0] * m, cp[2] + d[2] * m): hi = m
                else: lo = m
            t = hi
            x = cp[0] + d[0] * t; y = cp[1] + d[1] * t; z = cp[2] + d[2] * t
            e = 0.7
            gx = (hsample(H, x + e, z) - hsample(H, x - e, z)) / (2 * e)
            gz = (hsample(H, x, z + e) - hsample(H, x, z - e)) / (2 * e)
            nx = -gx; ny = 1.0; nz = -gz; nl = math.sqrt(nx * nx + ny * ny + nz * nz); nx /= nl; ny /= nl; nz /= nl
            slope = 1 - ny
            # albedo (linear): rock / scree / sand like Ward Desert Terrain V2
            wr = min(max((slope - rock_slope + .035) / .07, 0.0), 1.0)
            ws = (1 - wr) * (1.0 if slope < 0.03 else 0.0) * 0.5
            rock = np.array([.30, .17, .085]); scree = np.array([.27, .17, .085]); sand = np.array([.31, .21, .11])
            bandf = (y + math.sin(x * 0.024 + z * 0.018) * 2.0) / 1.7
            bid = math.floor(bandf)
            rnd = math.sin(bid * 12.9898) * 43758.5453; rnd = rnd - math.floor(rnd)
            sa = min(max((slope - .1) / .35, 0.0), 1.0)
            st = 1.0 + sa * ((0.73 + 0.4 * rnd) - 1.0)
            alb = (rock * st * wr + scree * (1 - wr - ws) + sand * ws)
            # sun: lambert with shadow ray inside 150 m of the camera (beyond: none, like URP)
            ndl = max(nx * sund[0] + ny * sund[1] + nz * sund[2], 0.0)
            sh = 1.0
            if ndl > 0 and t < 150:
                s = 0.6
                while s < 160:
                    if y + 0.15 + sund[1] * s < hsample(H, x + sund[0] * s, z + sund[2] * s):
                        sh = 0.0; break
                    s += max(0.4, s * 0.03)
            fi = (x - ORG) / CELL; fj = (z - ORG) / CELL
            sky = SKY[min(max(int(fj + .5), 0), N - 1), min(max(int(fi + .5), 0), N - 1)]
            col = np.empty(3)
            for c in range(3):
                col[c] = alb[c] * (keyc[c] * ndl * sh + amb[c] * (0.6 + 0.4 * ny) * sky * 1.4)
            # terrain haze: optical depth with optional far scale and height falloff
            dd = max(0.0, t - 38.0)
            if hfs < 0.999 and dd > hfar: dd = hfar + (dd - hfar) * hfs
            od = dd * hd
            if hhf > 0:
                h0 = max(cp[1] - 6.0, 0.0) / hhf; h1 = max(y - 6.0, 0.0) / hhf
                if abs(h1 - h0) > 1e-4: od *= (math.exp(-h0) - math.exp(-h1)) / (h1 - h0)
                else: od *= math.exp(-h0)
            hz = 1 - math.exp(-od)
            hz = min(max(hz + math.exp(-max(0.0, y) * 0.06) * 0.11, 0.0), 1.0)
            for c in range(3): out[py, px, c] = col[c] * (1 - hz) + hazec[c] * hz


def tonemap(img, exposure):
    x = img * exposure
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    y = np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)
    return (y ** (1 / 2.2) * 255).astype(np.uint8)


def euler_dir(ex, ey):
    p, y = math.radians(ex), math.radians(ey)
    fwd = np.array([math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p)])
    return -fwd


def haze_params(kind):
    # density, far start, far scale, height falloff (m)
    return {'old': (0.0068, 1e9, 1.0, 0.0), 'new': (0.0068, 90.0, 0.5, 55.0)}[kind] if isinstance(kind, str) else kind


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cams', default='cam_hill,cam_avenue,cam_westgate_mouth,cam_berms_overview,cam_berms_road,cam_courtyard')
    ap.add_argument('--hours', default='13,17')
    ap.add_argument('--fields', default='old,new')
    ap.add_argument('--haze', default='old,new')
    ap.add_argument('--tag', default='')
    ap.add_argument('--size', default='960x540')
    ap.add_argument('--rock-slope', type=float, default=0.075)
    ap.add_argument('--pose', default='', help='extra camera: name,x,y,z,fx,fy,fz,fov')
    a = ap.parse_args()
    W, Hh = map(int, a.size.split('x'))
    hf = np.load(WORK / 'heightfield.npz')
    fields = {'new': hf['H'].astype(np.float64)}
    old = hf['old'].astype(np.float64)
    fields['old'] = np.where(np.isfinite(old), old, -1.8)
    sky = hf['sky'].astype(np.float64)
    cams = {c['name']: c for c in json.loads(CAMS.read_text())['cameras']}
    if a.pose:
        v = a.pose.split(','); f = np.array(list(map(float, v[4:7]))); f /= np.linalg.norm(f)
        r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r); u = np.cross(f, r)
        cams[v[0]] = dict(name=v[0], pos=list(map(float, v[1:4])), fwd=list(f), up=list(u), fov=float(v[7]))
    out_dir = WORK / 'preview'; out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for cam in a.cams.split(','):
        c = cams[cam]
        cp = np.array(c['pos'], float); fw = np.array(c['fwd'], float); up = np.array(c['up'], float)
        rt = np.cross(up, fw); rt /= np.linalg.norm(rt)    # Unity left-handed: right = up x forward
        tanh = math.tan(math.radians(c['fov']) / 2)
        for hour in map(float, a.hours.split(',')):
            fr = frame(hour)
            sund = euler_dir(*fr[0]); keyc = lin(fr[1]) * fr[2]; amb = lin(fr[3])
            scale = lin(fr[4]) / lin(AUTH_FOG)
            hazec = lin((.66, .54, .40)) * scale
            row = []
            for fld, hz in zip(a.fields.split(','), a.haze.split(',')):
                hp = haze_params(hz)
                img = np.zeros((Hh, W, 3))
                render(fields[fld], sky, W, Hh, cp, fw, rt, up, tanh, sund, keyc, amb, hazec, hp[0], hp[1], hp[2], hp[3],
                       lin(fr[6]) * 1.2, lin(fr[5]) * 1.1, a.rock_slope, img)
                name = '%s-h%05.2f-%s-%s%s.png' % (cam, hour, fld, hz, a.tag)
                Image.fromarray(tonemap(img, 1.25 if hour < 16.5 else 1.6)).save(out_dir / name)
                row.append(name)
            rows.append(row)
    # sheet
    tw, th = W // 2, Hh // 2
    sheet = Image.new('RGB', (tw * max(len(r) for r in rows), (th + 18) * len(rows)), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    for j, r in enumerate(rows):
        for i, n in enumerate(r):
            sheet.paste(Image.open(out_dir / n).resize((tw, th)), (i * tw, j * (th + 18) + 18))
            dr.text((i * tw + 4, j * (th + 18) + 3), n, fill=(230, 220, 200))
    sheet.save(out_dir / ('sheet%s.jpg' % a.tag), quality=88)
    print('sheet', out_dir / ('sheet%s.jpg' % a.tag))


if __name__ == '__main__':
    main()
