# Inspection renders of the base pistol (and FP hands) in the metric pistol frame.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import pm_common as C

OUT = C.ART + 'work/inspect/'
C.reset()
p = C.import_pistol()
hands = C.import_hands()
C.setup_render(res=(1200, 800), samples=24)
C.world_sky(strength=0.6)
sun = C.sun_lamp(elev=50, azim=150, energy=3.5)
C.ground(z=-0.4)

# bounds
import numpy as np
V = np.array([p.matrix_world @ v.co for v in p.data.vertices])
print('PISTOL metric bounds', V.min(0), V.max(0))
for h in hands:
    H = np.array([h.matrix_world @ v.co for v in h.data.vertices])
    print('HANDS', h.name, H.min(0), H.max(0))

views = {
    'right': ((0, 0.6, 0), (0, -1, 0), (0, 0, 1)),
    'left': ((0, -0.6, 0), (0, 1, 0), (0, 0, 1)),
    'top': ((0, 0, 0.6), (0, 0, -1), (-1, 0, 0)),
    'bottom': ((0, 0, -0.6), (0, 0, 1), (-1, 0, 0)),
    'front': ((-0.6, 0, 0), (1, 0, 0), (0, 0, 1)),
    'back': ((0.6, 0, 0), (-1, 0, 0), (0, 0, 1)),
}
mode = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
for h in hands:
    h.hide_render = True
for n, (loc, d, u) in views.items():
    cam = C.camera('c_' + n, loc, d, u, ortho=0.32)
    C.render(OUT + 'pistol_%s.png' % n, cam)
for h in hands:
    h.hide_render = False
C.render(OUT + 'hands_right.png', C.camera('hr', (0, 0.6, 0), (0, -1, 0), (0, 0, 1), ortho=0.36))
C.render(OUT + 'hands_left.png', C.camera('hl', (0, -0.6, 0), (0, 1, 0), (0, 0, 1), ortho=0.36))
C.render(OUT + 'hands_bottom.png', C.camera('hb', (0, 0, -0.6), (0, 0, 1), (-1, 0, 0), ortho=0.36))
C.render(OUT + 'fp_hip.png', C.fp_camera('hip'))
C.render(OUT + 'fp_ads.png', C.fp_camera('ads'))
