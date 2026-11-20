#!/usr/bin/env python3
"""Hero base: slim copy of a Meshy clip GLB for Art/CharacterMotion/Source/Player (numpy; no Blender, no round trip).
The Meshy animation GLBs carry the full 150k-triangle mesh and three 4K textures (34 MB each). The game's retarget
(CharacterFeelPass.Retarget) only needs the skeleton, the skin's bind matrices and the animation, so this keeps:
  * every node, the skin (inverse bind matrices byte-identical) and the animation (keyframe bytes identical),
  * every Nth triangle of the mesh as a proxy (positions, normals, joints, weights; vertices compacted),
and drops materials, textures and images. The root node is renamed `Armature` and the mesh node `char1`.
Usage: slim_clip.py in.glb out.glb [every=60]"""
import json, struct, sys
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read(path):
    b = open(path, 'rb').read(); assert b[:4] == b'glTF'
    jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
    bl = struct.unpack('<I', b[o:o + 4])[0]; assert b[o + 4:o + 8] == b'BIN\x00'
    return j, b[o + 8:o + 8 + bl]


def get(j, binary, i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]; assert 'sparse' not in a
    dt = np.dtype(CT[a['componentType']]); n = NC[a['type']]; off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride') or dt.itemsize * n
    if stride == dt.itemsize * n:
        return np.frombuffer(binary, dt, a['count'] * n, off).reshape(a['count'], n).copy()
    raw = np.frombuffer(binary, np.uint8, a['count'] * stride, off).reshape(a['count'], stride)[:, :dt.itemsize * n]
    return np.ascontiguousarray(raw).view(dt).reshape(a['count'], n).copy()


def slim(src, dst, every=60):
    j, binary = read(src)
    out = bytearray(); views = []; accs = []

    def put(arr, typ, comp, minmax=False, target=None):
        while len(out) % 4: out.append(0)
        data = np.ascontiguousarray(arr, CT[comp]).tobytes()
        v = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data)}
        if target: v['target'] = target
        out.extend(data); views.append(v)
        a = {'bufferView': len(views) - 1, 'componentType': comp, 'count': int(arr.shape[0]), 'type': typ}
        if minmax: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
        accs.append(a); return len(accs) - 1

    def keep(i):   # copy an accessor unchanged (bind matrices, key times, key values)
        a = j['accessors'][i]; arr = get(j, binary, i)
        k = put(arr if NC[a['type']] > 1 else arr[:, 0] if False else arr, a['type'], a['componentType'])
        for key in ('min', 'max', 'normalized'):
            if key in a: accs[k][key] = a[key]
        return k

    prim = j['meshes'][0]['primitives'][0]; at = prim['attributes']
    idx = get(j, binary, prim['indices'])[:, 0].astype(np.int64).reshape(-1, 3)[::every]
    used, inv = np.unique(idx.ravel(), return_inverse=True)
    new_idx = inv.reshape(-1, 1).astype(np.uint16 if len(used) < 65536 else np.uint32)
    pos = get(j, binary, at['POSITION'])[used]; nor = get(j, binary, at['NORMAL'])[used]
    jo = get(j, binary, at['JOINTS_0'])[used]; we = get(j, binary, at['WEIGHTS_0'])[used]
    nprim = {'attributes': {'POSITION': put(pos, 'VEC3', 5126, True, 34962), 'NORMAL': put(nor, 'VEC3', 5126, target=34962),
                            'JOINTS_0': put(jo, 'VEC4', j['accessors'][at['JOINTS_0']]['componentType'], target=34962),
                            'WEIGHTS_0': put(we, 'VEC4', j['accessors'][at['WEIGHTS_0']]['componentType'], target=34962)},
             'indices': put(new_idx, 'SCALAR', 5123 if len(used) < 65536 else 5125, target=34963), 'mode': prim.get('mode', 4)}
    if j['accessors'][at['WEIGHTS_0']].get('normalized'): accs[nprim['attributes']['WEIGHTS_0']]['normalized'] = True
    skins = json.loads(json.dumps(j['skins']))
    for s in skins: s['inverseBindMatrices'] = keep(s['inverseBindMatrices'])
    anims = json.loads(json.dumps(j['animations'])); done = {}
    for an in anims:
        for s in an['samplers']:
            for key in ('input', 'output'):
                if s[key] not in done: done[s[key]] = keep(s[key])
                s[key] = done[s[key]]
    nodes = json.loads(json.dumps(j['nodes']))
    scene = j['scenes'][j.get('scene', 0)]
    for r in scene['nodes']:
        if nodes[r].get('name') == 'SmartRigArmature': nodes[r]['name'] = 'Armature'
    for n in nodes:
        if 'mesh' in n: n['name'] = 'char1'
    while len(out) % 4: out.append(0)
    k = dict(asset=j['asset'], scene=j.get('scene', 0), scenes=j['scenes'], nodes=nodes, skins=skins, animations=anims,
             meshes=[{'name': 'char1', 'primitives': [nprim]}], accessors=accs, bufferViews=views, buffers=[{'byteLength': len(out)}])
    js = json.dumps(k, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    with open(dst, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(out)))
        f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js); f.write(struct.pack('<I4s', len(out), b'BIN\x00')); f.write(out)
    # verify against the source: joints, bind matrices and keyframe data unchanged
    j2, b2 = read(dst)
    assert [nodes[i]['name'] for i in j2['skins'][0]['joints']] == [j['nodes'][i]['name'] for i in j['skins'][0]['joints']]
    assert np.array_equal(get(j, binary, j['skins'][0]['inverseBindMatrices']), get(j2, b2, j2['skins'][0]['inverseBindMatrices']))
    for a1, a2 in zip(j['animations'], j2['animations']):
        assert a1['channels'] == a2['channels'] and a1.get('name') == a2.get('name')
        for s1, s2 in zip(a1['samplers'], a2['samplers']):
            for key in ('input', 'output'): assert np.array_equal(get(j, binary, s1[key]), get(j2, b2, s2[key]))
    return {'triangles': int(len(new_idx) // 3), 'vertices': int(len(used)), 'bytes': 12 + 8 + len(js) + 8 + len(out),
            'animation': j['animations'][0].get('name'), 'channels': len(j['animations'][0]['channels'])}


if __name__ == '__main__':
    print(json.dumps(slim(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 60)))
