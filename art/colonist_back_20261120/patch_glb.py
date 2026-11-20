#!/usr/bin/env python3
"""Replace embedded images in a GLB without touching anything else (meshes, accessors, skins, inverse bind matrices,
animations stay byte-identical; only the image bufferViews are rewritten and the buffer re-packed).
Usage: patch_glb.py IN.glb OUT.glb IMAGE_NAME=path.png [IMAGE_NAME=path.png ...] [--mat NAME.key=json ...]
IMAGE_NAME is the glTF image name (e.g. suit_base). --mat sets a top-level or pbrMetallicRoughness key of a material,
e.g. --mat PlayerJumpsuit.pbrMetallicRoughness.roughnessFactor=0.86"""
import json, struct, sys, hashlib

def read(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'glTF'
    jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl])
    bl = struct.unpack('<I', b[20 + jl:24 + jl])[0]; binc = b[28 + jl:28 + jl + bl]
    return j, binc

def write(path, j, binc):
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4); binc += b'\0' * ((4 - len(binc) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(binc)
    with open(path, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2, total))
        f.write(struct.pack('<I', len(js)) + b'JSON' + js)
        f.write(struct.pack('<I', len(binc)) + b'BIN\0' + binc)

def patch(src, dst, images, mats=()):
    j, binc = read(src)
    views = j['bufferViews']
    repl = {}
    for name, path in images.items():
        idx = [i for i, im in enumerate(j['images']) if im.get('name') == name]
        assert len(idx) == 1, f'image {name}: {idx}'
        data = open(path, 'rb').read()
        repl[j['images'][idx[0]]['bufferView']] = data
        j['images'][idx[0]]['mimeType'] = 'image/png' if data[:4] == b'\x89PNG' else 'image/jpeg'
    out = bytearray()
    for vi, v in enumerate(views):
        data = repl.get(vi, binc[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']])
        while len(out) % 4: out += b'\0'
        v['byteOffset'] = len(out); v['byteLength'] = len(data); out += data
    j['buffers'][0]['byteLength'] = len(out)
    for spec in mats:
        key, val = spec.split('=', 1); parts = key.split('.')
        m = next(m for m in j['materials'] if m.get('name') == parts[0]); d = m
        for p in parts[1:-1]: d = d.setdefault(p, {})
        d[parts[-1]] = json.loads(val)
    write(dst, j, bytes(out))
    # integrity: every non-image view unchanged
    j0, b0 = read(src); j1, b1 = read(dst)
    imgviews = set(repl)
    for vi, (v0, v1) in enumerate(zip(j0['bufferViews'], j1['bufferViews'])):
        if vi in imgviews: continue
        a = b0[v0.get('byteOffset', 0):v0.get('byteOffset', 0) + v0['byteLength']]
        c = b1[v1.get('byteOffset', 0):v1.get('byteOffset', 0) + v1['byteLength']]
        assert a == c, f'view {vi} changed'
    for k in ('accessors', 'skins', 'nodes', 'meshes', 'animations'):
        assert j0.get(k) == j1.get(k), k
    print('PATCHED', dst, hashlib.sha256(open(dst, 'rb').read()).hexdigest())

if __name__ == '__main__':
    a = sys.argv[1:]; mats = []
    if '--mat' in a:
        i = a.index('--mat'); mats = a[i + 1:]; a = a[:i]
    patch(a[0], a[1], dict(x.split('=', 1) for x in a[2:]), mats)
