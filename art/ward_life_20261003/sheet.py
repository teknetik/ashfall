"""Contact sheet of images (Blender, no PIL on this host). Run: blender.sh sheet.py -- out.jpg cols img1 img2 ..."""
import bpy, sys, numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
out, cols, files = a[0], int(a[1]), a[2:]
imgs = []
for f in files:
    im = bpy.data.images.load(f)
    w, h = im.size
    p = np.empty(w * h * 4, np.float32); im.pixels.foreach_get(p); p = p.reshape(h, w, 4)
    imgs.append(p)
TW = 960
tiles = []
for p in imgs:
    h, w = p.shape[:2]
    th = int(TW * h / w)
    yi = (np.arange(th) * h / th).astype(int); xi = (np.arange(TW) * w / TW).astype(int)
    tiles.append(p[yi][:, xi])
TH = max(t.shape[0] for t in tiles)
rows = (len(tiles) + cols - 1) // cols
S = np.zeros((rows * TH, cols * TW, 4), np.float32); S[..., 3] = 1
for i, t in enumerate(tiles):
    r, c = i // cols, i % cols
    y0 = (rows - 1 - r) * TH + (TH - t.shape[0])
    S[y0:y0 + t.shape[0], c * TW:(c + 1) * TW] = t
img = bpy.data.images.new("sheet", S.shape[1], S.shape[0], alpha=True)
img.pixels.foreach_set(S.ravel()); img.filepath_raw = out; img.file_format = "JPEG"; img.save()
