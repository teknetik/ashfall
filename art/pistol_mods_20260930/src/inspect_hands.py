# Views of the FP hands on the pistol from below/behind, to find free space for grip hardware.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import pm_common as C

OUT = C.ART + 'work/inspect/'
C.reset()
p = C.import_pistol()
hands = C.import_hands()
C.setup_render(res=(900, 700), samples=16)
C.world_sky(strength=0.9)
C.sun_lamp(elev=50, azim=150, energy=2.5)
tgt = Vector((0.08, 0, -0.04))
views = {
    'h_backlow': Vector((0.45, 0.0, -0.25)),
    'h_under_r': Vector((0.15, 0.35, -0.3)),
    'h_under_l': Vector((0.15, -0.35, -0.3)),
    'h_front_low': Vector((-0.35, 0.15, -0.2)),
    'h_top_back': Vector((0.35, 0.1, 0.3)),
}
for n, loc in views.items():
    C.render(OUT + n + '.png', C.camera(n, tgt + loc, -loc, (0, 0, 1), fov_deg=35))
