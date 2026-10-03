#!/usr/bin/env python3
"""Linn: Meshy's rigging output kept only the base colour (also wired as full emissive; no normal or
metallic-roughness). Its UVs and base colour equal the pre-rig model.glb (RMSE 0.6 %). This writes a rigged GLB whose
material is model.glb's PBR set (base colour, metallic-roughness, normal), so the common pipeline applies.
Usage: linn_material.py rigged.glb model.glb out.glb"""
import json, struct, sys
def read(p):
    b = open(p, 'rb').read(); jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); o = 20 + jl
    bl = struct.unpack('<I', b[o:o + 4])[0]; return j, bytearray(b[o + 8:o + 8 + bl])
j, binary = read(sys.argv[1]); mj, mb = read(sys.argv[2])
def img_bytes(jj, bb, i):
    v = jj['bufferViews'][jj['images'][i]['bufferView']]; return bytes(bb[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]), jj['images'][i]['mimeType']
mm = mj['materials'][0]
src = {'normal': mj['textures'][mm['normalTexture']['index']]['source'], 'base': mj['textures'][mm['pbrMetallicRoughness']['baseColorTexture']['index']]['source'],
       'mr': mj['textures'][mm['pbrMetallicRoughness']['metallicRoughnessTexture']['index']]['source']}
j['images'] = []; j['textures'] = []
for k in ('normal', 'base', 'mr'):
    data, mime = img_bytes(mj, mb, src[k])
    while len(binary) % 4: binary.append(0)
    j['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)}); binary += data
    j['images'].append({'bufferView': len(j['bufferViews']) - 1, 'mimeType': mime, 'name': k})
    j['textures'].append({'sampler': 0, 'source': len(j['images']) - 1})
if not j.get('samplers'): j['samplers'] = [{}]
j['materials'] = [{'name': 'Material_0', 'doubleSided': True, 'normalTexture': {'index': 0},
                   'pbrMetallicRoughness': {'baseColorTexture': {'index': 1}, 'metallicRoughnessTexture': {'index': 2}}}]
for m in j['meshes']:
    for p in m['primitives']: p['material'] = 0
j.pop('extensionsUsed', None) if not any('extensions' in x for x in j['materials']) else None
while len(binary) % 4: binary.append(0)
j['buffers'][0]['byteLength'] = len(binary)
js = json.dumps(j, separators=(',', ':')).encode()
while len(js) % 4: js += b' '
with open(sys.argv[3], 'wb') as f:
    f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(binary)))
    f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js); f.write(struct.pack('<I4s', len(binary), b'BIN\x00')); f.write(binary)
print(sys.argv[3], 'material from', sys.argv[2])
