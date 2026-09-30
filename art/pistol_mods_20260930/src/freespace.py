# ASCII free-space maps around the grip: '#' pistol-near (<1.5mm), 'H' hand within 3 mm, '.' free, '+' free but hand within 8 mm
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import pm_common as C

C.reset()
p = C.import_pistol()
hands = C.import_hands()
def bvh(objs):
    bm = bmesh.new()
    for h in objs:
        tmp = bmesh.new(); tmp.from_mesh(h.data); tmp.transform(h.matrix_world)
        me = bpy.data.meshes.new('t'); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me)
    return BVHTree.FromBMesh(bm)
hb = bvh(hands); pb = bvh([p])
mode = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'xy'
def ch(pt):
    dh = hb.find_nearest(pt, 0.02); dp = pb.find_nearest(pt, 0.02)
    dh = dh[3] if dh[0] is not None else 1; dp = dp[3] if dp[0] is not None else 1
    if dp < .0015: return '#'
    if dh < .003: return 'H'
    if dh < .008: return '+'
    return '.'
step = 0.004
if mode == 'xy':  # horizontal slices below/around the grip base, x rows, y columns
    for z in (-0.07, -0.08, -0.088, -0.095, -0.105, -0.115):
        print('--- z=%.3f  (rows x from -0.02 to 0.20, cols y -0.06..0.06)' % z)
        for x in np.arange(-0.02, 0.2, step):
            print('%6.3f ' % x + ''.join(ch(Vector((x, y, z))) for y in np.arange(-0.06, 0.06, step / 2)))
elif mode == 'xz':  # vertical slices at given y: rows z, cols x
    for y in (-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03):
        print('--- y=%.3f (rows z 0.07..-0.13, cols x -0.14..0.20)' % y)
        for z in np.arange(0.07, -0.13, -step):
            print('%6.3f ' % z + ''.join(ch(Vector((x, y, z))) for x in np.arange(-0.14, 0.2, step / 2)))
