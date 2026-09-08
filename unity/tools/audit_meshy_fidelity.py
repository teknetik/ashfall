"""Inspect retained Meshy sources without importing, modifying, or downsampling them."""
import hashlib
import io
import json
import struct
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'unity/evidence/fidelity/20260908'

def glb(path):
    raw = path.read_bytes()
    assert raw[:4] == b'glTF'
    size = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20 + size])
    binary = raw[28 + size:]
    images = []
    for item in doc.get('images', []):
        if 'bufferView' not in item:
            continue
        view = doc['bufferViews'][item['bufferView']]
        start = view.get('byteOffset', 0)
        data = binary[start:start + view['byteLength']]
        with Image.open(io.BytesIO(data)) as image:
            images.append({'name': item.get('name'), 'size': list(image.size),
                           'sha256': hashlib.sha256(data).hexdigest()})
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(),
            'triangles': sum(doc['accessors'][p['indices']]['count'] // 3
                             for mesh in doc['meshes'] for p in mesh['primitives']),
            'images': images, 'materials': doc.get('materials', []),
            'attributes': [list(p['attributes']) for m in doc['meshes'] for p in m['primitives']]}

assets = []
for pattern in ['meshy/**/*.glb', 'unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/**/*.glb']:
    for path in sorted(ROOT.glob(pattern)):
        assets.append(glb(path))
texture_sizes = []
for path in sorted((ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy').rglob('*')):
    if path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
        with Image.open(path) as image:
            texture_sizes.append({'path': str(path.relative_to(ROOT)), 'size': list(image.size)})
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'source-audit.json').write_text(json.dumps({'models': assets, 'textures': texture_sizes}, indent=2) + '\n')
for a in assets:
    print(f"{a['triangles']:>6} triangles  {a['path']}")
print(f'Inspected {len(assets)} GLBs and {len(texture_sizes)} images; source-audit.json saved.')
