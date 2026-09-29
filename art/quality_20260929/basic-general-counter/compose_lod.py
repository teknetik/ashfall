"""Compose LOD0 | LOD1 | 8x amplified difference sheets (numpy only)."""
import bpy, numpy as np
from pathlib import Path

R = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter/renders')


def load(p):
    im = bpy.data.images.load(str(p), check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(im)
    return a


def save(a, p):
    h, w = a.shape[:2]
    im = bpy.data.images.new('tmp', w, h, alpha=True)
    im.pixels.foreach_set(a.reshape(-1))
    im.filepath_raw = str(p); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)


for n in ('6m', '12m', '3m_near'):
    a = load(R / f'lod_{n}_lod0.png'); b = load(R / f'lod_{n}_lod1.png')
    d = np.clip(np.abs(a - b) * 8.0, 0, 1); d[..., 3] = 1
    rms = float(np.sqrt(np.mean((a[..., :3] - b[..., :3]) ** 2)))
    print(n, 'rms', round(rms, 5), 'max', round(float(np.abs(a - b)[..., :3].max()), 4))
    save(np.concatenate([a, b, d], axis=1), R / f'compare_lod_{n}.png')
