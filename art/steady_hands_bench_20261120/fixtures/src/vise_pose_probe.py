#!/usr/bin/env python3
"""vise_pose_probe.py: the pistol at a pose in the vise, by numbers, without Blender (model-bench).
Reads ../pistol/export/pistol.glb (rest pose, rigid nodes), puts the frame node at a pose given in the vise's own
frame and reports what is between the pads, the gap the jaws need, and where the grip parts stand.
  python3 fixtures/src/vise_pose_probe.py            # the poses in POSES below"""
import json, struct, os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.abspath(os.path.join(HERE, '..', '..'))


def read_glb(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 12)[0]
    js = json.loads(b[20:20 + n]); rest = b[20 + n:]
    return js, rest


def acc(js, rest, idx):
    a = js['accessors'][idx]; bv = js['bufferViews'][a['bufferView']]
    k = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
    off = 8 + bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    if stride and stride != 4 * k:
        raw = np.frombuffer(rest, dtype=np.uint8, count=stride * a['count'], offset=off).reshape(a['count'], stride)[:, :4 * k]
        return np.frombuffer(raw.tobytes(), dtype=np.float32).reshape(a['count'], k)
    return np.frombuffer(rest, dtype=np.float32, count=a['count'] * k, offset=off).reshape(a['count'], k)


def local(n):
    if 'matrix' in n:
        return np.array(n['matrix'], dtype=float).reshape(4, 4).T
    t = n.get('translation', [0, 0, 0]); q = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1])
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R @ np.diag(s); M[:3, 3] = t
    return M


def load(path, prefix):
    js, rest = read_glb(path)
    nodes = js['nodes']; W = {}

    def walk(i, P):
        W[i] = P @ local(nodes[i])
        for c in nodes[i].get('children', []):
            walk(c, W[i])
    for r in js['scenes'][js.get('scene', 0)]['nodes']:
        walk(r, np.eye(4))
    out = {}
    for i, n in enumerate(nodes):
        if 'mesh' not in n or not n.get('name', '').startswith(prefix) or i not in W:
            continue
        vs = [acc(js, rest, p['attributes']['POSITION']) for p in js['meshes'][n['mesh']]['primitives']]
        v = np.vstack(vs).astype(float)
        vw = (W[i] @ np.c_[v, np.ones(len(v))].T).T
        out[n['name']] = (vw[:, :3], W[i])                 # glTF world (Y up)
    return out


Y2Z = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float)       # glTF axes -> Blender axes


def T(p):
    M = np.eye(4); M[:3, 3] = p; return M


def R(axis, deg):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    M = np.eye(4)
    i, j = {'x': (1, 2), 'y': (2, 0), 'z': (0, 1)}[axis]
    M[i, i] = c; M[j, j] = c; M[i, j] = -s; M[j, i] = s
    return M


PAD_HALF, PAD_Z = 0.042, (0.1095, 0.1356)
SKIP = ('pistol_card_a', 'pistol_card_b', 'pistol_cell')
GRIP = ('pistol_scale_l', 'pistol_scale_r', 'pistol_wrap', 'pistol_housing', 'pistol_housing_pin', 'pistol_screw_grip_a', 'pistol_screw_grip_b', 'pistol_bind_wire_a', 'pistol_bind_wire_b')


def report(P, name, M):
    Fi = Y2Z @ np.linalg.inv(P['pistol_frame'][1])        # into the frame node's own space, in Blender's axes
    ys, grip_lo, grip_x = [], 9.0, [9.0, -9.0]
    who = {}
    for n, (vw, _) in P.items():
        if n in SKIP:
            continue
        v = (M @ Fi @ np.c_[vw, np.ones(len(vw))].T).T[:, :3]
        m = (np.abs(v[:, 0]) <= PAD_HALF) & (v[:, 2] >= PAD_Z[0]) & (v[:, 2] <= PAD_Z[1])
        if m.any():
            ys += list(v[m, 1]); who[n] = (round(float(v[m, 1].min()) * 1000, 2), round(float(v[m, 1].max()) * 1000, 2))
        if n in GRIP:
            grip_lo = min(grip_lo, float(v[:, 2].min())); grip_x = [min(grip_x[0], float(v[:, 0].min())), max(grip_x[1], float(v[:, 0].max()))]
    ys = np.array(ys)
    print(name)
    print('  between the pads (y mm, fixed pad face at 0):', who)
    print('  highest y %.2f mm (must be under 0), jaw gap needed %.2f mm, jaw value %.4f' % (ys.max() * 1000, (-0.00006 - ys.min()) * 1000, 1 - (-0.00006 - ys.min()) / 0.090))
    print('  grip parts: lowest %.1f mm (pad tops at 135.6), x %.1f .. %.1f mm in the vise frame' % (grip_lo * 1000, grip_x[0] * 1000, grip_x[1] * 1000))


if __name__ == '__main__':
    P = load(os.path.join(PROG, 'pistol', 'export', 'pistol.glb'), 'pistol_')
    POSES = {'as built 20:30: T(-30, -18.0, 190.7) Ry(180)': T((-0.030, -0.0180, 0.1907)) @ R('y', 180),
             'mirrored, grip toward the bench centre: T(30, -18.0, 190.7) Rx(180)': T((0.030, -0.0180, 0.1907)) @ R('x', 180)}
    for k, M in POSES.items():
        report(P, k, M)
