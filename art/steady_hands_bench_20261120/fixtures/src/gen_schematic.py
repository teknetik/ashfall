#!/usr/bin/env python3
"""The schematic sheet's drawing (fixtures_schematic): 1000 x 1200 px for a 250 x 300 mm sheet (4 px/mm), white paper,
black ink. Eight regions (stages s0 to s7) in two columns of four, each with its number where the wax-pencil ring goes
(fx_m3.region_centre). An optional sketch image (--sketch PNG, e.g. an image-model drawing of the grip exploded) is laid
under the frames; without it each region gets a simple line sketch (placeholder).
    python3 fixtures/src/gen_schematic.py [--sketch sketch.png] -> fixtures/src/gen/schematic.png"""
import os, subprocess, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'gen', 'schematic.png')
PX = 4000.0
STAGES = ['LAY OUT', 'STRIP PISTOL', 'OPEN SERVO', 'WORK PARTS', 'FUSE CORE', 'ASSEMBLE GRIP', 'FIT GRIP', 'TEST']


def rc(i):
    col, row = i % 2, i // 2
    return (-0.060 + 0.120 * col, -0.068 - 0.064 * row)


def px(x, y):
    return (x + 0.125) * PX, -y * PX


def main():
    sketch = sys.argv[sys.argv.index('--sketch') + 1] if '--sketch' in sys.argv else None
    d = []
    # title strip and border
    d += ['-stroke', 'black', '-strokewidth', '3', '-fill', 'none', '-draw', 'rectangle 18,18 982,1182']
    d += ['-strokewidth', '2', '-draw', 'line 18,140 982,140']
    d += ['-stroke', 'none', '-fill', 'black', '-font', '/usr/share/fonts/noto/NotoSansMono-Bold.ttf', '-pointsize', '40', '-annotate', '+40+78', 'GRIP, STABILISED']
    d += ['-font', '/usr/share/fonts/noto/NotoSansMono-Regular.ttf', '-pointsize', '24', '-annotate', '+40+118', 'scrap pistol  /  servo gimbal damper  /  B. bench']
    d += ['-pointsize', '22', '-annotate', '+760+78', 'SHEET 1 OF 1']
    for i in range(8):
        cx, cy = rc(i)
        x0, y0 = px(cx - 0.057, cy + 0.029); x1, y1 = px(cx + 0.057, cy - 0.029)
        d += ['-stroke', 'black', '-strokewidth', '2', '-fill', 'none', '-draw', 'rectangle %d,%d %d,%d' % (x0, y0, x1, y1)]
        nx, ny = px(cx - 0.044, cy + 0.017)
        d += ['-stroke', 'none', '-fill', 'black', '-font', '/usr/share/fonts/noto/NotoSansMono-Bold.ttf', '-pointsize', '44', '-annotate', '+%d+%d' % (nx - 13, ny + 16), str(i)]
        d += ['-font', '/usr/share/fonts/noto/NotoSansMono-Regular.ttf', '-pointsize', '20', '-annotate', '+%d+%d' % (nx + 30, ny + 8), STAGES[i]]
        if not sketch and not os.path.exists(os.path.join(HERE, '..', 'sheets', 'schematic', 's%d.jpg' % i)):
            # placeholder line sketch: a part outline and an arrow in each region
            sx, sy = px(cx + 0.005, cy - 0.005)
            d += ['-stroke', 'black', '-strokewidth', '2', '-fill', 'none',
                  '-draw', 'roundrectangle %d,%d %d,%d 10,10' % (sx - 60, sy - 30, sx + 40, sy + 40),
                  '-draw', 'circle %d,%d %d,%d' % (sx - 10, sy + 5, sx + 8, sy + 5),
                  '-draw', 'line %d,%d %d,%d' % (sx + 60, sy - 40, sx + 120, sy - 40),
                  '-draw', 'line %d,%d %d,%d' % (sx + 120, sy - 40, sx + 110, sy - 46),
                  '-draw', 'line %d,%d %d,%d' % (sx + 120, sy - 40, sx + 110, sy - 34)]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = ['magick', '-size', '1000x1200', 'xc:white']
    # per-region sketches (fixtures/sheets/schematic/s<i>.jpg, Grok image route): fitted under each region's label
    sk = os.path.join(HERE, '..', 'sheets', 'schematic')
    for i in range(8):
        f = os.path.join(sk, 's%d.jpg' % i)
        if not os.path.exists(f):
            continue
        cx, cy = rc(i)
        x0, y0 = px(cx - 0.057, cy + 0.029); x1, y1 = px(cx + 0.057, cy - 0.029)
        w, h = int(x1 - x0 - 16), int(y1 - y0 - 72)
        base += ['(', f, '-colorspace', 'gray', '-level', '25%,88%', '-fuzz', '8%', '-trim', '+repage', '-resize', '%dx%d' % (w, h),
                 '-background', 'white', '-gravity', 'center', '-extent', '%dx%d' % (w, h), ')',
                 '-gravity', 'NorthWest', '-geometry', '+%d+%d' % (int(x0 + 8), int(y0 + 64)), '-compose', 'multiply', '-composite']
        sketch = sketch or f
    base += ['-compose', 'over', '-gravity', 'NorthWest']
    subprocess.check_call(base + d + ['-colorspace', 'gray', OUT])
    print('wrote', OUT)


if __name__ == '__main__':
    main()
