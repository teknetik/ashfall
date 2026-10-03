#!/usr/bin/env python3
"""Meshy's rigging output carries MikkTSpace tangent directions with the handedness (w) inverted against the glTF
convention (bitangent = cross(normal, tangent) * w): all w disagree with MikkTSpace computed by Blender on the same
normals/UVs, while xyz match exactly (vex: dot median 1.0). The inverted bitangent flips the normal map's green channel,
which renders as per-chart facets in Unity. This negates TANGENT.w in place; nothing else changes.
Usage: fix_tangents.py in.glb out.glb"""
import json, struct, sys
import numpy as np
b = bytearray(open(sys.argv[1], 'rb').read())
jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); base = 20 + jl + 8
done = set()
for m in j['meshes']:
    for p in m['primitives']:
        i = p['attributes'].get('TANGENT')
        if i is None or i in done: continue
        done.add(i); a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
        assert a['componentType'] == 5126 and a['type'] == 'VEC4' and v.get('byteStride', 16) == 16
        off = base + v.get('byteOffset', 0) + a.get('byteOffset', 0)
        T = np.frombuffer(bytes(b[off:off + a['count'] * 16]), np.float32).reshape(-1, 4).copy()
        T[:, 3] *= -1; b[off:off + a['count'] * 16] = T.tobytes()
        print(sys.argv[1], 'tangent w negated on', a['count'], 'vertices')
if not done: sys.exit('no TANGENT attribute')
open(sys.argv[2], 'wb').write(b)
