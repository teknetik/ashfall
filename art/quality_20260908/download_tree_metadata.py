"""Retain the official CC0 tree candidate metadata for this quality pass."""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'refs/quality_20260908/tree'
OUT.mkdir(parents=True, exist_ok=True)
for asset in ['island_tree_01', 'island_tree_02', 'jacaranda_tree']:
    for route in ['files', 'info']:
        url = f'https://api.polyhaven.com/{route}/{asset}'
        destination = OUT / f'{asset}-{route}.json'
        if destination.exists():
            data = json.loads(destination.read_text())
        else:
            request = urllib.request.Request(url, headers={'User-Agent': 'WardAssetAudit/1.0 (local 3D asset research)', 'Accept': 'application/json'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            destination.write_text(json.dumps(data, indent=2) + '\n')
        if route == 'files':
            for key in ['blend', 'gltf', 'fbx']:
                if key in data:
                    entry = data[key]['4k'][key]
                    print(asset, key, 'bytes', entry['size'] + sum(x['size'] for x in entry['include'].values()))
