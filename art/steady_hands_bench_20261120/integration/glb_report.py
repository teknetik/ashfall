#!/usr/bin/env python3
"""Steady Hands bench, integration: what is inside each family GLB (no Unity, no Blender).
Usage: glb_report.py [--json OUT] [GLB ...]   (default: every GLB under Assets/AthenHill/Art/Bench)
Reads the GLB's JSON chunk and image headers only."""
import json, struct, sys, os, glob, hashlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ART = os.path.join(ROOT, 'unity/AthenHill/Assets/AthenHill/Art/Bench')

def read(path):
    with open(path, 'rb') as f:
        magic, ver, length = struct.unpack('<4sII', f.read(12))
        assert magic == b'glTF', path
        jlen, jtype = struct.unpack('<II', f.read(8)); js = json.loads(f.read(jlen))
        rest = f.read(8); blob = b''
        if len(rest) == 8:
            blen, btype = struct.unpack('<II', rest); blob = f.read(blen)
    return js, blob

def image_size(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        w, h = struct.unpack('>II', data[16:24]); return 'png', w, h
    if data[:2] == b'\xff\xd8':
        i = 2
        while i < len(data):
            if data[i] != 0xFF: i += 1; continue
            m = data[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', data[i + 5:i + 9]); return 'jpeg', w, h
            i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return '?', 0, 0

def report(path):
    js, blob = read(path)
    acc = js.get('accessors', []); bvs = js.get('bufferViews', [])
    out = {'file': os.path.relpath(path, ROOT), 'bytes': os.path.getsize(path), 'sha1': hashlib.sha1(open(path, 'rb').read()).hexdigest()[:12]}
    out['generator'] = js.get('asset', {}).get('generator'); out['extensionsUsed'] = js.get('extensionsUsed', [])
    imgs = []
    for im in js.get('images', []):
        bv = bvs[im['bufferView']]; data = blob[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        kind, w, h = image_size(data); imgs.append({'name': im.get('name'), 'kind': kind, 'w': w, 'h': h, 'bytes': bv['byteLength']})
    out['images'] = imgs
    def tex(t):
        if t is None: return None
        return imgs[js['textures'][t['index']]['source']]['name']
    mats = []
    for m in js.get('materials', []):
        p = m.get('pbrMetallicRoughness', {})
        mats.append({'name': m.get('name'), 'base': p.get('baseColorFactor'), 'baseTex': tex(p.get('baseColorTexture')), 'metal': p.get('metallicFactor', 1), 'rough': p.get('roughnessFactor', 1),
                     'ormTex': tex(p.get('metallicRoughnessTexture')), 'occTex': tex(m.get('occlusionTexture')), 'normalTex': tex(m.get('normalTexture')), 'emissive': m.get('emissiveFactor'),
                     'emissiveTex': tex(m.get('emissiveTexture')), 'alphaMode': m.get('alphaMode', 'OPAQUE'), 'doubleSided': m.get('doubleSided', False), 'extensions': list(m.get('extensions', {}).keys()),
                     'emissiveStrength': m.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength')})
    out['materials'] = mats
    meshes = []
    for me in js.get('meshes', []):
        tris = 0; ms = []
        for pr in me['primitives']:
            n = acc[pr['indices']]['count'] // 3 if 'indices' in pr else acc[pr['attributes']['POSITION']]['count'] // 3
            tris += n; ms.append(mats[pr['material']]['name'] if 'material' in pr else None)
        meshes.append({'name': me.get('name'), 'tris': tris, 'materials': ms, 'attrs': sorted(me['primitives'][0]['attributes'].keys())})
    nodes = js.get('nodes', [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i
    rows = []; use = {}
    for i, n in enumerate(nodes):
        if 'mesh' in n:
            me = meshes[n['mesh']]; rows.append({'node': n.get('name'), 'parent': nodes[parent[i]].get('name') if i in parent else None, 'tris': me['tris'], 'materials': me['materials'], 'skin': 'skin' in n})
            for m in me['materials']: use.setdefault(m, [0, 0]); use[m][0] += 1; use[m][1] += me['tris']
    out['meshNodes'] = rows; out['nodes'] = len(nodes); out['empties'] = sum(1 for n in nodes if 'mesh' not in n)
    out['triangles'] = sum(r['tris'] for r in rows); out['materialUse'] = {str(k): {'nodes': v[0], 'tris': v[1]} for k, v in use.items()}
    out['animations'] = [a.get('name') for a in js.get('animations', [])]; out['skins'] = len(js.get('skins', []))
    out['scenes'] = [[nodes[i].get('name') for i in s.get('nodes', [])] for s in js.get('scenes', [])]
    # texture memory as the project's importer stores it: BC7 with a full mip chain when power of two, else RGBA32
    def mem(w, h): pot = w and h and (w & (w - 1)) == 0 and (h & (h - 1)) == 0; return int(w * h * (1 if pot else 4) * 4 / 3)
    out['textureBytesBC7'] = sum(mem(i['w'], i['h']) for i in imgs)
    return out

if __name__ == '__main__':
    args = sys.argv[1:]; outp = None
    if '--json' in args: k = args.index('--json'); outp = args[k + 1]; del args[k:k + 2]
    files = args or sorted(glob.glob(os.path.join(ART, '*', '*.glb')))
    res = [report(f) for f in files]
    if outp: json.dump(res, open(outp, 'w'), indent=1)
    for r in res:
        print('=====', r['file'], f"{r['bytes'] / 1e6:.1f} MB", r['sha1'], r['generator'])
        print('  triangles', r['triangles'], 'mesh nodes', len(r['meshNodes']), 'nodes', r['nodes'], 'skins', r['skins'], 'clips', r['animations'])
        print('  extensions', r['extensionsUsed'], 'roots', r['scenes'])
        for i in r['images']: print('  image', i)
        for m in r['materials']: print('  material', {k: v for k, v in m.items() if v not in (None, [], False)})
        print('  use', r['materialUse'], ' texture memory (BC7 + mips) %.1f MB' % (r['textureBytesBC7'] / 1048576))
