"""Download CC0 Poly Haven surface maps (1k/2k JPG) for the Blender-built stall structures."""
import json, urllib.request, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT = Path(__file__).parent / 'sources' / 'textures'
SETS = {'weathered_planks':'2k','rusty_corrugated_iron':'2k','hessian_230':'1k','rough_linen':'1k','dirty_carpet':'1k',
        'fabric_pattern_05':'1k','fabric_pattern_07':'1k','rusty_metal_02':'1k','brown_leather':'1k','rough_wood':'1k'}
MAPS = ['Diffuse','nor_gl','Rough']
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'WardAssetProduction/1.0'})
    with urllib.request.urlopen(req, timeout=120) as r: return r.read()
def fetch(item):
    asset, res = item
    files = json.loads(get(f'https://api.polyhaven.com/files/{asset}'))
    d = OUT / asset; d.mkdir(parents=True, exist_ok=True); rows = []
    for m in MAPS:
        if m not in files: continue
        row = files[m][res]['jpg']; p = d / row['url'].split('/')[-1]
        if not p.exists(): p.write_bytes(get(row['url']))
        assert hashlib.md5(p.read_bytes()).hexdigest() == row['md5']
        rows.append(dict(map=m, file=p.name, url=row['url']))
    return dict(asset=asset, source=f'https://polyhaven.com/a/{asset}', license='CC0', maps=rows)
with ThreadPoolExecutor(8) as ex: manifest = list(ex.map(fetch, SETS.items()))
(OUT.parent / 'texture-manifest.json').write_text(json.dumps(manifest, indent=2)); print('ok')
