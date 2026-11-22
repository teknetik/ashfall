"""Three-view sheet -> Rodin inputs, cut in the empty gaps between the figures (equal thirds cut through the hands).
uv run --offline --with pillow python panels.py NAME [VERSION]"""
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter
H = Path(__file__).resolve().parent
n = sys.argv[1]; v = sys.argv[2] if len(sys.argv) > 2 else 'v1'
im = Image.open(H / f'{n}_sheet_{v}.png').convert('RGB')
W0, T0 = im.size
im = im.crop((0, int(T0 * (.032 if n in ('linn', 'brann', 'ossa') else 0)), W0, T0))  # only those sheets have an empty top strip
W, T = im.size
sm = im.resize((700, int(700 * T / W))).filter(ImageFilter.GaussianBlur(1))
w, h = sm.size
px = sm.load()
# background: the mean of both side margins on that row
def content(x):
    c = 0
    for y in range(int(h * .02), int(h * .86)):        # above the feet, whose floor shadows fill the gaps
        l, r = px[3, y], px[w - 4, y]
        t = x / w
        c += sum(abs(px[x, y][i] - (l[i] * (1 - t) + r[i] * t)) for i in range(3)) > 48
    return c
score = [content(x) for x in range(w)]
on = [s > 1 for s in score]
runs = []; x = 0
while x < w:
    if on[x]:
        a = x
        while x < w and on[x]: x += 1
        runs.append([a, x])
    x += 1
while len(runs) > 3:
    g = min(range(len(runs) - 1), key=lambda i: runs[i + 1][0] - runs[i][1]); runs[g][1] = runs[g + 1][1]; del runs[g + 1]
assert len(runs) == 3, runs
cut = [0, (runs[0][1] + runs[1][0]) // 2, (runs[1][1] + runs[2][0]) // 2, w]
out = H / n; out.mkdir(exist_ok=True)
width = max(b - a for a, b in runs) * 1.14 * W / w
row = []
for i, p in enumerate(('front', 'side', 'back')):
    a, b = cut[i] * W // w, cut[i + 1] * W // w
    part = im.crop((a, 0, b, T))
    pad = Image.new('RGB', (int(max(width, b - a)), T), im.getpixel((8, T // 3)))
    pad.paste(part, ((pad.width - part.width) // 2, 0))
    pad = pad.resize((int(pad.width * 2000 / T), 2000))
    pad.save(out / f'panel_{p}.png'); row.append(pad)
prev = Image.new('RGB', (sum(p.width + 12 for p in row), 2000), 'white'); x = 0
for p in row: prev.paste(p, (x, 0)); x += p.width + 12
prev.resize((prev.width * 700 // 2000, 700)).save(out / 'panels_preview.jpg')
print(n, runs, cut)
