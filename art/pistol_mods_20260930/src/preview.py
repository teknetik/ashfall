# Quick modelling previews (procedural materials, low samples). Usage: preview.py -- <mod> [<mod>...]
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
import pm_common as C
import pm_geo as G
import pm_mats as PM

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = C.ART + 'work/preview/'
C.reset()
pistol = C.import_pistol()
hands = C.import_hands()
for h in hands:
    h.hide_render = True
M = PM.library()
import mods_barrel as MB, mods_cell as MC, mods_grip as MG
builders = {'barrel_bored_alloy': MB.build_bored_alloy, 'barrel_lattice_focused': MB.build_lattice_focused,
            'cell_salvaged_capacitor': MC.build_capacitor, 'cell_overclocked': MC.build_overclocked,
            'grip_stabilised_pistol': MG.build_stabilised, 'grip_gyro_braced': MG.build_gyro}
C.setup_render(res=(1100, 760), samples=int(os.environ.get('PM_SAMPLES', '40')))
C.world_sky(strength=0.7, sun_elev=45, sun_rot=200)
C.sun_lamp(elev=45, azim=200, energy=4.0)
C.ground(z=-0.35)
for name in args:
    obj, extra = builders[name](M)
    print('BUILT', name, 'tris', G.tris(obj), 'extra', extra)
    bb = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    ctr = sum(bb, Vector()) / 8
    size = max((bb[6] - bb[0]).length, 0.05)
    views = {'r34': Vector((-0.6, 0.7, 0.45)), 'l34': Vector((0.5, -0.8, 0.35)), 'back': Vector((0.9, -0.25, 0.45)),
             'low': Vector((-0.3, 0.6, -0.5))}
    if os.environ.get('PM_VIEWS'):
        views = {k: v for k, v in views.items() if k in os.environ['PM_VIEWS'].split(',')}
    for vn, d in views.items():
        d = d.normalized()
        cam = C.camera('c', ctr + d * size * 2.6, -d, (0, 0, 1), fov_deg=30)
        C.render(OUT + '%s_%s.png' % (name, vn), cam)
    if os.environ.get('PM_HANDS'):
        for h in hands:
            h.hide_render = False
        C.render(OUT + '%s_fphip.png' % name, C.fp_camera('hip'))
        for h in hands:
            h.hide_render = True
    obj.hide_render = True
