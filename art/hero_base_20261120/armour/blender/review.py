"""Review renders (CPU Cycles) of armour pieces on a body.
Usage: blender.sh review.py -- <tag> body=new|old pieces=helmet,vest,... pose=rest|idle:P|walk:P|run:P|clip:<name>:P|rifle|kneel|fist|armsup
                               views=front,back,left,right,q_fl focus=body|<piece>|x,y,z,size [res=WxH] [dir=out|work] [lens=70]
Writes renders/<tag>_<view>.png and renders/<tag>.jpg (contact sheet). `dir=work` reads pieces from work/stage/ (trial
exports), default from out/. body=old shows the shipped body with the shipped pieces (reference for the look)."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, math
from mathutils import Vector, Matrix, Euler, Quaternion
import hlib as H

args = sys.argv[sys.argv.index('--') + 1:]
TAG = args[0]; opt = dict(a.split('=', 1) for a in args[1:] if '=' in a)
BODY = opt.get('body', 'new'); PIECES = [p for p in opt.get('pieces', '').split(',') if p]
POSE = opt.get('pose', 'rest'); VIEWS = opt.get('views', 'front,back,left,right,q_fl').split(',')
FOCUS = opt.get('focus', 'body'); RES = tuple(int(x) for x in opt.get('res', '700x900').split('x'))
SRC = H.OUTD if opt.get('dir', 'out') == 'out' else H.WORK / 'stage'
LENS = float(opt.get('lens', 70)); HIDE_BODY = opt.get('nobody') == '1'


def load():
    if BODY == 'new':
        arm, body = H.load_hero(); src = SRC
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = H.import_glb(H.OLD_BODY); arm = next(o for o in objs if o.type == 'ARMATURE')
        body = max((o for o in objs if o.type == 'MESH'), key=lambda o: len(o.data.vertices)); H.rest(arm); src = H.TS_OLD
    return arm, body, H.load_pieces(arm, PIECES, src)


eval_bounds = H.eval_bounds
arm, body, got = load()
H.set_pose(arm, body, POSE.split('+')[0])
if HIDE_BODY: body.hide_render = True
cam = H.setup_render(RES)


def frame(focus):
    if focus == 'body':
        lo, hi = eval_bounds([body]); return (lo + hi) / 2, (hi.z - lo.z) * 1.04
    if focus in got:
        lo, hi = eval_bounds([got[focus]]); return (lo + hi) / 2, max(hi - lo) * 1.25
    if focus.endswith(('_R', '_L')) and focus[:-2] in got:      # one side of a mirrored piece
        s = -1 if focus.endswith('_R') else 1
        dg = bpy.context.evaluated_depsgraph_get(); o = got[focus[:-2]]; ev = o.evaluated_get(dg); me = ev.to_mesh()
        ws = [o.matrix_world @ v.co for v in me.vertices if (o.matrix_world @ v.co).x * s > 0.02]; ev.to_mesh_clear()
        lo = Vector([min(w[i] for w in ws) for i in range(3)]); hi = Vector([max(w[i] for w in ws) for i in range(3)])
        return (lo + hi) / 2, max(hi - lo) * 1.3
    if focus.startswith('bone:'):                                # bone:<name>:<size>
        _, bn, sz = focus.split(':'); pb = arm.pose.bones[bn]
        return arm.matrix_world @ ((pb.head + pb.tail) / 2), float(sz)
    x, y, z, size = [float(v) for v in focus.split(',')]; return Vector((x, y, z)), size


paths = []
FOCI = FOCUS.split('+'); POSES = POSE.split('+')
for pi, ps in enumerate(POSES):
    if len(POSES) > 1 or pi > 0: H.set_pose(arm, body, ps)
    for fi, focus in enumerate(FOCI):
        centre, size = frame(focus)
        for v in VIEWS:
            paths.append(H.shot(cam, H.REND / f'{TAG}_{pi}_{fi}_{v}.png', centre, size, v, lens=LENS, res=RES))
        print('REVIEW', TAG, ps, focus, 'centre', [round(c, 3) for c in centre], 'size', round(size, 3), flush=True)
H.sheet(paths, H.REND / f'{TAG}.jpg', cols=int(opt.get('cols', len(VIEWS))))
import os
if opt.get('keep') != '1':
    for p_ in paths: os.remove(p_)
