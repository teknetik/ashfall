# The other mods against a pistol GLB without Blender: nearest triangle of the pistol for every mod vertex, the side
# it lies on by that triangle's winding, and by ray parity whether it is really inside the part. numpy only.
import json, struct, sys, numpy as np
S = 0.13674

def load(f):
    d = open(f, 'rb').read()
    n, t = struct.unpack('<II', d[12:20]); js = json.loads(d[20:20 + n]); off = 20 + n
    bn, bt = struct.unpack('<II', d[off:off + 8]); return js, d[off + 8:off + 8 + bn]

def acc(js, b, i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    o = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    dt = {5126: 'f4', 5123: 'u2', 5125: 'u4', 5121: 'u1'}[a['componentType']]
    nc = {'VEC3': 3, 'VEC2': 2, 'SCALAR': 1, 'VEC4': 4}[a['type']]
    sz = np.dtype(dt).itemsize * nc; st = bv.get('byteStride', sz)
    if st == sz:
        return np.frombuffer(b, dt, a['count'] * nc, o).reshape(-1, nc).astype(np.float64 if dt == 'f4' else np.int64)
    return np.stack([np.frombuffer(b, dt, nc, o + k * st) for k in range(a['count'])]).astype(np.float64)

def quat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def world(js):
    M = {}
    par = {}
    for i, nd in enumerate(js['nodes']):
        for c in nd.get('children', []):
            par[c] = i
    def loc(i):
        nd = js['nodes'][i]
        m = np.eye(4)
        if 'matrix' in nd:
            return np.array(nd['matrix']).reshape(4, 4).T
        m[:3, :3] = quat(nd.get('rotation', [0, 0, 0, 1])) * np.array(nd.get('scale', [1, 1, 1]))[None, :]
        m[:3, 3] = nd.get('translation', [0, 0, 0])
        return m
    def w(i):
        if i not in M:
            M[i] = (w(par[i]) @ loc(i)) if i in par else loc(i)
        return M[i]
    return [w(i) for i in range(len(js['nodes']))]

def tris_of(f, scale, skip=('card',)):
    js, b = load(f); W = world(js)
    out = {}
    for i, nd in enumerate(js['nodes']):
        if 'mesh' not in nd or any(s in nd.get('name', '') for s in skip):
            continue
        T = []
        for p in js['meshes'][nd['mesh']]['primitives']:
            P = acc(js, b, p['attributes']['POSITION']); I = acc(js, b, p['indices']).reshape(-1, 3).astype(int)
            Pw = (W[i][:3, :3] @ P.T).T + W[i][:3, 3]
            Mm = np.stack([Pw[:, 0], -Pw[:, 2], Pw[:, 1]], 1) * scale * 1000.0          # glTF -> pistol frame, mm
            T.append(Mm[I])
        out[nd['name']] = np.concatenate(T)
    return out

def closest(p, A, B, C):
    ab = B - A; ac = C - A; ap = p - A
    d1 = (ab * ap).sum(1); d2 = (ac * ap).sum(1)
    bp = p - B; d3 = (ab * bp).sum(1); d4 = (ac * bp).sum(1)
    cp = p - C; d5 = (ab * cp).sum(1); d6 = (ac * cp).sum(1)
    vc = d1 * d4 - d3 * d2; vb = d5 * d2 - d1 * d6; va = d3 * d6 - d5 * d4
    den = np.where(np.abs(va + vb + vc) < 1e-30, 1e-30, va + vb + vc)
    v = vb / den; w = vc / den
    q = A + ab * v[:, None] + ac * w[:, None]
    m = (d1 <= 0) & (d2 <= 0); q[m] = A[m]
    m2 = (d3 >= 0) & (d4 <= d3); q[m2] = B[m2]
    m3 = (vc <= 0) & (d1 >= 0) & (d3 <= 0); t = d1 / np.where(d1 - d3 == 0, 1, d1 - d3); q[m3] = (A + ab * t[:, None])[m3]
    m4 = (d6 >= 0) & (d5 <= d6); q[m4] = C[m4]
    m5 = (vb <= 0) & (d2 >= 0) & (d6 <= 0); t = d2 / np.where(d2 - d6 == 0, 1, d2 - d6); q[m5] = (A + ac * t[:, None])[m5]
    m6 = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0); t = (d4 - d3) / np.where((d4 - d3) + (d5 - d6) == 0, 1, (d4 - d3) + (d5 - d6)); q[m6] = (B + (C - B) * t[:, None])[m6]
    return q

def parity(p, A, B, C, d=np.array([0.317, 0.611, 0.725])):
    d = d / np.linalg.norm(d)
    e1 = B - A; e2 = C - A
    h = np.cross(d, e2); a = (e1 * h).sum(1)
    ok = np.abs(a) > 1e-12
    f = 1.0 / np.where(ok, a, 1); s = p - A
    u = f * (s * h).sum(1); q = np.cross(s, e1); v = f * (q @ d); t = f * (e2 * q).sum(1)
    return int(((ok) & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)).sum())

pistol = tris_of(sys.argv[1], 1.0)
mods = tris_of('art/pistol_mods_20260930/export/PistolMods.glb', S, skip=())
names = list(pistol); allT = np.concatenate([pistol[n] for n in names]); owner = np.concatenate([np.full(len(pistol[n]), k) for k, n in enumerate(names)])
A, B, C = allT[:, 0], allT[:, 1], allT[:, 2]
N = np.cross(B - A, C - A); N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-30)
res = {}
for mn in (sys.argv[2:] or sorted(mods)):
    V = np.unique(mods[mn].reshape(-1, 3).round(4), axis=0)
    rows = []
    for p in V:
        q = closest(p, A, B, C); dv = p - q; dist = np.linalg.norm(dv, axis=1)
        k = int(dist.argmin())
        if dist[k] > 0.3 and (dv[k] * N[k]).sum() < 0:
            own = names[owner[k]]
            T = pistol[own]
            rows.append((round(float(dist[k]), 2), own, parity(p, T[:, 0], T[:, 1], T[:, 2]) % 2 == 1, [round(float(x), 1) for x in p]))
    rows.sort(reverse=True)
    by = {}
    for r in rows:
        by['%s inside=%s' % (r[1], r[2])] = by.get('%s inside=%s' % (r[1], r[2]), 0) + 1
    print(mn, 'unique verts', len(V), 'behind the nearest face and over 0.3 mm:', len(rows), by)
    for r in rows[:5]:
        print('    ', r)
