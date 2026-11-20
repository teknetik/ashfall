"""Helmet placement probe: how far the helmet's OUTER shell clears the head and hair, seen radially from the middle of
the head, for a grid of uniform scales and offsets. Prints a table and writes work/helmet_probe.json.
Usage: blender.sh helmet_probe.py -- [mults=1.0,1.03,...] [dys=..] [dzs=..] [margin=0.016]"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, json, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []; opt = dict(a.split('=', 1) for a in args if '=' in a)
fl = lambda k, d: [float(x) for x in opt.get(k, d).split(',')]
MULTS = fl('mults', '0.96,1.0,1.04,1.08'); DYS = fl('dys', '-0.012,-0.006,0.0,0.006'); DZS = fl('dzs', '-0.01,0.0,0.01,0.02')
MARGIN = float(opt.get('margin', 0.016))
arm, body = H.load_hero()
ws = H.world_verts(body); top = max(w.z for w in ws)
cap = [w for w in ws if w.z > top - 0.13]
xs = [w.x for w in cap]; ys = [w.y for w in cap]
hd = max(ys) - min(ys); cx = (max(xs) + min(xs)) / 2; cy = (max(ys) + min(ys)) / 2
c0 = Vector((cx, cy, top - 0.12))
head = [w for w in ws if w.z > top - 0.24 and abs(w.x) < 0.14][::2]
h = H.import_piece(H.MESHY / 'helmet' / 'model.glb', 'probe'); H.merge_splits(h)
lo, hi = H.bounds(h); s0 = (hd + 2 * MARGIN) / ((hi - lo).y * 0.93)
bm = bmesh.new(); bm.from_mesh(h.data); bvh = BVHTree.FromBMesh(bm)
rows = []
for mult in MULTS:
    s = s0 * mult
    for dy in DYS:
        for dz in DZS:
            T = Vector((cx, cy + dy, top + MARGIN * 0.9 - s * hi.z + dz))
            q0 = (c0 - T) / s; n = 0; neg = 0; lt3 = 0; worst = 9; liner = 0; where = None
            for w in head:
                d = w - c0; rb = d.length; d = d / rb
                hit = bvh.ray_cast(q0 + d * 5.0, -d, 5.0)                 # from far outside inwards: the outer shell
                if hit[0] is None: continue
                rout = (hit[0] - q0).length * s
                hin = bvh.ray_cast(q0, d, 5.0); rin = (hin[0] - q0).length * s if hin[0] is not None else rout
                if rout - rin < 0.002: continue                           # a single wall: rim, strap or ear cup edge
                n += 1; cl = rout - rb
                if cl < worst: worst = cl; where = (round(w.x, 3), round(w.y, 3), round(w.z, 3))
                if cl < 0: neg += 1
                if cl < 0.003: lt3 += 1
                if rin < rb: liner += 1
            rows.append(dict(mult=mult, dy=dy, dz=dz, scale=round(s, 5), covered=n, through=neg, lt3mm=lt3, worst_mm=round(worst * 1000, 1),
                             liner_inside=liner, where=where))
rows.sort(key=lambda r: (r['mult'], r['through'], r['lt3mm']))
for r in rows: print('PROBE', r)
(H.WORK / 'helmet_probe.json').write_text(json.dumps(dict(c0=list(c0), s0=s0, rows=rows), indent=1))
