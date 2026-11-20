#!/usr/bin/env python3
"""Pure-Python GLB reader used by the armour check: skin joints, inverse bind matrices, triangles, weights, materials,
images. Usage: glbinfo.py FILE.glb [...]  (prints a summary per file)"""
import json, struct, sys
CT = {5120: 'b', 5121: 'B', 5122: 'h', 5123: 'H', 5125: 'I', 5126: 'f'}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
class Glb:
    def __init__(self, path):
        b = open(path, 'rb').read(); self.path = path
        jl = struct.unpack('<I', b[12:16])[0]; self.j = json.loads(b[20:20 + jl]); self.bin = b[28 + jl:]; self.size = len(b)
    def acc(self, i):
        a = self.j['accessors'][i]; v = self.j['bufferViews'][a['bufferView']]
        n = NC[a['type']]; fmt = CT[a['componentType']]; sz = struct.calcsize(fmt) * n
        stride = v.get('byteStride') or sz; off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        out = []
        for k in range(a['count']):
            out.append(struct.unpack_from('<%d%s' % (n, fmt), self.bin, off + k * stride))
        if a.get('normalized'):
            d = {'B': 255.0, 'H': 65535.0, 'b': 127.0, 'h': 32767.0}.get(fmt)
            if d: out = [tuple(x / d for x in t) for t in out]
        return out
    def skin(self):
        s = self.j['skins'][0]; names = [self.j['nodes'][i].get('name') for i in s['joints']]
        ibm = self.acc(s['inverseBindMatrices']); return names, ibm
    def summary(self):
        j = self.j; names, ibm = self.skin()
        tris = 0; verts = 0; maxinf = 0; unweighted = 0; notnorm = 0; used = {}; hist = [0] * 5
        for m in j['meshes']:
            for p in m['primitives']:
                a = p['attributes']; n = j['accessors'][a['POSITION']]['count']; verts += n
                tris += (j['accessors'][p['indices']]['count'] if 'indices' in p else n) // 3
                if 'JOINTS_1' in a: maxinf = 8
                js = self.acc(a['JOINTS_0']); ws = self.acc(a['WEIGHTS_0'])
                for jj, ww in zip(js, ws):
                    k = sum(1 for w in ww if w > 1e-5); hist[k] += 1; maxinf = max(maxinf, k)
                    t = sum(ww)
                    if t < 1e-5: unweighted += 1
                    elif abs(t - 1) > 2e-3: notnorm += 1
                    for q, w in zip(jj, ww):
                        if w > 1e-5: used[names[q]] = used.get(names[q], 0) + w
        imgs = []
        for im in j.get('images', []):
            v = j['bufferViews'][im['bufferView']]; d = self.bin[v.get('byteOffset', 0):v.get('byteOffset', 0) + v['byteLength']]
            w = h = None
            if d[:8] == b'\x89PNG\r\n\x1a\n': w, h = struct.unpack('>II', d[16:24])
            elif d[:2] == b'\xff\xd8':
                i = 2
                while i < len(d):
                    if d[i] != 0xFF: i += 1; continue
                    mk = d[i + 1]
                    if mk in (0xC0, 0xC1, 0xC2): h, w = struct.unpack('>HH', d[i + 5:i + 9]); break
                    i += 2 + struct.unpack('>H', d[i + 2:i + 4])[0]
            imgs.append(dict(name=im.get('name'), mime=im.get('mimeType'), w=w, h=h, bytes=v['byteLength']))
        scene_roots = [j['nodes'][i].get('name') for i in j['scenes'][j.get('scene', 0)]['nodes']]
        mesh_nodes = [n.get('name') for n in j['nodes'] if 'mesh' in n]
        return dict(file=self.path.split('/')[-1], bytes=self.size, joints=len(names), triangles=tris, vertices=verts,
                    max_influences=maxinf, influence_hist=hist, unweighted=unweighted, not_normalised=notnorm,
                    weighted_bones={k: round(v, 1) for k, v in sorted(used.items(), key=lambda kv: -kv[1])},
                    meshes=[m.get('name') for m in j['meshes']], mesh_nodes=mesh_nodes, scene_roots=scene_roots,
                    materials=[m.get('name') for m in j.get('materials', [])], images=imgs,
                    animations=len(j.get('animations', [])), material_json=j.get('materials', []))
if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = Glb(p).summary(); mj = s.pop('material_json')
        print(json.dumps(s, indent=1)); print('MAT', json.dumps(mj))
