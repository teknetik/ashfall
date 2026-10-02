#!/usr/bin/env python3
"""(Copied from meshy/salvage-dealer-20261001.) Animation-only copy of a Meshy clip GLB: keeps the node hierarchy, scenes and animations (accessor data byte-identical)
and drops the mesh, skin, materials and textures, which duplicate rigged.glb (same rig task). ~12 MB -> a few hundred kB.
Usage: python3 strip_clip.py in.glb out.glb"""
import json, struct, sys


def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'glTF'
    jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl])
    o = 20 + jl; bl = struct.unpack('<I', b[o:o + 4])[0]; assert b[o + 4:o + 8] == b'BIN\x00'
    return j, b[o + 8:o + 8 + bl]


def acc_bytes(j, binary, i):
    a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
    start = v.get('byteOffset', 0); return binary[start:start + v['byteLength']], a.get('byteOffset', 0)


def strip(src, dst):
    j, binary = read(src)
    used = sorted({i for an in j['animations'] for s in an['samplers'] for i in (s['input'], s['output'])})
    acc_map, view_map, views, out = {}, {}, [], bytearray()
    accessors = []
    for i in used:
        a = dict(j['accessors'][i]); assert 'sparse' not in a
        bv = a['bufferView']
        if bv not in view_map:
            v = dict(j['bufferViews'][bv]); data = binary[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
            while len(out) % 4: out.append(0)
            v['byteOffset'] = len(out); v['buffer'] = 0; v.pop('target', None); out += data
            view_map[bv] = len(views); views.append(v)
        a['bufferView'] = view_map[bv]; acc_map[i] = len(accessors); accessors.append(a)
    while len(out) % 4: out.append(0)
    anims = json.loads(json.dumps(j['animations']))
    for an in anims:
        for s in an['samplers']: s['input'] = acc_map[s['input']]; s['output'] = acc_map[s['output']]
    nodes = []
    for n in j['nodes']:
        n = dict(n); n.pop('mesh', None); n.pop('skin', None); nodes.append(n)
    k = dict(asset=j['asset'], scene=j.get('scene', 0), scenes=j['scenes'], nodes=nodes, animations=anims,
             accessors=accessors, bufferViews=views, buffers=[dict(byteLength=len(out))])
    js = json.dumps(k, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    total = 12 + 8 + len(js) + 8 + len(out)
    with open(dst, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total)); f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js)
        f.write(struct.pack('<I4s', len(out), b'BIN\x00')); f.write(out)
    # Verify: same channels, same node names, identical keyframe bytes.
    j2, b2 = read(dst)
    assert [n.get('name') for n in j2['nodes']] == [n.get('name') for n in j['nodes']]
    for a1, a2 in zip(j['animations'], j2['animations']):
        assert a1['channels'] == a2['channels']
        for s1, s2 in zip(a1['samplers'], a2['samplers']):
            for key in ('input', 'output'):
                x1, o1 = acc_bytes(j, binary, s1[key]); x2, o2 = acc_bytes(j2, b2, s2[key])
                assert x1 == x2 and o1 == o2 and j['accessors'][s1[key]]['count'] == j2['accessors'][s2[key]]['count']
    return len(binary), len(out)


if __name__ == '__main__':
    print(sys.argv[1], '->', sys.argv[2], 'bin bytes %d -> %d' % strip(sys.argv[1], sys.argv[2]))
