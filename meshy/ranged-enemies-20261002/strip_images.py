#!/usr/bin/env python3
"""Copy of a GLB without images, textures and samplers (materials keep their factors; texture references removed) and
with the binary rebuilt from the accessors only. Unity imports the ranged enemies' geometry/skeleton from these copies
and uses URP Lit materials on the exported texture sets (make_textures.py), so the 2k maps are not imported twice.
Usage: python3 strip_images.py in.glb out.glb"""
import copy, json, struct, sys
from gltf_io import GLB


def strip(src, dst):
    g = GLB(src); j = copy.deepcopy(g.j)
    for k in ('images', 'textures', 'samplers'): j.pop(k, None)
    def drop_tex(o):
        if isinstance(o, dict):
            for k in [k for k, v in o.items() if k.endswith('Texture') and isinstance(v, dict) and 'index' in v]: del o[k]
            for v in o.values(): drop_tex(v)
        elif isinstance(o, list):
            for v in o: drop_tex(v)
    drop_tex(j.get('materials', []))
    for k in ('extensionsUsed', 'extensionsRequired'):
        if k in j:
            j[k] = [e for e in j[k] if e not in ('KHR_texture_transform',)]
            if not j[k]: del j[k]
    used = sorted({a['bufferView'] for a in j['accessors'] if 'bufferView' in a})
    out = bytearray(); remap = {}; views = []
    for bv in used:
        v = dict(j['bufferViews'][bv]); data = g.bin[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
        while len(out) % 4: out.append(0)
        v['byteOffset'] = len(out); v['buffer'] = 0; out += data; remap[bv] = len(views); views.append(v)
    while len(out) % 4: out.append(0)
    for a in j['accessors']:
        if 'bufferView' in a: a['bufferView'] = remap[a['bufferView']]
    if 'skins' in j: pass
    j['bufferViews'] = views; j['buffers'] = [dict(byteLength=len(out))]
    g2 = GLB.__new__(GLB); g2.j = j; g2.bin = out; g2.save(dst)
    return len(g.bin), len(out)


if __name__ == '__main__':
    print(sys.argv[1], '->', sys.argv[2], 'bin %d -> %d bytes' % strip(sys.argv[1], sys.argv[2]))
