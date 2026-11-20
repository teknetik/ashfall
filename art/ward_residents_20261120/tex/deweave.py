"""Removes the periodic crosshatch ("canvas weave") that Meshy's texture model baked into the residents' skin (20 Nov 2026).

Mask: the base-colour atlas texels covered by the LOD0 triangles whose vertices are skinned mainly to the head, neck,
hands, fingers and forearms, AND skin-coloured (YCbCr skin range), feathered. Cloth elsewhere keeps its weave.
Filter: overlapping 128 px tiles (Hann window, 50 % overlap), per tile and channel the FFT magnitude in the band of
periods 2.5-32 px is compared with a smooth (radially median) reference; peaks above `k` times the reference are cut back
to it (phase kept). Overlap-added, then blended into the original only through the mask.
Usage: python3 deweave.py <rigged_fixed.glb> <out_base_colour.png> [k]   (numpy only; image IO through ImageMagick)."""
import json, struct, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

LIMIT = 18.0   # largest change of a texel channel (0-255)
SKIN_BONES = ('Head', 'neck', 'head_end', 'headfront', 'Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Pinky', 'ForeArm')


def glb(path):
    b = Path(path).read_bytes(); jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl + 8
    return j, b, o


def acc(j, b, o, i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
    n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[a['componentType']]
    st = o + v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride')
    cnt = a['count']
    if stride and stride != n * np.dtype(dt).itemsize:
        raw = np.frombuffer(b[st:st + stride * cnt], np.uint8).reshape(cnt, stride)[:, :n * np.dtype(dt).itemsize]
        arr = raw.copy().view(dt).reshape(cnt, n)
    else:
        arr = np.frombuffer(b[st:st + cnt * n * np.dtype(dt).itemsize], dt).reshape(cnt, n)
    if a.get('normalized') and dt != np.float32: arr = arr.astype(np.float32) / np.iinfo(dt).max
    return arr


def image_bytes(j, b, o, idx):
    im = j['images'][idx]; v = j['bufferViews'][im['bufferView']]
    return b[o + v.get('byteOffset', 0):o + v.get('byteOffset', 0) + v['byteLength']]


def load_rgb(data, tmp):
    src = Path(tmp) / 'src.img'; src.write_bytes(data)
    w, h = map(int, subprocess.check_output(['magick', 'identify', '-format', '%w %h', str(src)]).split())
    raw = subprocess.check_output(['magick', str(src), '-depth', '8', 'rgb:-'])
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)


def raster_mask(uv, tris, size):
    """Coverage of the given UV triangles at texel resolution (glTF UV: v down from the top)."""
    m = np.zeros((size, size), np.uint8)
    P = uv * size
    for t in tris:
        a, b_, c = P[t[0]], P[t[1]], P[t[2]]
        x0, x1 = int(max(0, np.floor(min(a[0], b_[0], c[0])))), int(min(size - 1, np.ceil(max(a[0], b_[0], c[0]))))
        y0, y1 = int(max(0, np.floor(min(a[1], b_[1], c[1])))), int(min(size - 1, np.ceil(max(a[1], b_[1], c[1]))))
        if x1 < x0 or y1 < y0: continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        d = (b_[1] - c[1]) * (a[0] - c[0]) + (c[0] - b_[0]) * (a[1] - c[1])
        if abs(d) < 1e-9: continue
        l1 = ((b_[1] - c[1]) * (xs - c[0]) + (c[0] - b_[0]) * (ys - c[1])) / d
        l2 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        inside = (l1 >= -.02) & (l2 >= -.02) & (1 - l1 - l2 >= -.02)
        m[y0:y1 + 1, x0:x1 + 1] |= inside.astype(np.uint8)
    return m


def box_blur(a, r):
    if r <= 0: return a
    k = 2 * r + 1
    c = np.cumsum(np.pad(a, ((r + 1, r), (0, 0)), mode='edge'), 0); a = (c[k:] - c[:-k]) / k
    c = np.cumsum(np.pad(a, ((0, 0), (r + 1, r)), mode='edge'), 1); return (c[:, k:] - c[:, :-k]) / k


