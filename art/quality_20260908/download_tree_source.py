"""Download verified original Poly Haven Jacaranda source and its full 4K inputs."""
import concurrent.futures
import hashlib
import json
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
RECORDS = ROOT / 'refs/quality_20260908/tree'
OUT = RECORDS / 'jacaranda_tree'
OUT.mkdir(parents=True, exist_ok=True)
entry = json.loads((RECORDS / 'jacaranda_tree-files.json').read_text())['blend']['4k']['blend']
jobs = [('jacaranda_tree_4k.blend', entry)] + list(entry['include'].items())

def fetch(job):
    name, record = job
    destination = (OUT / name).resolve()
    assert destination.is_relative_to(OUT.resolve())
    assert urllib.parse.urlparse(record['url']).hostname == 'dl.polyhaven.org'
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or hashlib.md5(destination.read_bytes()).hexdigest() != record['md5']:
        request = urllib.request.Request(record['url'], headers={'User-Agent': 'WardAssetAudit/1.0 (local 3D asset production)'})
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
        assert hashlib.md5(data).hexdigest() == record['md5'], name
        destination.write_bytes(data)
    data = destination.read_bytes()
    result = {'file': name, 'url': record['url'], 'bytes': len(data), 'md5': hashlib.md5(data).hexdigest(), 'sha256': hashlib.sha256(data).hexdigest()}
    print(name, len(data), flush=True)
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    files = list(executor.map(fetch, jobs))
(OUT / 'download-manifest.json').write_text(json.dumps({'asset': 'jacaranda_tree', 'source': 'https://polyhaven.com/a/jacaranda_tree', 'license': 'CC0', 'licenseUrl': 'https://polyhaven.com/license', 'files': files}, indent=2)+'\n')
