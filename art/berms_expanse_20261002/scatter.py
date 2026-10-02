#!/usr/bin/env python3
"""Rock and scrub scatter for the Outer Berms expansion (2 Oct 2026) -> scatter.json (+ work/scatter.png).

Poisson-disc samples over the playable floor with a density that follows the ground: talus boulders round the
outcrops and at the mountain foot, cobbles and stones on the fans, scrub along the wash banks and in hollows, sparse
desert pavement elsewhere. Clear of sites (their own dressing), Warden routes, spawns, salvage, the old Berms footprint
and steep ground. Instances are existing kit prefabs (Poly Haven CC0 scans, see their records), uniform scale only.
Run: uv run --with numpy --with scipy --with matplotlib python scatter.py
"""
import json, math
from pathlib import Path
import numpy as np
from scipy import ndimage

HERE = Path(__file__).resolve().parent
FP = json.loads((HERE / 'footprint.json').read_text())
SITES = json.loads((HERE / 'sites.json').read_text())
RNG = np.random.default_rng(20261002)

KINDS = {   # prefab pool, scale range, minimum spacing (m)
    'boulder': (['WestGate/PH_BoulderA', 'WestGate/PH_BoulderB', 'WestGate/PH_BoulderC', 'OuterBermsDepot/PHD_BoulderD', 'OuterBermsDepot/PHD_BoulderE'], (0.8, 1.6), 9.0),
    'rock': (['WestGate/PH_RockA', 'WestGate/PH_RockB', 'WestGate/PH_RockC', 'WestGate/PH_RockD'], (0.8, 1.8), 6.0),
    'stones': (['WestGate/PH_StonesA', 'WestGate/PH_StonesB', 'WestGate/PH_StonesC'], (0.9, 1.5), 7.0),
    'scrub': (['WestGate/PH_RooibosA', 'WestGate/PH_RooibosB', 'WestGate/PH_RooibosC', 'WestGate/PH_SearsiaSmall'], (0.7, 1.3), 6.0),
    'deadwood': (['WestGate/PH_DryBranchA', 'WestGate/PH_DryBranchB'], (0.8, 1.2), 12.0),
}
TARGET = dict(boulder=110, rock=280, stones=170, scrub=230, deadwood=45)


