"""Poke-through numbers in motion: for each pose, every piece's vertices against the DEFORMED body (inside count,
deeper than 3 mm, worst depth). Usage: blender.sh check_motion.py -- [pieces=helmet,vest,...] [poses=a,b,c] [tag=motion]
Writes work/<tag>.json. Poses as in hlib.set_pose."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, json
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []; opt = dict(a.split('=', 1) for a in args if '=' in a)
PIECES = opt.get('pieces', 'helmet,vest,carrier,arms,gloves,legs,boots').split(',')
POSES = opt.get('poses', 'rest,idle:0,idle:50,walk:0,walk:25,walk:50,walk:75,run:0,run:25,run:50,run:75,rifle,kneel,fist,'
                         'clip:rifle_573:50,clip:aim_95:50,clip:carry_334:50,clip:draw_222:50').split(',')
TAG = opt.get('tag', 'motion')
arm, body = H.load_hero(); got = H.load_pieces(arm, PIECES)
out = {}
for pose in POSES:
    H.set_pose(arm, body, pose); row = {}
    for k in PIECES: row[k] = H.posed_penetration(got[k], body)
    out[pose] = row
    print('MOTION %-22s' % pose, '  '.join('%s %d/%d/%.0f' % (k[:4], r['inside'], r['deeper_3mm'], r['worst_mm']) for k, r in row.items()), flush=True)
(H.WORK / f'{TAG}.json').write_text(json.dumps(out, indent=1))
