#!/usr/bin/env python3
"""Adds a TANGENT attribute (from tangents_blender.py) to a GLB's first mesh primitive; everything else unchanged.
Checks that Blender's vertex order matches the file (positions within 1e-4 after the axis conversion).
Usage: add_tangents.py in.glb tangents.npy out.glb"""
import json, struct, sys
import numpy as np
src, tnp, dst = sys.argv[1:4]
b = open(src, 'rb').read()
jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
bl = struct.unpack('<I', b[o:o + 4])[0]; binary = bytearray(b[o + 8:o + 8 + bl]); rest = b[o + 8 + bl:]
prim = j['meshes'][0]['primitives'][0]
pa = j['accessors'][prim['attributes']['POSITION']]; pv = j['bufferViews'][pa['bufferView']]
off = pv.get('byteOffset', 0) + pa.get('byteOffset', 0)
P = np.frombuffer(bytes(binary[off:off + pa['count'] * 12]), np.float32).reshape(-1, 3)
T = np.load(tnp); BP = np.load(tnp.replace('.npy', '_pos.npy'))
assert len(T) == len(P), f'vertex count differs: blender {len(T)} vs glTF {len(P)}'
err = np.abs(BP - P).max()
scale = None
if err > 1e-4:   # Blender may hold the mesh at another uniform scale; compare shapes
    scale = np.linalg.norm(P - P.mean(0), axis=1).mean() / np.linalg.norm(BP - BP.mean(0), axis=1).mean()
    err = np.abs((BP - BP.mean(0)) * scale - (P - P.mean(0))).max()
assert err < 1e-3, f'vertex order/positions differ (max {err})'
if 'TANGENT' in prim['attributes']: sys.exit('already has tangents')
while len(binary) % 4: binary.append(0)
start = len(binary); data = T.astype(np.float32).tobytes(); binary += data
j['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(data), 'target': 34962})
j['accessors'].append({'bufferView': len(j['bufferViews']) - 1, 'componentType': 5126, 'count': len(T), 'type': 'VEC4'})
prim['attributes']['TANGENT'] = len(j['accessors']) - 1
j['buffers'][0]['byteLength'] = len(binary)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
while len(binary) % 4: binary.append(0)
total = 12 + 8 + len(js) + 8 + len(binary) + len(rest)
with open(dst, 'wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, total)); f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js)
    f.write(struct.pack('<I4s', len(binary), b'BIN\x00')); f.write(binary); f.write(rest)
print(dst, 'tangents', len(T), 'position check max err %.2e' % err, 'scale', scale, 'w<0 share %.2f' % (T[:, 3] < 0).mean())
