#!/usr/bin/env python3
"""Splices lod_blender.py's LOD0/LOD1 into a rigged Meshy GLB: the char1 primitive becomes LOD0 (POSITION, NORMAL,
TEXCOORD_0, TANGENT, JOINTS_0, WEIGHTS_0, indices), a second node 'char1_lod1' (same skin, same material) carries LOD1,
and the normal image is replaced with normal_lod0.png. Armature, skin, bind matrices and other textures unchanged.
Usage: glb_lod.py <npc folder> <src glb> <out glb>"""
import json, struct, sys
import numpy as np
from pathlib import Path
D = Path(sys.argv[1]); b = open(D / sys.argv[2], 'rb').read()
jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
bl = struct.unpack('<I', b[o:o + 4])[0]; binary = bytearray(b[o + 8:o + 8 + bl])
z = np.load(D / (sys.argv[5] if len(sys.argv) > 5 else 'lod.npz'))
def add(arr, typ, comp, target=None, minmax=False):
    while len(binary) % 4: binary.append(0)
    data = np.ascontiguousarray(arr).tobytes(); start = len(binary); binary.extend(data)
    bv = {'buffer': 0, 'byteOffset': start, 'byteLength': len(data)}
    if target: bv['target'] = target
    j['bufferViews'].append(bv)
    a = {'bufferView': len(j['bufferViews']) - 1, 'componentType': comp, 'count': len(arr), 'type': typ}
    if minmax: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    j['accessors'].append(a); return len(j['accessors']) - 1
def prim(l, material):
    g = lambda k: z[f'{l}_{k}']
    return {'attributes': {'POSITION': add(g('P'), 'VEC3', 5126, 34962, True), 'NORMAL': add(g('N'), 'VEC3', 5126, 34962),
                           'TEXCOORD_0': add(g('UV'), 'VEC2', 5126, 34962), 'TANGENT': add(g('T'), 'VEC4', 5126, 34962),
                           'JOINTS_0': add(g('J'), 'VEC4', 5123, 34962), 'WEIGHTS_0': add(g('W'), 'VEC4', 5126, 34962)},
            'indices': add(g('I').ravel(), 'SCALAR', 5125, 34963), 'material': material, 'mode': 4}
mat = j['meshes'][0]['primitives'][0].get('material', 0)
j['meshes'][0]['primitives'] = [prim('l0', mat)]
j['meshes'].append({'name': 'char1_lod1', 'primitives': [prim('l1', mat)]})
mesh_node = next(i for i, n in enumerate(j['nodes']) if n.get('mesh') == 0)
j['nodes'].append({'name': 'char1_lod1', 'mesh': len(j['meshes']) - 1, 'skin': j['nodes'][mesh_node]['skin']})
parent = next(n for n in j['nodes'] if mesh_node in n.get('children', []))
parent['children'].insert(parent['children'].index(mesh_node) + 1, len(j['nodes']) - 1)
# normal map
new = open(D / (sys.argv[4] if len(sys.argv) > 4 else 'normal_lod0.png'), 'rb').read()
ni = j['materials'][mat]['normalTexture']['index']; img = j['images'][j['textures'][ni]['source']]
while len(binary) % 4: binary.append(0)
j['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(new)}); binary.extend(new)
img['bufferView'] = len(j['bufferViews']) - 1; img['mimeType'] = 'image/png'
while len(binary) % 4: binary.append(0)
j['buffers'][0]['byteLength'] = len(binary)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
with open(D / sys.argv[3], 'wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(binary)))
    f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js); f.write(struct.pack('<I4s', len(binary), b'BIN\x00')); f.write(binary)
print(D / sys.argv[3], 'lod0', len(z['l0_I']), 'tris', 'lod1', len(z['l1_I']), 'tris')
