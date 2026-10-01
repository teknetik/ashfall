import sys
from PIL import Image
src, out, w = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert("RGB"); print(src, im.size)
im.thumbnail((w, w)); im.save(out)
