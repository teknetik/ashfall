"""Validate exported GLB buffers and exact PBR conversion without operating Unity."""
from pathlib import Path
import hashlib, json, struct
import numpy as np
from PIL import Image

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/quality_20260908/platform-terminals'
SOURCE = ROOT / 'meshy/platform-terminals-20260908/source/terminal_textures'
TYPES = {5120: '<i1', 5121: '<u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect(path):
    raw = path.read_bytes()
    assert struct.unpack_from('<4sII', raw) == (b'glTF', 2, len(raw))
    chunks, at = {}, 12
    while at < len(raw):
        size, kind = struct.unpack_from('<II', raw, at)
        chunks[kind] = raw[at + 8:at + 8 + size]
        at += 8 + size
    doc, data = json.loads(chunks[0x4e4f534a]), chunks[0x004e4942]

    def accessor(index):
        a = doc['accessors'][index]
        assert 'sparse' not in a
        v = doc['bufferViews'][a['bufferView']]
        dtype = np.dtype(TYPES[a['componentType']])
        width = WIDTHS[a['type']]
        stride = v.get('byteStride', dtype.itemsize * width)
        offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        last = offset + max(0, a['count'] - 1) * stride + dtype.itemsize * width
        assert last <= len(data)
        values = np.ndarray((a['count'], width), dtype=dtype, buffer=data,
                            offset=offset, strides=(stride, dtype.itemsize))
        assert np.isfinite(values).all()
        return values

    triangles, vertices, attributes = 0, 0, []
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            assert primitive.get('mode', 4) == 4
            values = {name: accessor(index) for name, index in primitive['attributes'].items()}
            assert 'POSITION' in values and 'NORMAL' in values
            if 'lod' in path.stem:
                assert 'TEXCOORD_0' in values
            count = len(values['POSITION'])
            assert all(len(v) == count for v in values.values())
            indices = accessor(primitive['indices'])
            assert indices.size % 3 == 0 and indices.max() < count
            triangles += indices.size // 3
            vertices += count
            attributes.append(sorted(values))
    return {'path': str(path.relative_to(ROOT)), 'sha256': digest(path),
            'triangles': triangles, 'vertices': vertices, 'attributes': attributes,
            'finite_attributes': True, 'indices_in_range': True,
            'materials_external': not doc.get('materials'), 'bytes': len(raw)}

meshes = [inspect(OUT / f'terminal-lod{i}.glb') for i in range(3)]
meshes += [inspect(OUT / 'terminal-gasket.glb')]
assert [x['triangles'] for x in meshes] == [295588, 74238, 19794, 288]
textures = []
for original, output in [('base_color.png', 'BaseColor.png'), ('normal.png', 'Normal.png')]:
    assert digest(SOURCE / original) == digest(OUT / 'textures' / output)
    textures.append({'path': output, 'size': list(Image.open(OUT / 'textures' / output).size),
                     'byte_identical_to_original_png': True, 'sha256': digest(OUT / 'textures' / output)})
packed = np.asarray(Image.open(OUT / 'textures/MetalSmooth.png').convert('RGBA'))
assert np.array_equal(packed[:, :, 0], np.asarray(Image.open(SOURCE / 'metallic.png').convert('L')))
assert np.array_equal(packed[:, :, 3], 255 - np.asarray(Image.open(SOURCE / 'roughness.png').convert('L')))
assert np.count_nonzero(packed[:, :, 1:3]) == 0
textures.append({'path': 'MetalSmooth.png', 'size': list(packed.shape[1::-1]),
                 'exact_metallic_R_inverse_roughness_A': True,
                 'sha256': digest(OUT / 'textures/MetalSmooth.png')})
report = {'meshes': meshes, 'textures': textures,
          'limitation': 'Buffer validity and conversion evidence only; native shading, LOD transitions and access remain to be tested.'}
(OUT / 'buffer-validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