def deweave(img, mask, k=2.2, T=128):
    h, w, _ = img.shape; step = T // 2
    win = np.outer(np.hanning(T), np.hanning(T)).astype(np.float32)
    fy = np.fft.fftfreq(T)[:, None]; fx = np.fft.fftfreq(T)[None, :]; rad = np.sqrt(fx ** 2 + fy ** 2)
    band = (rad >= 1 / 32) & (rad <= 1 / 2.5)
    rbin = np.minimum((rad * T).astype(int), T // 2)
    out = np.zeros_like(img); wsum = np.zeros((h, w), np.float32); changed = 0
    for y in range(0, h - T + 1, step):
        for x in range(0, w - T + 1, step):
            if mask[y:y + T, x:x + T].max() == 0: continue
            for ch in range(3):
                tile = img[y:y + T, x:x + T, ch]; mean = tile.mean()
                F = np.fft.fft2((tile - mean) * win); mag = np.abs(F)
                ref = np.zeros_like(mag)
                for r in range(T // 2 + 1):
                    sel = rbin == r
                    if sel.any(): ref[sel] = np.median(mag[sel])
                peak = band & (mag > k * ref)
                if peak.any():
                    F[peak] *= (ref[peak] / np.maximum(mag[peak], 1e-6)); changed += int(peak.sum())
                out[y:y + T, x:x + T, ch] += np.real(np.fft.ifft2(F)) + mean * win
            wsum[y:y + T, x:x + T] += win
    filt = np.where(wsum[..., None] > 1e-3, out / np.maximum(wsum[..., None], 1e-3), img)
    return filt, changed


def main():
    src, dst = sys.argv[1], sys.argv[2]; k = float(sys.argv[3]) if len(sys.argv) > 3 else 2.2
    j, b, o = glb(src)
    prim = j['meshes'][0]['primitives'][0]; at = prim['attributes']
    uv = acc(j, b, o, at['TEXCOORD_0']); jo = acc(j, b, o, at['JOINTS_0']).astype(int); we = acc(j, b, o, at['WEIGHTS_0'])
    idx = acc(j, b, o, prim['indices']).reshape(-1, 3)
    names = [j['nodes'][n].get('name', '') for n in j['skins'][0]['joints']]
    skin_joint = np.array([any(s in nm for s in SKIN_BONES) for nm in names])
    vskin = (we * skin_joint[jo]).sum(1) > .5
    tris = idx[vskin[idx].all(1)]
    tex = j['pbrMetallicRoughness'] if False else j['materials'][prim.get('material', 0)]['pbrMetallicRoughness']['baseColorTexture']['index']
    with tempfile.TemporaryDirectory(dir=str(Path(dst).parent)) as tmp:
        img = load_rgb(image_bytes(j, b, o, j['textures'][tex]['source']), tmp)
        h, w, _ = img.shape
        cover = raster_mask(uv, tris, w)
        R, G, B = img[..., 0], img[..., 1], img[..., 2]
        Y = .299 * R + .587 * G + .114 * B; Cb = 128 - .168736 * R - .331264 * G + .5 * B; Cr = 128 + .5 * R - .418688 * G - .081312 * B
        skin = (Cb > 77) & (Cb < 132) & (Cr > 133) & (Cr < 180) & (Y > 40)
        m = (cover.astype(bool) & skin).astype(np.float32)
        mask = np.clip(box_blur(box_blur(m, 3), 3) * 1.6, 0, 1)
        filt, changed = deweave(img, (mask > .01).astype(np.uint8), k)
        # ringing at atlas-chart borders (black gaps, other cloth) gave isolated specks: limit the change per texel
        filt = img + np.clip(filt - img, -LIMIT, LIMIT)
        res = img * (1 - mask[..., None]) + filt * mask[..., None]
        res = np.clip(np.round(res), 0, 255).astype(np.uint8)
        raw = Path(tmp) / 'out.rgb'; raw.write_bytes(res.tobytes())
        subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '8', f'rgb:{raw}', dst], check=True)
        mp = Path(dst).with_name(Path(dst).stem + '_mask.png'); (Path(tmp) / 'm.gray').write_bytes((mask * 255).astype(np.uint8).tobytes())
        subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '8', f'gray:{Path(tmp) / "m.gray"}', '-resize', '1024x1024', str(mp)], check=True)
    print(json.dumps({'src': src, 'dst': dst, 'size': [w, h], 'skinTriangles': int(len(tris)), 'maskTexels': int((m > 0).sum()),
                      'maskShare': round(float(m.mean()), 4), 'peaksCut': changed, 'k': k}))


main()
