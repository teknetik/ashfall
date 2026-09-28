"""Download CC0 Poly Haven surface maps for the Ward district retrofit kit (MD5-checked)."""
import json, urllib.request, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT = Path(__file__).parent / 'sources' / 'textures'
SETS = {'blue_metal_plate': '2k', 'metal_plate_02': '2k', 'green_metal_rust': '2k', 'rusty_painted_metal': '2k',
        'container_side': '2k', 'factory_wall': '2k', 'concrete_wall_008': '2k', 'rebar_reinforced_concrete': '2k',
        'metal_grate_rusty': '2k', 'corrugated_iron_02': '2k', 'worn_corrugated_iron': '2k', 'rusty_metal_sheet': '2k',
        'painted_metal_shutter': '2k', 'ribbed_concrete_wall': '2k', 'cracked_concrete_wall': '2k', 'rusty_metal_04': '2k',
        'concrete_debris': '2k', 'metal_plate': '2k'}
MAPS = ['Diffuse', 'nor_gl', 'Rough', 'Metal', 'AO']
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'WardAssetProduction/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r: return r.read()
def fetch(item):
    asset, res = item
    files = json.loads(get(f'https://api.polyhaven.com/files/{asset}'))
    d = OUT / asset; d.mkdir(parents=True, exist_ok=True); rows = []
    for m in MAPS:
        if m not in files or res not in files[m]: continue
        row = files[m][res]['jpg']; p = d / row['url'].split('/')[-1]
        if not p.exists(): p.write_bytes(get(row['url']))
        assert hashlib.md5(p.read_bytes()).hexdigest() == row['md5'], p
        rows.append(dict(map=m, file=p.name, url=row['url'], md5=row['md5']))
    return dict(asset=asset, source=f'https://polyhaven.com/a/{asset}', license='CC0', maps=rows)
with ThreadPoolExecutor(8) as ex: manifest = list(ex.map(fetch, SETS.items()))
(OUT.parent / 'texture-manifest.json').write_text(json.dumps(manifest, indent=2)); print('ok', sum(len(m['maps']) for m in manifest))
