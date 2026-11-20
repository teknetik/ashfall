"""Hero armour: scrap helmet (Meshy source meshy/tutorial-set-20261002/helmet) fitted to the new head.
Port of art/colonist_back_20261120/blender/fit_piece.py (helmet): uniform scale from the head cap (skull + sculpted
hair above the ears), UV-seam splits merged, smooth push-out against the head, texture-aware decimation outside
Blender, rigid on Head.
Usage: blender.sh fit_helmet.py -- fit [margin=0.016] [mult=1.0] [dy=0.006] [dz=0.0]   -> work/helmet_fit.obj
       blender.sh fit_helmet.py -- skin                                            -> work/stage/TS_Helmet.glb"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, json
from mathutils import Vector
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:]; STAGE = args[0]; opt = dict(a.split('=', 1) for a in args[1:] if '=' in a)
MARGIN = float(opt.get('margin', 0.016)); MULT = float(opt.get('mult', 1.0)); DY = float(opt.get('dy', 0.006)); DZ = float(opt.get('dz', 0.0)); CLEAR = float(opt.get('clear', 0.004))
arm, body = H.load_hero()
if STAGE == 'fit':
    ws = H.world_verts(body); top = max(w.z for w in ws)
    cap = [w for w in ws if w.z > top - 0.13]                       # skull + hair above the ears
    xs = [w.x for w in cap]; ys = [w.y for w in cap]
    hd = max(ys) - min(ys); hw = max(xs) - min(xs); cx = (max(xs) + min(xs)) / 2; cy = (max(ys) + min(ys)) / 2
    h = H.import_piece(H.MESHY / 'helmet' / 'model.glb', 'TS_Helmet'); merged = H.merge_splits(h)
    lo, hi = H.bounds(h)
    s = (hd + 2 * MARGIN) / ((hi - lo).y * 0.93) * MULT; h.scale = (s, s, s); H.apply(h); lo, hi = H.bounds(h)
    h.location = (cx - (lo.x + hi.x) / 2, cy - (lo.y + hi.y) / 2 + DY, top + MARGIN * 0.9 - hi.z + DZ); H.apply(h)
    pen0 = H.penetration(h, body)
    # The shipped recipe's push_out moved only the vertices inside the head, wall by wall: on the sculpted hair the
    # padding was pushed through the outer shell and the quiff still came through the dome. radial_fit swells the
    # whole shell where the hair needs room and keeps the padding under the outer wall.
    c0 = Vector((cx, cy, top - 0.12))
    rf = H.radial_fit(h, body, c0, clear=CLEAR, liner=0.002, radius=0.05, log_tag='helmet fit')
    moved = rf; pen1 = H.penetration(h, body); lo, hi = H.bounds(h)
    rec = dict(c0=[round(v, 4) for v in c0], clear=CLEAR, outer=H.outer_clearance(h, body, c0), head_top=round(top, 4), cap_depth=round(hd, 4), cap_width=round(hw, 4), cap_centre=[round(cx, 4), round(cy, 4)],
               margin=MARGIN, mult=MULT, dy=DY, dz=DZ, scale=round(s, 5), merged=merged, size=[round(v, 4) for v in hi - lo],
               lo=[round(v, 4) for v in lo], hi=[round(v, 4) for v in hi], pen_before=pen0, pushed=moved, pen_after=pen1,
               tris=H.tris(h), gap=H.gap_stats(h, body))
    H.log('FIT helmet', json.dumps(rec)); (H.WORK / 'helmet_fit.json').write_text(json.dumps(rec, indent=1))
    H.export_obj(h, H.WORK / 'helmet_fit.obj')
else:
    c = H.import_obj(H.WORK / ('helmet_dec.obj' if STAGE == 'skin' else 'helmet_fit.obj'), 'TS_Helmet')
    H.log('MERGED', H.merge_splits(c))
    rec = json.loads((H.WORK / 'helmet_fit.json').read_text()); c0 = Vector(rec['c0'])
    # decimation moves vertices: touch the clearance up on the final mesh
    H.radial_fit(c, body, c0, clear=rec['clear'], liner=0.002, radius=0.035, iters=4, log_tag='helmet touch-up')
    H.log('OUTER', H.outer_clearance(c, body, c0), 'PEN', H.penetration(c, body))
    H.smooth_shade(c, 50)
    H.clear_groups(c); H.skin_rigid(c, 'Head'); H.log('UNWEIGHTED', H.ensure_weighted(c, 'Head'))
    H.bind(c, arm); (H.WORK / 'stage').mkdir(exist_ok=True)
    H.export_skinned(c, arm, H.WORK / 'stage' / 'TS_Helmet.glb')
