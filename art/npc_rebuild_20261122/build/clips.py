"""Animation-only clip copies for a rebuilt NPC: root renamed to `Armature` (the built model's), and the skeleton
checked against the built file node by node. python3 clips.py built.glb out_dir clip.glb=name ..."""
import json, struct, subprocess, sys
from pathlib import Path
STRIP = Path(__file__).resolve().parents[3] / 'meshy/ward-npcs-20261003/strip_clip.py'

def read(p):
    b = Path(p).read_bytes(); n = struct.unpack('<I', b[12:16])[0]
    return json.loads(b[20:20 + n]), b[20 + n:]

def local(j):
    out = {}
    for n in j['nodes']:
        if n.get('name'): out[n['name']] = (n.get('translation', [0, 0, 0]), n.get('scale', [1, 1, 1]), sorted(j['nodes'][c].get('name', '') for c in n.get('children', []) if 'mesh' not in j['nodes'][c]))
    return out

built, _ = read(sys.argv[1]); B = local(built); out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
bad = 0
for arg in sys.argv[3:]:
    src, name = arg.split('='); dst = out / f'{name}.glb'
    subprocess.run([sys.executable, str(STRIP), src, str(dst)], check=True, capture_output=True)
    j, rest = read(dst)
    for n in j['nodes']:
        if n.get('name') == 'SmartRigArmature': n['name'] = 'Armature'
    js = json.dumps(j, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    dst.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(js) + len(rest)) + struct.pack('<I4s', len(js), b'JSON') + js + rest)
    C = local(j); used = {j['nodes'][c['target']['node']].get('name') for a in j['animations'] for c in a['channels']}
    missing = sorted(u for u in used if u not in B)
    moved = [k for k in used if k in B and k not in ('Hips', 'Armature') and max(abs(x - y) for x, y in zip(B[k][0], C[k][0])) > 2e-3]
    bad += bool(missing or moved)
    print('CLIP', name, 'missing', missing, 'rest offsets differ', moved[:6])
sys.exit(1 if bad else 0)
