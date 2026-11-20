"""CPU software render of the first-person dumps (RifleHandsPass20261120 --steps dump), for when the Blender slot is
held by a running player. Camera at the origin looking +Z (Unity camera space), vertical FOV from camera.json, flat
Lambert shading, z-buffer; arms skin-coloured, armour olive, weapon grey. Shape and framing only.
Usage: python3 render_soft.py DUMP_DIR OUT_DIR [states...]  (writes <state>_fp_soft.png and _fp_armour_soft.png)"""
import json, os, sys, zlib, struct
import numpy as np

W, H = 960, 540


def png(path, img):
    raw = b''.join(b'\x00' + img[y].tobytes() for y in range(img.shape[0]))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', img.shape[1], img.shape[0], 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def load(path):
    objs, v, name, faces = [], [], None, []
    for line in open(path):
        if line.startswith('v '):
            v.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('f '):
            faces.append([int(t) - 1 for t in line.split()[1:4]])
        elif line.startswith('o '):
            if name: objs.append((name, faces))
            name, faces = line.split()[1], []
    if name: objs.append((name, faces))
    return np.array(v, np.float64), objs


def render(path, out, vfov, armour):
    V, objs = load(path)
    f = (H / 2) / np.tan(np.radians(vfov) / 2)
    zb = np.full((H, W), np.inf); img = np.zeros((H, W, 3), np.uint8); img[:] = (168, 158, 144)
    light = np.array([-.4, .7, -.55]); light /= np.linalg.norm(light)
    cols = {'arms': np.array([200, 140, 110]), 'armour': np.array([80, 88, 62]), 'weapon': np.array([150, 150, 156])}
    for name, faces in objs:
        kind = name.split('_')[0]
        if kind == 'armour' and not armour: continue
        F = np.array(faces); P = V[F]                      # (n,3,3)
        nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]); ln = np.linalg.norm(nrm, axis=1) + 1e-12; nrm /= ln[:, None]
        keep = (P[:, :, 2] > .01).all(1)
        P, nrm = P[keep], nrm[keep]
        sx = W / 2 + f * P[:, :, 0] / P[:, :, 2]; sy = H / 2 - f * P[:, :, 1] / P[:, :, 2]
        shade = np.abs(nrm @ light) * .75 + .25
        base = cols.get(kind, cols['weapon'])
        for i in range(len(P)):
            x0, x1 = int(max(0, np.floor(sx[i].min()))), int(min(W - 1, np.ceil(sx[i].max())))
            y0, y1 = int(max(0, np.floor(sy[i].min()))), int(min(H - 1, np.ceil(sy[i].max())))
            if x0 > x1 or y0 > y1: continue
            xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
            (ax, bx, cx), (ay, by, cy) = sx[i], sy[i]
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-9: continue
            l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / d
            l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / d
            l3 = 1 - l1 - l2
            m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
            if not m.any(): continue
            iz = l1 / P[i, 0, 2] + l2 / P[i, 1, 2] + l3 / P[i, 2, 2]
            z = 1 / np.where(m, iz, 1e-9)
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            w = m & (z < sub)
            sub[w] = z[w]
            img[y0:y1 + 1, x0:x1 + 1][w] = (base * shade[i]).astype(np.uint8)
    png(out, img)
    print('wrote', out, flush=True)


if __name__ == '__main__':
    dump, outdir = sys.argv[1], sys.argv[2]
    states = sys.argv[3:] or ['rifle_hip', 'rifle_ads', 'rifle_burst', 'rifle_walk', 'rifle_sprint', 'rifle_lowered', 'pistol_hip', 'pistol_ads']
    os.makedirs(outdir, exist_ok=True)
    vfov = json.load(open(os.path.join(dump, 'camera.json')))['vfov']
    for st in states:
        p = os.path.join(dump, st + '.obj')
        if not os.path.exists(p): print('missing', p); continue
        for armour in (False, True):
            render(p, os.path.join(outdir, f"{st}_fp{'_armour' if armour else ''}_soft.png"), vfov, armour)
