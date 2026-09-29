"""Side-by-side comparison of two lookbook runs (matched camera/hour names).

  uv run --offline --with pillow python unity/tools/compare_lookbooks.py BEFORE AFTER OUT [--width 960] [--filter cam_hill]

Writes OUT/<name>.jpg (before | after, labelled) for every capture present in both runs, and OUT/index.json with the
frame-time profiles of both runs.
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    p = argparse.ArgumentParser(); p.add_argument('before', type=Path); p.add_argument('after', type=Path); p.add_argument('out', type=Path)
    p.add_argument('--width', type=int, default=960); p.add_argument('--filter', default='')
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    names = sorted(x.stem for x in a.before.glob('cam_*.png') if (a.after / x.name).exists() and a.filter in x.stem)
    w = a.width; h = w * 9 // 16
    for n in names:
        sheet = Image.new('RGB', (w * 2, h + 24), (18, 18, 18)); d = ImageDraw.Draw(sheet)
        for i, (label, folder) in enumerate([('BEFORE', a.before), ('AFTER', a.after)]):
            with Image.open(folder / (n + '.png')) as im: sheet.paste(im.convert('RGB').resize((w, h), Image.LANCZOS), (i * w, 24))
            d.text((i * w + 8, 6), '%s  %s' % (label, n), fill=(235, 220, 190))
        sheet.save(a.out / (n + '.jpg'), quality=90)
    prof = {k: json.loads((f / 'lookbook.json').read_text()).get('profiles', {}) for k, f in [('before', a.before), ('after', a.after)]}
    (a.out / 'index.json').write_text(json.dumps(dict(before=str(a.before), after=str(a.after), images=names, profiles=prof), indent=1))
    print(len(names), 'comparisons ->', a.out)


if __name__ == '__main__':
    main()
