"""Download CC0 Poly Haven props (glTF, 1k maps) used as Ward district retrofit props."""
import json, urllib.request, hashlib, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
OUT = Path(__file__).parent / 'sources' / 'polyhaven'
ASSETS = ['exterior_aircon_unit','modular_airduct_circular_01','modular_airduct_rectangular_01','modular_electric_cables',
 'modular_electricity_poles','modular_industrial_pipes_01','modular_pipes','modular_metal_gutter','modular_fire_escape',
 'modular_chainlink_fence','concrete_road_barrier','concrete_road_barrier_02','metal_trash_can','old_tyre','industrial_wall_lamp',
 'industrial_caged_sconce','security_light','security_camera_01','utility_box_01','utility_box_02','power_box_01','portable_generator',
 'old_military_compressor','small_lpg_tank','propane_tank','metal_jerrycan','plastic_crate_03','industrial_pastic_container','rusted_wheel_rim_01',
 'barrel_03','Barrel_01','Barrel_02','hand_truck','metal_toolbox','portable_welding_cart','wooden_military_crate','old_military_crate','cement_bag',
 'planter_box_01','planter_box_02','planter_box_03','potted_plant_01','potted_plant_02','shrub_01','shrub_02','cheiridopsis_succulent','crystalline_iceplant',
 'rollershutter_door','rollershutter_window_01','water_manhole_cover','ladder_sectioned_01','cardboard_box_01']
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
