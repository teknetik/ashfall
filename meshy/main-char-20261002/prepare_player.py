#!/usr/bin/env python3
"""Assemble the runtime player GLB for Carl's main_char_OK (2 Oct 2026) the way unity/tools/prepare_meshy.py did for the
mpc colonist: one mesh/skin (Meshy rig of the decimated LOD0) plus the 'idle' (library Idle 13 / action 252), 'walk'
and 'run' (Meshy basic walking/running) clips, written to Assets/AthenHill/Art/Imported/Meshy/colonist.glb (same path and
GUID, so MeshyPlayer.prefab and ImportMeshyPlayer keep working). The 1k rig-upload textures are replaced by the 2048 px
source base colour and metallic/roughness JPEGs from main_char_OK.glb and the 4096 px normal map baked from the 595k
source (blender/player_normal_4k.png). The eight library clips are also copied to Art/CharacterMotion/Source/Player/
Player_<name>.glb for CharacterFeelPass.RetargetPlayerClips (old copies there came from the 27 Sep colonist rig).
Previous colonist.glb: git blob of HEAD (recorded in previous/README.md) or regenerate with unity/tools/prepare_meshy.py."""
import copy, hashlib, json, shutil, struct, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TARGET = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb'
SOURCE_PLAYER = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/CharacterMotion/Source/Player'
PREFAB = ROOT / 'unity/AthenHill/Assets/AthenHill/Prefabs/MeshyPlayer.prefab'
SRC_CHAR = ROOT / 'meshy/incoming-20261002/main_char_OK.glb'
NORMAL_PNG = HERE / 'blender/player_normal_4k.png'
CLIPS = {'idle': ('idle_252.glb', 0), 'walk': ('basic_walking.glb', 0), 'run': ('basic_running.glb', 0)}
LIBRARY = ['idle_252', 'aim_95', 'rifleturn_573', 'lower_334', 'aimturn_585', 'left_528', 'back_233', 'fwd_234']


def read(path):
    raw = path.read_bytes()
    size = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20 + size]), raw[28 + size:]


def write(path, doc, binary):
    doc['buffers'] = [{'byteLength': len(binary)}]
    encoded = json.dumps(doc, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary = bytes(binary) + b'\0' * (-len(binary) % 4)
    path.write_bytes(struct.pack('<III', 0x46546C67, 2, 28 + len(encoded) + len(binary))
                     + struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
                     + struct.pack('<II', len(binary), 0x004E4942) + binary)


def append_view(doc, binary, data):
    binary.extend(b'\0' * (-len(binary) % 4))
    doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)})
    binary.extend(data)
    return len(doc['bufferViews']) - 1


def image_bytes(doc, binary, index):
    view = doc['bufferViews'][doc['images'][index]['bufferView']]
    off = view.get('byteOffset', 0)
    return binary[off:off + view['byteLength']]


def main():
    rec = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    # previous version record
    prev = HERE / 'previous'; prev.mkdir(exist_ok=True)
    blob = subprocess.run(['git', 'rev-parse', 'HEAD:unity/AthenHill/Assets/AthenHill/Art/Imported/Meshy/colonist.glb'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if TARGET.exists():
        rec['previous_colonist_sha256'] = hashlib.sha256(TARGET.read_bytes()).hexdigest(); rec['previous_colonist_git_blob'] = blob
    if PREFAB.exists() and not (prev / 'MeshyPlayer.prefab.before').exists(): shutil.copy(PREFAB, prev / 'MeshyPlayer.prefab.before')
    doc, data = read(HERE / 'rigged.glb')
    binary = bytearray(data)
    doc['animations'] = []
    names = {node['name']: i for i, node in enumerate(doc['nodes'])}
    for name, (file, index) in CLIPS.items():
        source, buffer = read(HERE / file)
        assert source['skins'] == doc['skins'], 'Skeleton mismatch ' + file
        assert [n['name'] for n in source['nodes']] == [n['name'] for n in doc['nodes']], 'Node mismatch ' + file
        clip = copy.deepcopy(source['animations'][index]); clip['name'] = name
        mapped = {}
        for sampler in clip['samplers']:
            for field in ('input', 'output'):
                old = sampler[field]
                if old not in mapped:
                    accessor = copy.deepcopy(source['accessors'][old])
                    view = source['bufferViews'][accessor['bufferView']]
                    off = view.get('byteOffset', 0)
                    accessor['bufferView'] = append_view(doc, binary, buffer[off:off + view['byteLength']])
                    accessor.pop('byteOffset', None)
                    mapped[old] = len(doc['accessors']); doc['accessors'].append(accessor)
                sampler[field] = mapped[old]
        for channel in clip['channels']:
            channel['target']['node'] = names[source['nodes'][channel['target']['node']]['name']]
        doc['animations'].append(clip)
        rec.setdefault('clips', {})[name] = {'source': file, 'meshy_name': source['animations'][index].get('name'), 'seconds': max(doc['accessors'][s['input']]['max'][0] for s in clip['samplers'])}
    # textures: material roles -> full-resolution images
    mat = doc['materials'][0]
    src_doc, src_bin = read(SRC_CHAR)
    src_mat = src_doc['materials'][0]
    def src_image(tex_ref): return image_bytes(src_doc, src_bin, src_doc['textures'][tex_ref['index']]['source'])
    roles = {'base': (mat['pbrMetallicRoughness']['baseColorTexture'], src_image(src_mat['pbrMetallicRoughness']['baseColorTexture']), 'image/jpeg'),
             'metallicRoughness': (mat['pbrMetallicRoughness']['metallicRoughnessTexture'], src_image(src_mat['pbrMetallicRoughness']['metallicRoughnessTexture']), 'image/jpeg'),
             'normal': (mat['normalTexture'], NORMAL_PNG.read_bytes(), 'image/png')}
    for role, (ref, bytes_, mime) in roles.items():
        image = doc['images'][doc['textures'][ref['index']]['source']]
        image['bufferView'] = append_view(doc, binary, bytes_); image['mimeType'] = mime; image['name'] = 'player_' + role
        rec.setdefault('textures', {})[role] = {'bytes': len(bytes_), 'mime': mime}
    mat['name'] = 'PlayerMainChar'
    for t in doc['textures']: t.setdefault('sampler', 0)
    doc.setdefault('samplers', [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}])
    doc['asset']['extras'] = {'ward': 'main_char_OK LOD0 59,999 tris, Meshy rig 01a0fd2b, idle 252 + basic walk/run; see meshy/main-char-20261002/README.md'}
    # drop the orphaned 1k image views? glTF keeps them in the buffer; rebuild the binary without unreferenced image views for size
    write(TARGET, doc, binary)
    rec['target'] = str(TARGET.relative_to(ROOT)); rec['target_bytes'] = TARGET.stat().st_size; rec['target_sha256'] = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    pr = doc['meshes'][0]['primitives'][0]
    rec['mesh'] = {'triangles': doc['accessors'][pr['indices']]['count'] // 3, 'vertices': doc['accessors'][pr['attributes']['POSITION']]['count'], 'joints': len(doc['skins'][0]['joints'])}
    # library clip sources for the retarget
    SOURCE_PLAYER.mkdir(parents=True, exist_ok=True)
    for name in LIBRARY:
        dst = SOURCE_PLAYER / f'Player_{name}.glb'
        shutil.copy(HERE / f'{name}.glb', dst); rec.setdefault('library_sources', []).append(dst.name)
    (HERE / 'prepare.json').write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec, indent=2))


if __name__ == '__main__':
    main()
