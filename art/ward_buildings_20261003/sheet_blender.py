"""Contact sheet without PIL (round two): blender.sh sheet_blender.py -- out.png img1 img2 ... (2 columns, 960 px tiles)."""
import bpy, sys, numpy as np, os
args = sys.argv[sys.argv.index("--") + 1:]
out, fs = args[0], args[1:]
W, H = 960, 540
tiles = []
for f in fs:
    im = bpy.data.images.load(f)
    im.scale(W, H)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)
    tiles.append(a)
rows = (len(tiles) + 1) // 2
sheet = np.zeros((rows * H, 2 * W, 4), dtype=np.float32)
sheet[..., 3] = 1
for i, t in enumerate(tiles):
    r, c = i // 2, i % 2
    y0 = (rows - 1 - r) * H          # Blender images are bottom-up
    sheet[y0:y0 + H, c * W:(c + 1) * W] = t
img = bpy.data.images.new("sheet", 2 * W, rows * H, alpha=False)
img.pixels = sheet.ravel()
img.filepath_raw = out
img.file_format = "JPEG" if out.endswith(".jpg") else "PNG"
img.save()
print("sheet", out, [os.path.basename(f) for f in fs])
