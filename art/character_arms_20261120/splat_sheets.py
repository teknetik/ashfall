#!/usr/bin/env python3
"""CPU-only before/after contact sheets from CharacterArmsPass20261120 --steps dump, without Blender or the GPU
(numpy point-splat renderer: vertices, face centroids and edge midpoints splatted with a z-buffer, Lambert + rim
shading from the face normals). Shape review only. Orthographic, the actor's frame (feet at the origin, Unity +Z forward).
One PNG per actor and view: columns = poses; top row before (blue-grey), bottom row after (warm).
Usage: python3 splat_sheets.py DUMP_DIR OUT_DIR [actor_regex] [views=front,threequarter,back,side] [px_per_m=220]
       python3 splat_sheets.py --crop DUMP_DIR OUT_DIR actor pose_regex view centre_x,centre_y size_m px_per_m
         (close-up of one region, e.g. the hands: before | after side by side)"""
import json, math, os, re, struct, sys, zlib
import numpy as np

YAW = {'front': 0, 'threequarter': 35, 'side': 90, 'back': 180, 'backthreequarter': 145, 'leftthreequarter': -35}


def write_png(path, img):
    h, w, _ = img.shape
    raw = b''.join(b'\x00' + img[y].tobytes() for y in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def load_obj(path):
    vs, fs, kinds, kind = [], [], [], 'body'
    with open(path) as f:
        for line in f:
            if line.startswith('v '):
                p = line.split(); vs.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith('f '):
                p = line.split(); fs.append((int(p[1]) - 1, int(p[2]) - 1, int(p[3]) - 1)); kinds.append(kind)
            elif line.startswith('o '):
                kind = 'prop' if line.split()[1].startswith('prop') else 'body'
    return np.array(vs, np.float32).reshape(-1, 3), np.array(fs, np.int64).reshape(-1, 3), np.array([k == 'prop' for k in kinds])


def points(path, yaw):
    v, f, prop = load_obj(path)
    if len(f) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0, bool)
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)   # Unity winding (clockwise front faces, left-handed)
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    pts = [a, b, c, (a + b + c) / 3, (a + b) / 2, (b + c) / 2, (c + a) / 2, (2 * a + b + c) / 4, (a + 2 * b + c) / 4, (a + b + 2 * c) / 4]
    P = np.concatenate(pts); N = np.concatenate([n] * len(pts)); K = np.concatenate([prop] * len(pts))
    r = math.radians(yaw); cs, sn = math.cos(r), math.sin(r)
    # turn the figure by yaw about +Y (positive = the figure turns its left side away from the camera)
    def rot(X):
        x, y, z = X[:, 0], X[:, 1], X[:, 2]
        return np.stack([x * cs + z * sn, y, -x * sn + z * cs], 1)
    return rot(P), rot(N), K


def render(cells, w_m, h_m, px, origin_x=0.0, origin_y=0.0):
    """cells: list of (P, N, K, dx, dy, tint). Camera on +Z looking -Z (it sees the figures' fronts), x right."""
    W, H = int(w_m * px), int(h_m * px)
    img = np.full((H, W, 3), 236, np.uint8); zb = np.full((H, W), -1e9, np.float32)
    light = np.array([-.45, .6, .65]); light /= np.linalg.norm(light)
    for P, N, K, dx, dy, tint in cells:
        if len(P) == 0:
            continue
        # mirror x: camera on +Z looking back, so the figure's right (+x) appears on the image's left
        sx = ((-(P[:, 0]) + dx - origin_x) * px).astype(np.int64)
        sy = (H - 1 - (P[:, 1] + dy - origin_y) * px).astype(np.int64)
        z = P[:, 2]
        lam = np.clip(N @ light, 0, 1); facing = N[:, 2]
        shade = .35 + .65 * lam
        shade = np.where(facing < 0, shade * .55, shade)
        col = np.where(K[:, None], np.array([70, 72, 78]) * shade[:, None], np.array(tint) * shade[:, None])
        col = np.clip(col, 0, 255).astype(np.uint8)
        order = np.argsort(z)
        for ox in (0, 1):
            for oy in (0, 1):
                x = sx[order] + ox; y = sy[order] + oy
                ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
                xi, yi, zi, ci = x[ok], y[ok], z[order][ok], col[order][ok]
                cur = zb[yi, xi]
                m = zi >= cur
                zb[yi[m], xi[m]] = zi[m]; img[yi[m], xi[m]] = ci[m]
    # light ground line and 10 cm grid ticks for scale
    gy = int(H - 1 - (0 - origin_y) * px)
    return img


def sheet(dump, out, actor_re, views, px):
    index = json.load(open(os.path.join(dump, 'index.json')))
    actors = []
    for e in index:
        if e['actor'] not in actors and (not actor_re or re.search(actor_re, e['actor'])):
            actors.append(e['actor'])
    for actor in actors:
        poses = []
        for e in index:
            if e['actor'] == actor and e['pose'] not in poses:
                poses.append(e['pose'])
        for view in views:
            cells = []
            col = 1.1
            for i, pose in enumerate(poses):
                for row, version in enumerate(('before', 'after')):
                    f = os.path.join(dump, f"{actor}__{pose}__{version}.obj")
                    if not os.path.exists(f):
                        continue
                    P, N, K = points(f, YAW[view])
                    # columns run left to right on the image: image x = -(P.x) + dx, so dx grows with i
                    cells.append((P, N, K, (i + .5) * col, (1 - row) * 2.2 + .05, (150, 160, 178) if version == 'before' else (205, 170, 135)))
            img = render(cells, len(poses) * col, 4.45, px)
            # separator line between the rows
            img[int(img.shape[0] - 1 - 2.22 * px), :] = (180, 60, 60)
            os.makedirs(out, exist_ok=True)
            p = os.path.join(out, f"{actor}__{view}.png")
            write_png(p, img)
            print('wrote', p, poses, flush=True)


def crop(dump, out, actor, pose_re, view, centre, size, px):
    index = json.load(open(os.path.join(dump, 'index.json')))
    poses = []
    for e in index:
        if e['actor'] == actor and re.search(pose_re, e['pose']) and e['pose'] not in poses:
            poses.append(e['pose'])
    cx, cy = centre
    for pose in poses:
        cells = []
        for k, version in enumerate(('before', 'after')):
            f = os.path.join(dump, f"{actor}__{pose}__{version}.obj")
            P, N, K = points(f, YAW[view])
            cells.append((P, N, K, (k + .5) * size - (-cx), 0, (150, 160, 178) if version == 'before' else (205, 170, 135)))
        img = render(cells, 2 * size, size, px, origin_y=cy - size / 2)
        p = os.path.join(out, f"{actor}__{pose}__{view}__crop.png")
        write_png(p, img); print('wrote', p, flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--crop':
        _, dump, out, actor, pose_re, view, c, size, px = a
        os.makedirs(out, exist_ok=True)
        crop(dump, out, actor, pose_re, view, tuple(map(float, c.split(','))), float(size), float(px))
    else:
        dump, out = a[0], a[1]
        sheet(dump, out, a[2] if len(a) > 2 and a[2] else None, (a[3] if len(a) > 3 else 'front,threequarter').split(','), float(a[4]) if len(a) > 4 else 220)
