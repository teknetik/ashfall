"""Read named cameras (cam_*) from the saved scene YAML: world position, forward, fov. Read-only helper for layout/review.
Usage: python3 scene_cams.py [prefix ...]  -> prints JSON {name: {pos, fwd, fov}}"""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENE = ROOT / "unity/AthenHill/Assets/AthenHill/Scenes/AthenHill.unity"


def qrot(q, v):
    x, y, z, w = q
    # v' = q v q*
    ix = w * v[0] + y * v[2] - z * v[1]
    iy = w * v[1] + z * v[0] - x * v[2]
    iz = w * v[2] + x * v[1] - y * v[0]
    iw = -x * v[0] - y * v[1] - z * v[2]
    return (ix * w + iw * -x + iy * -z - iz * -y, iy * w + iw * -y + iz * -x - ix * -z, iz * w + iw * -z + ix * -y - iy * -x)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def load():
    text = SCENE.read_text()
    docs = re.split(r'\n(?=--- !u!)', text)
    objs, trs, cams = {}, {}, {}
    for d in docs:
        m = re.match(r'--- !u!(\d+) &(-?\d+)', d)
        if not m:
            continue
        cls, fid = m.group(1), m.group(2)
        if cls == '1':
            n = re.search(r'\n  m_Name: (.*)', d)
            comps = re.findall(r'component: \{fileID: (-?\d+)\}', d)
            objs[fid] = (n.group(1).strip() if n else '', comps)
        elif cls == '4':
            g = re.search(r'm_GameObject: \{fileID: (-?\d+)\}', d)
            if not g:
                continue
            go = g.group(1)
            p = re.search(r'm_LocalPosition: \{x: ([^,]+), y: ([^,]+), z: ([^}]+)\}', d)
            r = re.search(r'm_LocalRotation: \{x: ([^,]+), y: ([^,]+), z: ([^,]+), w: ([^}]+)\}', d)
            s = re.search(r'm_LocalScale: \{x: ([^,]+), y: ([^,]+), z: ([^}]+)\}', d)
            par = re.search(r'm_Father: \{fileID: (-?\d+)\}', d)
            trs[fid] = dict(go=go, pos=tuple(map(float, p.groups())) if p else (0, 0, 0),
                            rot=tuple(map(float, r.groups())) if r else (0, 0, 0, 1),
                            scl=tuple(map(float, s.groups())) if s else (1, 1, 1), parent=par.group(1) if par else '0')
        elif cls == '20':
            g = re.search(r'm_GameObject: \{fileID: (-?\d+)\}', d)
            if not g:
                continue
            go = g.group(1)
            fov = re.search(r'field of view: ([^\n]+)', d)
            cams[go] = float(fov.group(1)) if fov else 60.0
    return objs, trs, cams


def world(trs, fid):
    t = trs[fid]
    pos, rot = t['pos'], t['rot']
    par = t['parent']
    while par != '0' and par in trs:
        pt = trs[par]
        sp = (pos[0] * pt['scl'][0], pos[1] * pt['scl'][1], pos[2] * pt['scl'][2])
        rp = qrot(pt['rot'], sp)
        pos = (rp[0] + pt['pos'][0], rp[1] + pt['pos'][1], rp[2] + pt['pos'][2])
        rot = qmul(pt['rot'], rot)
        par = pt['parent']
    return pos, rot


def cameras(prefixes=("cam_",)):
    objs, trs, cams = load()
    go2tr = {t['go']: fid for fid, t in trs.items()}
    out = {}
    for go, fov in cams.items():
        name = objs.get(go, ('', []))[0]
        if not any(name.startswith(p) for p in prefixes) or go not in go2tr:
            continue
        pos, rot = world(trs, go2tr[go])
        f = qrot(rot, (0, 0, 1))
        out[name] = dict(pos=[round(x, 3) for x in pos], fwd=[round(x, 4) for x in f], fov=fov)
    return out


if __name__ == "__main__":
    pre = tuple(sys.argv[1:]) or ("cam_",)
    print(json.dumps(cameras(pre), indent=0))
