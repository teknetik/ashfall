"""Soffit/jamb profile of both District gate arches at the planes the gate fittings use (from gate_world.obj via
extract_gate_mesh.read_chunk). Writes opening.json: for each arch centre, the minimum soffit height over x 48.30-48.95
at z offsets -2.5..2.5 (0.05 m), and the jamb faces. Run after extract_gate_mesh.py."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_gate_mesh import CHUNKS, read_chunk, tri_slice_x

V, T = [], []
for f in sorted(CHUNKS.glob("Chunk_*_District_gate_*.asset")):
    v, t = read_chunk(f); b = len(V); V += v; T += [(a + b, c + b, d + b) for a, c, d in t]


def slice_segs(x):
    return [s for a, b, c in T if (s := tri_slice_x(V[a], V[b], V[c], x))]


out = {}
XS = [48.30, 48.45, 48.60, 48.75, 48.90, 48.95]
segs = {x: slice_segs(x) for x in XS + [47.05, 47.2]}
for zc in (0.0, 12.0):
    soff = {}
    for i in range(-50, 51):
        dz = i * 0.05
        z = zc + dz
        best = 99.0
        for x in XS:
            for (y0, z0), (y1, z1) in segs[x]:
                if (z0 - z) * (z1 - z) <= 0 and z0 != z1:
                    y = y0 + (z - z0) / (z1 - z0) * (y1 - y0)
                    if y > 1.0:
                        best = min(best, y)
        soff[round(dz, 2)] = round(best, 3)
    jambs = {}
    for yv in (0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 4.6, 5.0):
        lo, hi = -99, 99
        for x in XS + [47.05, 47.2]:
            for (y0, z0), (y1, z1) in segs[x]:
                if (y0 - yv) * (y1 - yv) <= 0 and y0 != y1:
                    z = z0 + (yv - y0) / (y1 - y0) * (z1 - z0)
                    if abs(z - zc) < 3.2:
                        if z < zc: lo = max(lo, z - zc)
                        else: hi = min(hi, z - zc)
        jambs[yv] = [round(lo, 3), round(hi, 3)]
    out[str(zc)] = {"soffit": soff, "jambs": jambs}
    print("arch", zc, "jambs", jambs)
    print("  soffit", [(k, v) for k, v in soff.items() if abs(k * 20) % 5 == 0])
(Path(__file__).resolve().parent / "opening.json").write_text(json.dumps(out, indent=0))
