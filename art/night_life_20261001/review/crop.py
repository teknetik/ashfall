import sys
from PIL import Image
src, out = sys.argv[1], sys.argv[2]
x0,y0,x1,y1 = map(int, sys.argv[3].split(","))
im = Image.open(src).convert("RGB").crop((x0,y0,x1,y1)); im.save(out); print(im.size)
