"""Shared helpers for the Outer Berms ground variety pass (20 Nov 2026): heightfield access, the bowl window, sites,
routes and the saved-scene survey. Unity world metres (X east, Z north, Y up).

The heightfield is the Berms expansion's `art/berms_expanse_20261002/work/heightfield.npz` (2049 x 2049 at 1 m from
(-1088, -1024)). The walkable ground tiles were built from it at +4 cm with a 2.5 cm error, so H + 0.04 is the ground.
"""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BX = ROOT / 'art/berms_expanse_20261002'
NL = ROOT / 'art/next_level_20261002/enemies'
UNITY = ROOT / 'unity/AthenHill'
ART_OUT = UNITY / 'Assets/AthenHill/Art/BermsVariety'
GROUND_LIFT = 0.04

# region-mask window = the expanse ground window (ox -572, oz -256, 512 m square)
RX0, RZ0, RSIZE = -572.0, -256.0, 512.0
OLD = (-104.0, -60.0, -54.0, 48.0)          # old Berms ground footprint x0, x1, z0, z1 (unchanged, keeps V2)


class Field:
    def __init__(self):
        hf = np.load(BX / 'work/heightfield.npz')
        n, cell, ox, oz = hf['grid']
        self.n, self.cell, self.ox, self.oz = int(n), float(cell), float(ox), float(oz)
        self.H = hf['H'].astype(np.float64)
        self.playable = hf['playable']
        self.d_in = hf['d_in'].astype(np.float64)
        self.sky = hf['sky'].astype(np.float64)
        self.sun = hf['sun'].astype(np.float64)
        self.rocks = hf['rocks'].astype(np.float64)
        self.wash = hf['w'].astype(np.float64)

    def ij(self, x, z):
        return (np.asarray(z, float) - self.oz) / self.cell, (np.asarray(x, float) - self.ox) / self.cell

    def sample(self, arr, x, z):
        """Bilinear sample of a field array at world (x, z) (scalars or arrays)."""
        fj, fi = self.ij(x, z)
        j0 = np.clip(np.floor(fj).astype(int), 0, self.n - 2); i0 = np.clip(np.floor(fi).astype(int), 0, self.n - 2)
        tj = np.clip(fj - j0, 0, 1); ti = np.clip(fi - i0, 0, 1)
        a = arr[j0, i0] * (1 - ti) + arr[j0, i0 + 1] * ti
        b = arr[j0 + 1, i0] * (1 - ti) + arr[j0 + 1, i0 + 1] * ti
        return a * (1 - tj) + b * tj

    def ground(self, x, z):
        return self.sample(self.H, x, z) + GROUND_LIFT

    def window(self, x0, z0, size, res):
        """Resample an array window: returns world X, Z grids of res x res cell centres."""
        c = (np.arange(res) + 0.5) * (size / res)
        X, Z = np.meshgrid(x0 + c, z0 + c)
        return X, Z


def sites():
    """Expansion + next-level sites (centre, name, id). Positions as authored; the saved scene is checked by the survey."""
    s = json.loads((BX / 'sites.json').read_text())
    out = [dict(id=x['id'], name=x['name'], centre=x['centre'], waystation=bool(x.get('waystation'))) for x in s['sites']]
    n = json.loads((NL / 'sites.json').read_text())
    out += [dict(id=x.get('id', x['name']), name=x['name'], centre=x['centre'], waystation=False) for x in n['sites']]
    return out


def routes():
    return json.loads((BX / 'sites.json').read_text())['routes']


def survey():
    p = HERE / 'survey.json'
    return json.loads(p.read_text()) if p.exists() else None


def seg_dist(px, pz, ax, az, bx, bz):
    dx, dz = bx - ax, bz - az; L2 = dx * dx + dz * dz
    t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))


def poly_dist(px, pz, pts):
    return min(seg_dist(px, pz, *pts[k], *pts[k + 1]) for k in range(len(pts) - 1))
