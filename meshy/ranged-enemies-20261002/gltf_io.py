"""Minimal GLB reader/writer for the ranged-enemy scripts (numpy only).
GLB(path): .j (JSON), .bin (bytearray), acc(i) -> numpy array (copy), write_acc(i, array) in place (same count/type),
save(path). Node forward kinematics helpers for glTF skeletons (rest TRS + optional per-node overrides)."""
import json, struct
from pathlib import Path
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class GLB:
    def __init__(self, path):
        b = Path(path).read_bytes()
        assert b[:4] == b'glTF', path
        n = struct.unpack('<I', b[12:16])[0]
        self.j = json.loads(b[20:20 + n])
        o = 20 + n
        self.bin = bytearray()
        if o < len(b):
            m = struct.unpack('<I', b[o:o + 4])[0]
            self.bin = bytearray(b[o + 8:o + 8 + m])

    def _view(self, i):
        a = self.j['accessors'][i]; bv = self.j['bufferViews'][a['bufferView']]
        dt = np.dtype(CT[a['componentType']]); nc = NC[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', 0) or dt.itemsize * nc
        return a, dt, nc, off, stride

    def acc(self, i):
        a, dt, nc, off, stride = self._view(i)
        cnt = a['count']
        if stride == dt.itemsize * nc:
            arr = np.frombuffer(bytes(self.bin[off:off + cnt * stride]), dt).reshape(cnt, nc).copy()
        else:
            raw = np.frombuffer(bytes(self.bin[off:off + (cnt - 1) * stride + dt.itemsize * nc]), np.uint8)
            arr = np.stack([np.frombuffer(raw[k * stride:k * stride + dt.itemsize * nc].tobytes(), dt) for k in range(cnt)])
        if a.get('normalized') and dt.kind in 'iu':
            arr = arr.astype(np.float32) / np.iinfo(dt).max
        return arr if nc > 1 else arr[:, 0]

    def write_acc(self, i, values):
        a, dt, nc, off, stride = self._view(i)
        v = np.asarray(values)
        if a.get('normalized') and dt.kind in 'iu':
            v = np.round(np.clip(v, 0, 1) * np.iinfo(dt).max)
        v = v.astype(dt).reshape(a['count'], nc)
        assert stride == dt.itemsize * nc, 'interleaved write not supported'
        self.bin[off:off + v.nbytes] = v.tobytes()
        if 'min' in a and a['type'] != 'SCALAR' or ('min' in a and dt == np.float32):
            a['min'] = v.min(0).tolist() if nc > 1 else [float(v.min())]
            a['max'] = v.max(0).tolist() if nc > 1 else [float(v.max())]

    def save(self, path):
        js = json.dumps(self.j, separators=(',', ':')).encode()
        js += b' ' * ((4 - len(js) % 4) % 4)
        bn = bytes(self.bin) + b'\0' * ((4 - len(self.bin) % 4) % 4)
        self.j.setdefault('buffers', [{}])[0]['byteLength'] = len(self.bin)
        js = json.dumps(self.j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
        total = 12 + 8 + len(js) + (8 + len(bn) if bn else 0)
        out = struct.pack('<4sII', b'glTF', 2, total) + struct.pack('<I4s', len(js), b'JSON') + js
        if bn: out += struct.pack('<I4s', len(bn), b'BIN\0') + bn
        Path(path).write_bytes(out)

    # ---------------------------------------------------------------- skeleton helpers
    def node_index(self, name):
        return next(i for i, n in enumerate(self.j['nodes']) if n.get('name') == name)

    def parents(self):
        p = {}
        for i, n in enumerate(self.j['nodes']):
            for c in n.get('children', []): p[c] = i
        return p


def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


def qinv(q): return np.array([-q[0], -q[1], -q[2], q[3]]) / np.dot(q, q)


def qrot(q, v):
    p = np.array([v[0], v[1], v[2], 0.0])
    return qmul(qmul(q, p), qinv(q))[:3]


def qnorm(q): return q / np.linalg.norm(q)


def q_from_to(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    c = np.cross(a, b); d = float(np.dot(a, b))
    if d < -0.999999:
        ax = np.cross(a, [1, 0, 0]);
        if np.linalg.norm(ax) < 1e-6: ax = np.cross(a, [0, 1, 0])
        ax /= np.linalg.norm(ax); return np.array([ax[0], ax[1], ax[2], 0.0])
    return qnorm(np.array([c[0], c[1], c[2], 1 + d]))


def q_axis_angle(axis, ang):
    axis = np.asarray(axis, float) / np.linalg.norm(axis); s = np.sin(ang / 2)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, np.cos(ang / 2)])


def slerp(a, b, t):
    a = qnorm(a); b = qnorm(b); d = float(np.dot(a, b))
    if d < 0: b = -b; d = -d
    if d > .9995: return qnorm(a + (b - a) * t)
    th = np.arccos(d); return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / np.sin(th)


def trs(n, rot=None, tr=None):
    t = np.array(tr if tr is not None else n.get('translation', [0, 0, 0]), float)
    r = np.array(rot if rot is not None else n.get('rotation', [0, 0, 0, 1]), float)
    s = np.array(n.get('scale', [1, 1, 1]), float)
    return t, r, s


def world(glb, idx, local_rot=None, local_tr=None):
    """World (t, q, s) for node idx; local_rot/local_tr: dict node -> override."""
    par = glb.parents(); chain = []
    i = idx
    while i is not None: chain.append(i); i = par.get(i)
    T, Q, S = np.zeros(3), np.array([0, 0, 0, 1.0]), np.ones(3)
    for i in reversed(chain):
        n = glb.j['nodes'][i]
        t, r, s = trs(n, (local_rot or {}).get(i), (local_tr or {}).get(i))
        T = T + qrot(Q, S * t); Q = qnorm(qmul(Q, r)); S = S * s
    return T, Q, S
