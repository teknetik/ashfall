"""Small shared helpers for the north avenue buildings (30 September 2026)."""
import bmesh
from mathutils import Vector


def corrugated_sheet(part, xa, xb, a, b, mat, pitch=0.076, amp=0.018, t=0.005, lod=0):
    """Continuous trapezoidal corrugated sheet across x in [xa, xb], running from a = (y, z) to b = (y, z) along its fall
    line. Top and underside surfaces, closed at all four edges (no slits when seen from below)."""
    step = pitch / 4 if lod == 0 else pitch / 2
    xs, hs = [], []
    x, k = xa, 0
    pattern = [0.0, amp, amp, 0.0] if lod == 0 else [0.0, amp]
    while x < xb - 1e-6:
        xs.append(x)
        hs.append(pattern[k % len(pattern)])
        x += step
        k += 1
    xs.append(xb)
    hs.append(pattern[k % len(pattern)])
    bm = part.bm
    mi = part.mi(mat)
    (ya, za), (yb, zb) = a, b

    def row(y0, z0, off):
        return [bm.verts.new(Vector((xx, y0 + h + off, z0))) for xx, h in zip(xs, hs)]
    ta, tb = row(ya, za, 0.0), row(yb, zb, 0.0)
    ba, bb = row(ya, za, -t), row(yb, zb, -t)
    fs = []
    n = len(xs)
    for i in range(n - 1):
        fs.append(bm.faces.new([ta[i], ta[i + 1], tb[i + 1], tb[i]]))       # top
        fs.append(bm.faces.new([ba[i], bb[i], bb[i + 1], ba[i + 1]]))       # underside
        fs.append(bm.faces.new([ta[i], ba[i], ba[i + 1], ta[i + 1]]))       # edge at a
        fs.append(bm.faces.new([tb[i], tb[i + 1], bb[i + 1], bb[i]]))       # edge at b
    fs.append(bm.faces.new([ta[0], tb[0], bb[0], ba[0]]))
    fs.append(bm.faces.new([ta[-1], ba[-1], bb[-1], tb[-1]]))
    for f in fs:
        f.material_index = mi
    bmesh.ops.recalc_face_normals(bm, faces=fs)
    return fs
