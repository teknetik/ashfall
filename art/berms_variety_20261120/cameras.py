#!/usr/bin/env python3
"""Review cameras `cam_bv_*` for the Outer Berms ground variety pass -> review_cameras.json.

Player eye height (1.6 m above the ground) between neighbouring sites, looking from one toward the other, plus two
long views across the bowl and two that repeat old `cam_bx_*` poses for comparison. Positions are on the ground field.
Run: python3 cameras.py
"""
import json, math
from bv_common import Field, HERE

EYE = 1.6
F = Field()


def cam(name, at, look, between, fov=60.0, eye=EYE, note=''):
    x, z = at; tx, tz = look
    y = float(F.ground(x, z)) + eye
    ty = float(F.ground(tx, tz)) + 1.2
    return dict(name=name, pos=[round(x, 2), round(y, 2), round(z, 2)], target=[round(tx, 2), round(ty, 2), round(tz, 2)],
                fov=fov, between=between, note=note)


def lerp(a, b, t):
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]


S = {  # site centres (art/berms_expanse_20261002/sites.json, art/next_level_20261002/enemies/sites.json)
    'northgate': [-132, 64], 'caravan': [-205, 74], 'scrapper': [-208, -40], 'waystation': [-266, 52],
    'relay': [-330, 8], 'derrick': [-302, 140], 'scrapyard': [-292, -106], 'mesa': [-366, 86], 'pylon': [-424, -96],
    'westfans': [-486, -24], 'southridge': [-352, -176], 'dunes': [-468, 132], 'postrelay': [-432, 22],
    'reaper': [-242, 142], 'fanscamp': [-492, -108], 'southcache': [-252, -152],
}


import numpy as _np
_FEAT = json.loads((HERE / 'features.json').read_text()) if (HERE / 'features.json').exists() else {'ledges': []}
_PL = json.loads((HERE / 'placements.json').read_text())['prefabs'] if (HERE / 'placements.json').exists() else []


def blocked(at, look):
    """A camera spot is blocked if an outcrop (outline + 5 m apron) or a kit piece is within reach of the lens, or the
    first 14 m of the view line passes through one (fix round 2: two cameras ended up inside rebuilt outcrops)."""
    P = _np.asarray(at, float); D = _np.asarray(look, float) - P; D /= _np.linalg.norm(D)
    def hit(q, pad):
        for l in _FEAT['ledges']:
            O = _np.asarray(l['outline']); d = _np.hypot(O[:, 0] - q[0], O[:, 1] - q[1]).min()
            inside = _np.hypot(q[0] - l['x'], q[1] - l['z']) < _np.hypot(O[:, 0] - l['x'], O[:, 1] - l['z']).max()
            if inside or d < pad + 5: return True
        return any(_np.hypot(p['x'] - q[0], p['z'] - q[1]) < pad + 1.5 * p['scale'] for p in _PL)
    if hit(P, 2.0): return True
    return any(hit(P + D * s, 0.5) for s in _np.arange(2, 15, 1.0))


def between(a, b, t=0.3, side=0.0, name=None, fov=60.0):
    A, B = S[a], S[b]
    dx, dz = B[0] - A[0], B[1] - A[1]; L = math.hypot(dx, dz)
    def spot(tt, sd): q = lerp(A, B, tt); return [q[0] - dz / L * sd, q[1] + dx / L * sd]
    p = spot(t, side)
    if blocked(p, B):          # nearest clear standing spot that still looks from A toward B
        for r in range(1, 40):
            cands = [(t + dt, side + ds) for dt in (0, -0.02 * r, 0.02 * r) for ds in (0, -r, r) if 0.15 <= t + dt <= 0.7]
            ok = [c for c in cands if not blocked(spot(*c), B)]
            if ok:
                p = spot(*ok[0]); print('moved', name or f'cam_bv_{a}_{b}', 'to t=%.2f side=%.0f' % ok[0]); break
    return cam(name or f'cam_bv_{a}_{b}', p, B, [a, b], fov=fov)


cams = [
    between('northgate', 'caravan', 0.25, 6),
    between('scrapper', 'waystation', 0.3, -6),
    between('waystation', 'relay', 0.35, 5),
    between('caravan', 'derrick', 0.35, -5),
    between('relay', 'scrapyard', 0.3, 8),
    between('mesa', 'dunes', 0.62, 4),
    between('scrapyard', 'pylon', 0.3, 6),
    between('pylon', 'westfans', 0.35, -6),
    between('southridge', 'scrapyard', 0.35, 6),
    between('relay', 'postrelay', 0.35, 6),
    cam('cam_bv_long_gate', [-112, -6], [-420, 10], ['West Gate side', 'far west fans'], fov=55, eye=1.8,
        note='long view across the bowl from the gate side'),
    cam('cam_bv_long_far', [-520, 30], [-180, 0], ['far west fans', 'West Gate side'], fov=55, eye=1.8,
        note='long view back across the bowl from the far side'),
    # repeats of old cam_bx_* poses (art/berms_expanse_20261002/review_cameras.json), heights there are 1.7 m
    cam('cam_bv_bx_gate_west', [-66, 2], [-200, 10], ['West Gate', 'Northgate scrap / caravan'], eye=1.7,
        note='same pose as cam_bx_gate_west'),
    cam('cam_bv_bx_scrapyard', [-268, -92], [-292, -106], ['Wash scrapyard', 'its approach'], fov=55, eye=1.7,
        note='same pose as cam_bx_scrapyard'),
]
# cam_bx targets were absolute heights; keep the bx comparison targets as they were
cams[-2]['target'][1] = 2.0; cams[-1]['target'][1] = 2.0
(HERE / 'review_cameras.json').write_text(json.dumps(dict(version=1, eye=EYE, cameras=cams), indent=1) + '\n')
for c in cams: print(c['name'], c['pos'], '->', c['target'], 'BLOCKED' if blocked([c['pos'][0], c['pos'][2]], [c['target'][0], c['target'][2]]) else '')
