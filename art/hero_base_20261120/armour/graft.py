#!/usr/bin/env python3
"""Give a freshly exported armour GLB (mesh + skin, no images) the material of the piece's CURRENT game file:
materials, textures, samplers and images are copied from OLD byte for byte (so texture resolution, encoding and the
20 Nov clean-up of the vest/helmet maps are exactly what ships now), and the mesh and its node get the old names.
Usage: graft.py NEW.glb OLD.glb OUT.glb"""
import json, struct, sys, hashlib


def read(path):
    b = open(path, 'rb').read(); assert b[:4] == b'glTF'
    jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl])
    bl = struct.unpack('<I', b[20 + jl:24 + jl])[0]; return j, b[28 + jl:28 + jl + bl]


def write(path, j, binc):
    js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
    binc = bytes(binc) + b'\0' * ((4 - len(binc) % 4) % 4)
    with open(path, 'wb') as f:
        f.write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(binc)))
        f.write(struct.pack('<I', len(js)) + b'JSON' + js); f.write(struct.pack('<I', len(binc)) + b'BIN\0' + binc)


def graft(new, old, out):
    jn, bn = read(new); jo, bo = read(old)
    assert len(jn['meshes']) == 1 and len(jo['meshes']) == 1 and len(jo['materials']) == 1
    assert not jn.get('animations'), 'new file has animations'
    # drop any images/materials the new export carries, keep every other bufferView
    img_views = {im['bufferView'] for im in jn.get('images', []) if 'bufferView' in im}
    outb = bytearray(); remap = {}; views = []
    for i, v in enumerate(jn['bufferViews']):
        if i in img_views: continue
        d = bn[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
        while len(outb) % 4: outb += b'\0'
        nv = dict(v); nv['byteOffset'] = len(outb); outb += d; remap[i] = len(views); views.append(nv)
    for a in jn['accessors']:
        if 'bufferView' in a: a['bufferView'] = remap[a['bufferView']]
    images = []
    for im in jo['images']:
        v = jo['bufferViews'][im['bufferView']]; d = bo[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
        while len(outb) % 4: outb += b'\0'
        views.append({'buffer': 0, 'byteOffset': len(outb), 'byteLength': len(d)}); outb += d
        ni = dict(im); ni['bufferView'] = len(views) - 1; images.append(ni)
    jn['bufferViews'] = views; jn['buffers'] = [{'byteLength': len(outb)}]
    jn['images'] = images; jn['textures'] = jo['textures']; jn['samplers'] = jo.get('samplers', []); jn['materials'] = jo['materials']
    for k in ('extensionsUsed', 'extensionsRequired'):
        if k in jo: jn[k] = jo[k]
        else: jn.pop(k, None)
    name = jo['meshes'][0].get('name'); jn['meshes'][0]['name'] = name
    for p in jn['meshes'][0]['primitives']:
        p['material'] = 0; assert 'TEXCOORD_0' in p['attributes'] and 'JOINTS_0' in p['attributes'], p['attributes']
    old_node = next(n.get('name') for n in jo['nodes'] if 'mesh' in n)
    for n in jn['nodes']:
        if 'mesh' in n: n['name'] = old_node
    write(out, jn, outb)
    print('GRAFT', out.split('/')[-1], 'mesh', name, 'node', old_node, 'material', jo['materials'][0].get('name'),
          'images', [(i.get('name'), i.get('mimeType')) for i in images], hashlib.sha256(open(out, 'rb').read()).hexdigest()[:12])


if __name__ == '__main__':
    graft(*sys.argv[1:4])
