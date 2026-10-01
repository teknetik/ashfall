"""Analyse floor_tiles_04: course rows and joint columns from the displacement map."""
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
P = 'polyhaven/floor_tiles_04/'
disp = np.asarray(Image.open(P + 'floor_tiles_04_disp_4k.png')).astype(np.float32)
if disp.ndim == 3: disp = disp[..., 0]
disp /= disp.max()
print('disp', disp.shape, disp.min(), disp.max(), disp.mean())
# row profile: mean height per row; joints are low rows
rows = disp.mean(1); cols = disp.mean(0)
lo = np.argsort(rows)[:60]
print('lowest rows', sorted(lo.tolist()))
# joint mask: below local threshold
thr = np.percentile(disp, 6)
print('thr', thr)
jm = disp < thr
print('joint fraction', jm.mean())
rowfrac = jm.mean(1)
cand = np.where(rowfrac > 0.5)[0]
print('rows mostly joint', cand.tolist())
Image.fromarray((jm * 255).astype(np.uint8)).resize((1024, 1024)).save('review/src_jointmask.png')
Image.fromarray((disp * 255).astype(np.uint8)).resize((1024, 1024)).save('review/src_disp.png')
