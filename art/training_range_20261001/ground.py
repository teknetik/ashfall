"""Ground height sampler from survey.json (Berms ground mesh raycast grid, 0.5 m) and the range frame."""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
S = json.loads((HERE / "survey.json").read_text())
X0, X1, Z0, Z1 = S["window"]; ST = S["gridStep"]
NX = int(round((X1 - X0) / ST)) + 1; NZ = int(round((Z1 - Z0) / ST)) + 1
_g = np.array([p[2] for p in S["grid"]], float).reshape(NZ, NX)
_top = np.array([p[3] for p in S["grid"]], float).reshape(NZ, NX)


def _bil(A, x, z):
    i = (x - X0) / ST; j = (z - Z0) / ST
    i0 = min(max(int(math.floor(i)), 0), NX - 2); j0 = min(max(int(math.floor(j)), 0), NZ - 2)
    fi = i - i0; fj = j - j0
    return float(A[j0, i0] * (1 - fi) * (1 - fj) + A[j0, i0 + 1] * fi * (1 - fj) + A[j0 + 1, i0] * (1 - fi) * fj + A[j0 + 1, i0 + 1] * fi * fj)


def ground(x, z):
    """Berms ground surface height (world y) at (x, z)."""
    return _bil(_g, x, z)


def top(x, z):
    """Highest non-trigger collider surface (ground, apron, props with colliders)."""
    return _bil(_top, x, z)


# range frame: firing line origin F (the checkpoint_firingline landmark), facing yaw -63 deg (down range, WNW)
F = (-66.2, 7.6)
YAW = -63.0
_t = math.radians(YAW)
FWD = (math.sin(_t), math.cos(_t))
RIGHT = (math.cos(_t), -math.sin(_t))


def W(fwd, lat):
    """World (x, z) of a point fwd metres down range and lat metres to the right of F."""
    return (F[0] + fwd * FWD[0] + lat * RIGHT[0], F[1] + fwd * FWD[1] + lat * RIGHT[1])


def L(x, z):
    """(fwd, lat) of a world point."""
    dx, dz = x - F[0], z - F[1]
    return (dx * FWD[0] + dz * FWD[1], dx * RIGHT[0] + dz * RIGHT[1])
