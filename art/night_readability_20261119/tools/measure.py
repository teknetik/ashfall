#!/usr/bin/env python3
"""Night readability measurements from native lookbook captures (19 Nov 2026).

  measure.py RUN_DIR [--diag DIAG_DIR] [--json out.json]
      Per capture: frame statistics in the central play area (HUD corners excluded): display-luminance p5/p25/p50/p95,
      share of near-black pixels (< 12/255) and of clipped pixels (>= 250 in all channels).
      Per actor in view (needs night-diag.json, from RUN_DIR or --diag): face, torso and surrounding-ground display
      luminance (Rec.709 luminance in linear light, re-encoded to sRGB 0-255) and the face/ground, torso/ground ratios.
  measure.py --compare BEFORE_DIR AFTER_DIR [--hours 13,17,6.5]
      Same-camera pixel difference (mean absolute sRGB difference per pixel, 0-255, and mean-luminance change),
      for checking that day hours are unchanged.
"""
import argparse, json, math, sys
from pathlib import Path
from PIL import Image
import numpy as np


def lin(a):
    a = a / 255.0
    return np.where(a <= .04045, a / 12.92, ((a + .055) / 1.055) ** 2.4)


def enc(y):
    y = np.clip(y, 0, 1)
    return 255 * np.where(y <= .0031308, y * 12.92, 1.055 * np.power(y, 1 / 2.4) - .055)


def load(path):
    a = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64)
    l = lin(a)
    return a, .2126 * l[..., 0] + .7152 * l[..., 1] + .0722 * l[..., 2]


def region(Y, box):
    h, w = Y.shape
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, x1 = max(0, x0), min(w, x1); y0, y1 = max(0, y0), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2: return None
    return float(Y[y0:y1, x0:x1].mean())


def frame_stats(rgb, Y):
    h, w = Y.shape
    c = Y[int(h * .30):int(h * .84), int(w * .22):int(w * .78)]
    crgb = rgb[int(h * .30):int(h * .84), int(w * .22):int(w * .78)]
    d = enc(c)
    return dict(p5=round(float(np.percentile(d, 5)), 1), p25=round(float(np.percentile(d, 25)), 1), p50=round(float(np.percentile(d, 50)), 1),
                p95=round(float(np.percentile(d, 95)), 1), mean=round(float(enc(np.array(c.mean()))), 1),
                black=round(float((d < 12).mean()), 3), clipped=round(float((crgb.min(axis=2) >= 250).mean()), 4))


def name_of(png):
    stem = png.stem
    cam, _, h = stem.rpartition('-h')
    return cam, float(h)


def measure(run, diag_dir=None):
    run = Path(run)
    diag = None
    for d in [Path(diag_dir) if diag_dir else None, run]:
        if d and (d / 'night-diag.json').exists():
            diag = json.loads((d / 'night-diag.json').read_text()); break
    entries = {}
    if diag:
        for e in diag['entries']: entries[(e['camera'], round(e['hour'], 2))] = e
    out = []
    for png in sorted(run.glob('*-h*.png')):
        cam, hour = name_of(png)
        rgb, Y = load(png)
        rec = dict(camera=cam, hour=hour, frame=frame_stats(rgb, Y), actors=[])
        e = entries.get((cam, round(hour, 2)))
        if e:
            rec['lightsInView'] = e['lightsInView']
            for a in e['actors']:
                s = a.get('screen')
                if not a['onScreen'] or not s: continue
                face = region(Y, s['face']) if s['face'] and s['faceVisible'] else None
                torso = region(Y, s['torso']) if s['torso'] and s['torsoVisible'] else None
                g = [region(Y, b) for b in s['ground']]; g = [x for x in g if x is not None]
                ground = float(np.median(g)) if g else None
                if face is None and torso is None: continue
                # skip actors whose face box is tiny (far away): under 6 px
                if s['face'] and (s['face'][2] - s['face'][0]) < 6: continue
                rec['actors'].append(dict(name=a['name'], kind=a['kind'], distance=a['distance'],
                                          face=None if face is None else round(float(enc(np.array(face))), 1),
                                          torso=None if torso is None else round(float(enc(np.array(torso))), 1),
                                          ground=None if ground is None else round(float(enc(np.array(ground))), 1),
                                          faceOverGround=None if face is None or not ground else round(face / ground, 2),
                                          torsoOverGround=None if torso is None or not ground else round(torso / ground, 2),
                                          moonShadow=a['moonShadowAtChest'], facing=a['facingCamera']))
        out.append(rec)
    return out


def compare(before, after, hours):
    res = []
    for png in sorted(Path(after).glob('*-h*.png')):
        cam, hour = name_of(png)
        if hours and not any(abs(hour - h) < .01 for h in hours): continue
        b = Path(before) / png.name
        if not b.exists(): continue
        ra, Ya = load(png); rb, Yb = load(b)
        res.append(dict(camera=cam, hour=hour, meanAbsDiff=round(float(np.abs(ra - rb).mean()), 2),
                        meanBefore=round(float(enc(np.array(Yb.mean()))), 1), meanAfter=round(float(enc(np.array(Ya.mean()))), 1)))
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run', nargs='?')
    p.add_argument('--diag')
    p.add_argument('--json')
    p.add_argument('--compare', nargs=2)
    p.add_argument('--hours', default='')
    a = p.parse_args()
    if a.compare:
        r = compare(*a.compare, [float(h) for h in a.hours.split(',') if h])
        for x in r: print('%-46s h%05.2f  diff %5.2f  mean %5.1f -> %5.1f' % (x['camera'], x['hour'], x['meanAbsDiff'], x['meanBefore'], x['meanAfter']))
    else:
        r = measure(a.run, a.diag)
        for x in r:
            f = x['frame']; L = x.get('lightsInView', {})
            print('%-46s h%05.2f  p5 %5.1f p25 %5.1f p50 %5.1f p95 %5.1f black %.3f clip %.4f  lights %s' % (x['camera'], x['hour'], f['p5'], f['p25'], f['p50'], f['p95'], f['black'], f['clipped'], L.get('total', '-')))
            for ac in x['actors']:
                print('      %-28s %-6s d%5.1f face %6s torso %6s ground %6s  F/G %5s T/G %5s moonShadow %s' % (ac['name'][:28], ac['kind'], ac['distance'], ac['face'], ac['torso'], ac['ground'], ac['faceOverGround'], ac['torsoOverGround'], ac['moonShadow']))
    if a.json: Path(a.json).write_text(json.dumps(r, indent=1))


if __name__ == '__main__':
    main()
