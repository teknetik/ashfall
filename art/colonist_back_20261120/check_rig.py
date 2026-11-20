#!/usr/bin/env python3
"""Compare the skins of two GLBs: joint names in order and inverse bind matrices (max abs diff). The game binds armour
pieces to the player's bones by name and rejects differing bind poses; the scene's SkinnedMeshRenderer keeps the old
bone order, so the order must match too. Usage: check_rig.py OLD.glb NEW.glb [...pairs]"""
import json, struct, sys
def load(p):
    b = open(p, 'rb').read(); jl = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + jl]); bin0 = 28 + jl
    s = j['skins'][0]; names = [j['nodes'][i].get('name') for i in s['joints']]
    a = j['accessors'][s['inverseBindMatrices']]; v = j['bufferViews'][a['bufferView']]
    off = bin0 + v.get('byteOffset', 0) + a.get('byteOffset', 0)
    m = struct.unpack('<%df' % (16 * a['count']), b[off:off + 64 * a['count']])
    return names, m, [mm.get('name') for mm in j['meshes']], [mm.get('name') for mm in j['materials']]
ok = True; a = sys.argv[1:]
for i in range(0, len(a), 2):
    n0, m0, me0, ma0 = load(a[i]); n1, m1, me1, ma1 = load(a[i + 1])
    d = max(abs(x - y) for x, y in zip(m0, m1)) if len(m0) == len(m1) else float('inf')
    same = n0 == n1 and d < 1e-5 and me0 == me1 and ma0 == ma1
    ok &= same
    print(('OK  ' if same else 'FAIL'), a[i + 1].split('/')[-1], 'joints', len(n1), 'order', n0 == n1, 'ibm max diff %.2e' % d, 'meshes', me1, 'materials', ma1)
sys.exit(0 if ok else 1)