def main():
    hf = np.load(HERE / 'work/heightfield.npz')
    H = hf['H'].astype(float); N, CELL, OX, OZ = hf['grid']; inF = hf['playable']; din = hf['d_in']; rocks = hf['rocks']
    gz, gx = np.gradient(H, CELL); slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    X, Z = np.meshgrid(OX + np.arange(int(N)) * CELL, OZ + np.arange(int(N)) * CELL)
    # wash banks: where the floor is cut below its 12 m neighbourhood mean
    lowpass = ndimage.uniform_filter(H, 24)
    wash = np.clip((lowpass - H) / 0.8, 0, 1)
    bank = ndimage.maximum_filter(wash, 9) * (1 - wash)
    talus = ndimage.maximum_filter((rocks > 1.0).astype(float), 25) * (rocks < 0.6)
    edge = np.clip(1 - din / 30.0, 0, 1) * inF
    x0, x1, z0, z1 = FP['old']
    old = (X > x0 - 6) & (X < x1 + 6) & (Z > z0 - 6) & (Z < z1 + 6)
    blocked = np.zeros_like(inF)
    def block(x, z, r):
        j, i = int(round((z - OZ) / CELL)), int(round((x - OX) / CELL)); rr = int(math.ceil(r))
        jj, ii = np.ogrid[-rr:rr + 1, -rr:rr + 1]; m = jj * jj + ii * ii <= rr * rr
        blocked[j - rr:j + rr + 1, i - rr:i + rr + 1] |= m
    for s in SITES['sites']:
        block(*s['centre'], 22 if s.get('waystation') else 17)
        for p in s['props']: block(*p['world'], 3)
    for r in SITES['routes']:
        for p in r: block(*p, 3)
    for f in SITES['tutorial']['first_contact'] + SITES['tutorial']['depot_extra']: block(*f['world'], 6)
    ok = inF & ~old & ~blocked & (din > 4) & (slope < 30)
    dens = dict(
        boulder=ok * (0.15 + 2.5 * talus + 1.4 * edge),
        rock=ok * (0.35 + 1.5 * talus + 1.0 * edge + 0.8 * bank),
        stones=ok * (0.5 + 0.8 * edge + 0.6 * bank),
        scrub=ok * (0.25 + 2.5 * bank + 0.6 * np.clip((ndimage.uniform_filter(H, 40) - H) / 0.5, 0, 1)),
        deadwood=ok * (0.2 + 1.5 * bank),
    )
    placed = []; pts = []
    cand_idx = np.flatnonzero(ok.ravel())
    for kind, target in TARGET.items():
        pool, (s0, s1), spacing = KINDS[kind]
        w = dens[kind].ravel()[cand_idx]; w = w / w.sum()
        tries = 0; n = 0
        while n < target and tries < target * 60:
            tries += 1
            k = cand_idx[RNG.choice(len(cand_idx), p=w)]
            x, z = float(X.ravel()[k] + RNG.uniform(-0.5, 0.5)), float(Z.ravel()[k] + RNG.uniform(-0.5, 0.5))
            if any((x - a) ** 2 + (z - b) ** 2 < (max(spacing, sp) * 0.5) ** 2 * (4 if kk == kind else 1) for a, b, sp, kk in pts): continue
            pts.append((x, z, spacing, kind))
            placed.append(dict(kind=kind, prefab=pool[RNG.integers(len(pool))], x=round(x, 2), z=round(z, 2),
                               yaw=round(float(RNG.uniform(0, 360)), 1), scale=round(float(RNG.uniform(s0, s1)), 2)))
            n += 1
    # the depot rise (the old ground's south-west slope, seen from the gate): talus and scrub on the slope, clear of
    # the conveyor (x -101..-87, z -48..-31) and the old footprint's interior work areas
    slope_zone = (X > -106) & (X < -90) & (Z > -29) & (Z < 9) & (slope > 6) & (slope < 34) & ~blocked
    zone_idx = np.flatnonzero(slope_zone.ravel())
    for kind, target in (('boulder', 14), ('rock', 22), ('scrub', 12), ('stones', 8)):
        pool, (s0, s1), spacing = KINDS[kind]; n = 0; tries = 0
        while n < target and tries < target * 80 and len(zone_idx):
            tries += 1; k = zone_idx[RNG.integers(len(zone_idx))]
            x, z = float(X.ravel()[k] + RNG.uniform(-0.5, 0.5)), float(Z.ravel()[k] + RNG.uniform(-0.5, 0.5))
            if any((x - a) ** 2 + (z - b) ** 2 < (max(spacing, sp) * 0.4) ** 2 for a, b, sp, kk in pts): continue
            pts.append((x, z, spacing, kind))
            placed.append(dict(kind=kind, prefab=pool[RNG.integers(len(pool))], x=round(x, 2), z=round(z, 2), zone='depot rise',
                               yaw=round(float(RNG.uniform(0, 360)), 1), scale=round(float(RNG.uniform(s0, s1 * 1.2)), 2)))
            n += 1
    (HERE / 'scatter.json').write_text(json.dumps(dict(version=1, seed=20261002, items=placed), indent=0) + '\n')
    from collections import Counter
    print(Counter(p['kind'] for p in placed))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 11))
    xa, xb, za, zb = -580, -50, -240, 230
    ja, jb = int((za - OZ) / CELL), int((zb - OZ) / CELL); ia, ib = int((xa - OX) / CELL), int((xb - OX) / CELL)
    ax.imshow(np.clip(0.6 - 0.45 * gx[ja:jb, ia:ib] - 0.65 * gz[ja:jb, ia:ib], 0, 1), cmap='gray', origin='lower', extent=(xa, xb, za, zb))
    col = dict(boulder='brown', rock='peru', stones='tan', scrub='green', deadwood='olive')
    for p in placed: ax.plot(p['x'], p['z'], '.', ms=4, color=col[p['kind']])
    fig.savefig(HERE / 'work/scatter.png', dpi=70, bbox_inches='tight')


if __name__ == '__main__':
    main()
