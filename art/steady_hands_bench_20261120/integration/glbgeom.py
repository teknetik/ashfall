#!/usr/bin/env python3
"""Steady Hands bench, integration: GLB geometry for the numbers checks (numpy only, no Unity, no Blender).
Read a GLB's nodes and triangles with world transforms; closest points and ray casts on a triangle soup.
Used by hand_check.py and enclosure.py."""
import json, math, struct
import numpy as np

# ------------------------------------------------------------------ GLB
def read_glb(path):
    with open(path, 'rb') as f:
        magic, _, _ = struct.unpack('<4sII', f.read(12)); assert magic == b'glTF', path
        jl, _ = struct.unpack('<II', f.read(8)); js = json.loads(f.read(jl))
        rest = f.read(8); blob = b''
        if len(rest) == 8: bl, _ = struct.unpack('<II', rest); blob = f.read(bl)
    return js, blob

def accessor(js, blob, i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a['componentType']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0); item = np.dtype(dt).itemsize * n
    stride = bv.get('byteStride', item)
    raw = np.frombuffer(blob, dtype=np.uint8, count=stride * (a['count'] - 1) + item, offset=off)
    if stride == item: return np.frombuffer(raw.tobytes(), dtype=dt).reshape(a['count'], n)
    return np.stack([np.frombuffer(raw[k * stride:k * stride + item].tobytes(), dtype=dt) for k in range(a['count'])])

def trs(n):
    if 'matrix' in n: return np.array(n['matrix'], dtype=float).reshape(4, 4).T
    t = np.array(n.get('translation', [0, 0, 0]), float); q = n.get('rotation', [0, 0, 0, 1]); s = np.array(n.get('scale', [1, 1, 1]), float)
    x, y, z, w = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4); m[:3, :3] = r * s; m[:3, 3] = t
    return m

class Model:
    def __init__(self, path):
        self.path = path; self.js, self.blob = read_glb(path)
        nodes = self.js['nodes']; self.world = {}; self.byname = {}
        parent = {c: i for i, n in enumerate(nodes) for c in n.get('children', [])}
        def world(i):
            if i not in self.world: self.world[i] = (world(parent[i]) if i in parent else np.eye(4)) @ trs(nodes[i])
            return self.world[i]
        for i, n in enumerate(nodes): world(i); self.byname[n.get('name', str(i))] = i

    def local_tris(self, name, opaque_only=False):
        """Triangles of a node's mesh in the node's own frame (glTF units/axes of the file); opaque_only leaves out
        primitives whose material blends (glass)."""
        n = self.js['nodes'][self.byname[name]]; out = []
        mats = self.js.get('materials', [])
        for p in self.js['meshes'][n['mesh']]['primitives']:
            if p.get('mode', 4) != 4: continue
            if opaque_only and 'material' in p and mats[p['material']].get('alphaMode') == 'BLEND': continue
            v = accessor(self.js, self.blob, p['attributes']['POSITION']).astype(float)
            idx = accessor(self.js, self.blob, p['indices']).astype(np.int64).reshape(-1, 3) if 'indices' in p else np.arange(len(v)).reshape(-1, 3)
            out.append(v[idx])
        return np.concatenate(out) if out else np.zeros((0, 3, 3))

    def tris(self, name, matrix=None, opaque_only=False):
        t = self.local_tris(name, opaque_only); m = self.world[self.byname[name]] if matrix is None else matrix
        return t @ m[:3, :3].T + m[:3, 3]

    def verts(self, name):
        n = self.js['nodes'][self.byname[name]]; out = []
        for p in self.js['meshes'][n['mesh']]['primitives']:
            out.append(accessor(self.js, self.blob, p['attributes']['POSITION']).astype(float))
        v = np.concatenate(out); m = self.world[self.byname[name]]
        return v @ m[:3, :3].T + m[:3, 3]

    def mesh_nodes(self):
        return [n.get('name', str(i)) for i, n in enumerate(self.js['nodes']) if 'mesh' in n]

