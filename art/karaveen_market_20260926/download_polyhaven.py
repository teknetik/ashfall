"""Download CC0 Poly Haven props (glTF, 1k maps) used as Karaveen market goods."""
import json, urllib.request, hashlib, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT = Path(__file__).parent / 'sources' / 'polyhaven'
ASSETS = ['food_apple_01','food_pomegranate_01','food_lime_01','lemon','yellow_onion','sweet_potato','food_ginger_01',
 'food_avocado_01','wicker_basket_01','wicker_basket_02','ceramic_vase_01','ceramic_vase_02','ceramic_vase_03','ceramic_vase_04',
 'planter_pot_clay','jug_01','brass_pot_01','brass_pot_02','brass_vase_03','brass_vase_04','metal_jerrycan_green','plastic_jerrycan',
 'can_rusted','russian_food_cans_01','wooden_crate_01','wooden_crate_02','wooden_bucket_01','barrel_03','barrel_stove','wooden_lantern_01',
 'folding_wooden_stool','wooden_stool_02','hatchet','sledgehammer_01','rusted_hacksaw','pipe_wrench','adjustable_wrench','old_gas_mask',
 'propane_tank','carved_wooden_plate','wooden_bowl_02','pot_enamel_01','ammo_box','old_military_crate','long_life_food','metal_jug',
 'crowbar_01','rusted_spade_01','binoculars','plastic_bottle_gallon','cardboard_box_01','wooden_barrels_01','small_oil_can_01']
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'WardAssetProduction/1.0 (local 3D asset production)'})
    with urllib.request.urlopen(req, timeout=120) as r: return r.read()
def fetch(asset):
    d = OUT / asset; d.mkdir(parents=True, exist_ok=True)
    files = json.loads(get(f'https://api.polyhaven.com/files/{asset}'))
    info = json.loads(get(f'https://api.polyhaven.com/info/{asset}'))
    gltf = files['gltf']['1k']['gltf']
    out = []
    items = [('', gltf)] + list(gltf.get('include', {}).items())
    for rel, row in items:
        name = rel or gltf['url'].split('/')[-1]
        p = d / name; p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or hashlib.md5(p.read_bytes()).hexdigest() != row['md5']: p.write_bytes(get(row['url']))
        assert hashlib.md5(p.read_bytes()).hexdigest() == row['md5'], name
        out.append(dict(file=name, url=row['url'], md5=row['md5']))
    return dict(asset=asset, source=f'https://polyhaven.com/a/{asset}', license='CC0', authors=info.get('authors'), polycount=info.get('polycount'), gltf=gltf['url'].split('/')[-1], files=out)
with ThreadPoolExecutor(8) as ex: manifest = list(ex.map(fetch, ASSETS))
(OUT.parent / 'polyhaven-manifest.json').write_text(json.dumps(manifest, indent=2))
print(len(manifest), 'assets')
