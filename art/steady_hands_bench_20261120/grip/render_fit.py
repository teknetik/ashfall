# Fit and look renders of the grip with what the other families bring: the servo family's gimbal unit and four case
# screws appended from servo/export/servo.blend and placed on the core's pose marks, and the stand-in plates and strap
# that are already in grip.blend. Nothing is saved; review/fit_*.png and review/fit_sheet.jpg are written.
#   SH/blender.sh grip/render_fit.py -- [--samples 48] [--warm] [--only pocket,assembled_l]
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'kit'))
import bpy
from mathutils import Vector, Matrix
import review as RV
import measure as ME

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
opt = lambda k, d, cast=int: cast(argv[argv.index(k) + 1]) if k in argv else d
samples = opt('--samples', 48)
only = opt('--only', None, str)
warm = '--warm' in argv
tag = 'warm_fit_' if warm else 'fit_'
out = os.path.join(HERE, 'review'); os.makedirs(out, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'export', 'grip.blend'))
sc = bpy.context.scene
own = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and 'sh' in o}
UNIT = ['servo_gimbal_cradle', 'servo_gimbal_coil', 'servo_gimbal_ring', 'servo_gimbal_race', 'servo_gimbal_rotor', 'servo_gimbal_retainer']
SCREWS = ['servo_screw_case_a', 'servo_screw_case_b', 'servo_screw_case_c', 'servo_screw_case_d']
servo = os.path.join(HERE, '..', 'servo', 'export', 'servo.blend')
got = {}
if os.path.exists(servo):
    with bpy.data.libraries.load(servo, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        if o is not None:
            sc.collection.objects.link(o)
    bpy.context.view_layer.update()
    for o in dst.objects:
        if o is None:
            continue
        if o.type == 'MESH':
            o.hide_render = o.name not in UNIT + SCREWS
        got[o.name] = o

    def put(name, mark):
        o = got.get(name); e = bpy.data.objects.get(mark)
        if o is None or e is None:
            print('MISSING', name, mark); return
        bpy.context.view_layer.update()
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = e.matrix_world.copy()
        bpy.context.view_layer.update()
    put('servo_gimbal_cradle', 'grip_core__mark_seat_gimbal')
    for n, h in zip(SCREWS, ('lc', 'ld', 'rc', 'rd')):
        put(n, 'grip_core__mark_seat_plate_screw_' + h)
    bpy.context.view_layer.update()
else:
    print('no servo.blend: rendering without the unit')

RV.WARM = warm
RV.studio(samples=samples)
core = own['grip_core']
lo, hi = ME.bounds([core])
c = Vector((lo + hi) / 2)
size = float(max(hi - lo))


def show(names_hidden):
    for n, o in list(own.items()) + [(n, got[n]) for n in UNIT + SCREWS if n in got]:
        o.hide_render = n in names_hidden


L, R, ST = 'materials_sheet_a_plate', 'materials_sheet_b_plate', 'materials_strap_bent'
ALL_EXTRA = [L, R, ST] + UNIT + SCREWS + ['grip_screw_a', 'grip_screw_b', 'grip_seam_l', 'grip_seam_r']
F1, F2 = size * 0.62, size * 0.68
shots = [
    # name, hidden, yaw, down, fit
    ('core_left', ALL_EXTRA, -100, 18, F1),
    ('core_right', ALL_EXTRA, 80, 18, F1),
    ('core_back', ALL_EXTRA, 15, 12, F1),
    ('core_front', ALL_EXTRA, 162, 12, F1),
    ('core_top', ALL_EXTRA, -60, 62, F1),
    ('pocket', [L, 'grip_seam_l', 'grip_screw_a', 'grip_screw_b', SCREWS[0], SCREWS[1]], -105, 16, F1),
    ('pocket_close', [L, 'grip_seam_l', 'grip_screw_a', 'grip_screw_b', SCREWS[0], SCREWS[1]], -90, 10, size * 0.34),
    ('assembled_l', [], -115, 16, F2),
    ('assembled_r', [], 110, 16, F2),
    ('assembled_back', [], 20, 10, F2),
    ('assembled_front', [], 200, 12, F2),
    ('assembled_low', [], -60, -25, F2),
]
paths = []
for name, hidden, yaw, down, fit in shots:
    if only and name not in only.split(','):
        continue
    show(set(hidden))
    tgt = c if 'close' not in name else Vector(bpy.data.objects['grip_core__mark_seat_gimbal'].matrix_world.translation)
    cam = RV.close_cam(tgt, dist=0.3, down=down, yaw=yaw, name='cam_' + name, fit=fit)
    p = os.path.join(out, tag + name + '.png')
    RV.render(p, cam, res=(1200, 1200), samples=samples)
    paths.append(p)
if len(paths) > 1:
    RV.contact_sheet(paths, os.path.join(out, tag + 'sheet.jpg'), cols=4 if len(paths) > 6 else 3, labels=[os.path.basename(p)[len(tag):-4] for p in paths], width=800)
print('FIT RENDERS', len(paths), out)
