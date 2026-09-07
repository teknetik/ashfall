"""Combine supplied Meshy geometry and compatible clips without duplicating textures."""
import copy
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'meshy/mpc'
TARGET = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb'

def read(path):
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20 + size]), raw[28 + size:]

def main():
    doc, data = read(SOURCE / 'Meshy_AI_Character_output.glb')
    binary = bytearray(data)
    doc['animations'][0]['name'] = 'idle'
    names = {node['name']: i for i, node in enumerate(doc['nodes'])}
    for file, name in [('Meshy_AI_Animation_Walking_withSkin.glb', 'walk'),
                       ('Meshy_AI_Animation_Running_withSkin.glb', 'run')]:
        source, buffer = read(SOURCE / file)
        assert source['skins'] == doc['skins'], 'Skeleton mismatch'
        clip = copy.deepcopy(source['animations'][0])
        clip['name'] = name
        mapped = {}
        for sampler in clip['samplers']:
            for field in ('input', 'output'):
                old = sampler[field]
                if old not in mapped:
                    accessor = copy.deepcopy(source['accessors'][old])
                    view = copy.deepcopy(source['bufferViews'][accessor['bufferView']])
                    offset = view.get('byteOffset', 0)
                    binary.extend(b'\0' * (-len(binary) % 4))
                    view['byteOffset'] = len(binary)
                    binary.extend(buffer[offset:offset + view['byteLength']])
                    accessor['bufferView'] = len(doc['bufferViews'])
                    doc['bufferViews'].append(view)
                    mapped[old] = len(doc['accessors'])
                    doc['accessors'].append(accessor)
                sampler[field] = mapped[old]
        for channel in clip['channels']:
            channel['target']['node'] = names[source['nodes'][channel['target']['node']]['name']]
        doc['animations'].append(clip)
    doc['buffers'] = [{'byteLength': len(binary)}]
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary.extend(b'\0' * (-len(binary) % 4))
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(binary))
                      + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
                      + struct.pack('<II', len(binary), 0x004E4942) + binary)
    print(f'Wrote {TARGET} ({TARGET.stat().st_size:,} bytes, one mesh/texture set, idle/walk/run)')

if __name__ == '__main__':
    main()