# ------------------------------------------------------------------ geometry
class Surface:
    """Triangles in P mm, with a uniform grid for closest-point queries and a ray cast."""
    def __init__(self, tris_mm, h=4.0):
        self.t = np.asarray(tris_mm, float); self.h = h
        lo = self.t.min(1); hi = self.t.max(1)
        self.lo = lo; self.hi = hi; self.grid = {}
        a = np.floor(lo / h).astype(int); b = np.floor(hi / h).astype(int)
        for k in range(len(self.t)):
            for i in range(a[k, 0], b[k, 0] + 1):
                for j in range(a[k, 1], b[k, 1] + 1):
                    for l in range(a[k, 2], b[k, 2] + 1):
                        self.grid.setdefault((i, j, l), []).append(k)
        e1 = self.t[:, 1] - self.t[:, 0]; e2 = self.t[:, 2] - self.t[:, 0]
        n = np.cross(e1, e2); ln = np.linalg.norm(n, axis=1); ln[ln == 0] = 1; self.n = n / ln[:, None]

    def _cands(self, c, k):
        out = set()
        for i in range(c[0] - k, c[0] + k + 1):
            for j in range(c[1] - k, c[1] + k + 1):
                for l in range(c[2] - k, c[2] + k + 1):
                    out.update(self.grid.get((i, j, l), ()))
        return np.fromiter(out, int) if out else np.zeros(0, int)

    def closest(self, p):
        """Closest point on the surface to p: (distance, point, signed distance by the face normal, triangle).
        The grid answers within 16 mm; anything farther is a brute-force pass over every triangle."""
        p = np.asarray(p, float); c = tuple(np.floor(p / self.h).astype(int))
        for k in (1, 2, 4):
            idx = self._cands(c, k)
            if len(idx):
                q = closest_on_tris(p, self.t[idx]); d = np.linalg.norm(q - p, axis=1); m = int(np.argmin(d))
                if d[m] <= k * self.h: break
        else:
            idx = np.arange(len(self.t)); q = closest_on_tris(p, self.t); d = np.linalg.norm(q - p, axis=1); m = int(np.argmin(d))
        tri = idx[m]; s = float(np.dot(p - q[m], self.n[tri]))
        return float(d[m]), q[m], math.copysign(float(d[m]), s) if d[m] > 1e-9 else 0.0, int(tri)

    def hits(self, o, d):
        """Every hit along the ray o + t d (t > 0)."""
        o = np.asarray(o, float); d = np.asarray(d, float) / np.linalg.norm(d)
        v0 = self.t[:, 0]; e1 = self.t[:, 1] - v0; e2 = self.t[:, 2] - v0
        pv = np.cross(d, e2); det = np.einsum('ij,ij->i', e1, pv); ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0); tv = o - v0
        u = np.einsum('ij,ij->i', tv, pv) * inv; qv = np.cross(tv, e1)
        v = (qv @ d) * inv; t = np.einsum('ij,ij->i', e2, qv) * inv
        return np.sort(t[ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)])

    def inside(self, p):
        """In the metal? Odd crossings along three skew rays, by majority (the meshes are many closed shells)."""
        votes = sum(len(self.hits(p, d)) % 2 for d in ((.31, .82, .48), (-.7, .2, .69), (.1, -.9, -.42)))
        return votes >= 2

    def signed(self, p):
        """Distance to the surface, negative in the metal (sign by ray parity, not by the face normal)."""
        d = self.closest(p)[0]; return -d if self.inside(p) else d

    def ray(self, o, d):
        """First hit along the ray o + t d (t > 0): t or None."""
        o = np.asarray(o, float); d = np.asarray(d, float) / np.linalg.norm(d)
        v0 = self.t[:, 0]; e1 = self.t[:, 1] - v0; e2 = self.t[:, 2] - v0
        pv = np.cross(d, e2); det = np.einsum('ij,ij->i', e1, pv); ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0); tv = o - v0
        u = np.einsum('ij,ij->i', tv, pv) * inv; qv = np.cross(tv, e1)
        v = (qv @ d) * inv; t = np.einsum('ij,ij->i', e2, qv) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
        return float(t[hit].min()) if hit.any() else None

def closest_on_tris(p, T):
    """Closest point to p on each triangle of T (n, 3, 3): Ericson, Real-Time Collision Detection 5.1.5, vectorised."""
    a, b, c = T[:, 0], T[:, 1], T[:, 2]
    ab, ac, ap = b - a, c - a, p - a
    d1 = np.einsum('ij,ij->i', ab, ap); d2 = np.einsum('ij,ij->i', ac, ap)
    bp = p - b; d3 = np.einsum('ij,ij->i', ab, bp); d4 = np.einsum('ij,ij->i', ac, bp)
    cp = p - c; d5 = np.einsum('ij,ij->i', ab, cp); d6 = np.einsum('ij,ij->i', ac, cp)
    vc = d1 * d4 - d3 * d2; vb = d5 * d2 - d1 * d6; va = d3 * d6 - d5 * d4
    with np.errstate(divide='ignore', invalid='ignore'):
        den = va + vb + vc; v = vb / den; w = vc / den
        res = a + ab * v[:, None] + ac * w[:, None]
        # edge regions
        m = (va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0)
        wbc = (d4 - d3) / ((d4 - d3) + (d5 - d6)); res = np.where(m[:, None], b + (c - b) * wbc[:, None], res)
        m = (vb <= 0) & (d2 >= 0) & (d6 <= 0); w2 = d2 / (d2 - d6); res = np.where(m[:, None], a + ac * w2[:, None], res)
        m = (vc <= 0) & (d1 >= 0) & (d3 <= 0); v2 = d1 / (d1 - d3); res = np.where(m[:, None], a + ab * v2[:, None], res)
    # vertex regions (last, so they win)
    res = np.where(((d6 >= 0) & (d5 <= d6))[:, None], c, res)
    res = np.where(((d3 >= 0) & (d4 <= d3))[:, None], b, res)
    res = np.where(((d1 <= 0) & (d2 <= 0))[:, None], a, res)
    bad = ~np.isfinite(res).all(1)
    if bad.any(): res[bad] = a[bad]
    return res

