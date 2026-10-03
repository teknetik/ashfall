#!/usr/bin/env python3
"""Replaces a GLB's normal-map image with a PNG file and strips any TANGENT attribute (add_tangents.py adds the
matching ones). Usage: replace_normal.py in.glb normal.png out.glb"""
import json, struct, sys
b = open(sys.argv[1], 'rb').read(); new = open(sys.argv[2], 'rb').read()
jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
bl = struct.unpack('<I', b[o:o + 4])[0]; binary = bytearray(b[o + 8:o + 8 + bl]); rest = b[o + 8 + bl:]
ni = j['materials'][0]['normalTexture']['index']; img = j['images'][j['textures'][ni]['source']]
while len(binary) % 4: binary.append(0)
start = len(binary); binary += new
j['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': len(new)})
img['bufferView'] = len(j['bufferViews']) - 1; img['mimeType'] = 'image/png'
for m in j['meshes']:
    for p in m['primitives']: p['attributes'].pop('TANGENT', None)
while len(binary) % 4: binary.append(0)
j['buffers'][0]['byteLength'] = len(binary)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
with open(sys.argv[3], 'wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(binary) + len(rest)))
    f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js); f.write(struct.pack('<I4s', len(binary), b'BIN\x00')); f.write(binary); f.write(rest)
print(sys.argv[3], 'normal map replaced by', sys.argv[2], 'tangents stripped')
