#!/usr/bin/env python3
"""Fetch CC0 Poly Haven rock textures for the variety pass's outcrops (2k JPG: diffuse, GL normal, ARM) into
polyhaven/<id>/ with polyhaven/manifest.json (authors, CC0, real-world size). Pattern of art/berms_road_20261001."""
import json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent / 'polyhaven'
IDS = sys.argv[1:] or ['rock_face_03', 'cliff_side']
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'AthenHill-asset-fetch/1.0'}), timeout=120) as r: return r.read()
man = json.loads((ROOT / 'manifest.json').read_text()) if (ROOT / 'manifest.json').exists() else {}
for aid in IDS:
    files = json.loads(get(f'https://api.polyhaven.com/files/{aid}')); info = json.loads(get(f'https://api.polyhaven.com/info/{aid}'))
    d = ROOT / aid; d.mkdir(parents=True, exist_ok=True); maps = {}
    for key in ['Diffuse', 'nor_gl', 'arm']:
        f = files[key]['2k'].get('jpg') or files[key]['2k'].get('png')
        (d / Path(f['url']).name).write_bytes(get(f['url'])); maps[key] = Path(f['url']).name
    man[aid] = dict(name=info['name'], authors=info['authors'], license='CC0', source=f'https://polyhaven.com/a/{aid}', dimensions_mm=info.get('dimensions'), maps=maps)
(ROOT / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n'); print(json.dumps(man, indent=1))
