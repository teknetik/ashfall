# Look at the exported, baked GLB (what a plain viewer and Unity get), framed on the servo, under the kit's calibrated
# rigs (kit/READY.md: a white card of albedo 0.8 reads about 0.9 in scene-linear; the kit puts a white and a grey card
# in every frame): neutral and the warm bench lamp, at 0.3 m, at the bench camera (0.6 m) and opened.
# The kit's `review.py --glb` frames on every imported mesh, and the glTF importer adds a bone-shape mesh per armature
# far from the model, so its frames come out as specks for a family with rigs. This script drops those meshes.
# 21 Nov: the warm panels used to be the neutral rig recoloured by hand; they are now the kit's own warm rig.
#   SH/blender.sh servo/src/glb_view.py [-- --samples 24]       -> review/glb_views.png
import bpy, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import kitload
RV = kitload.load('review')
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SPP = int(argv[argv.index('--samples') + 1]) if '--samples' in argv else 24
OUT = os.path.join(HERE, '..', 'review')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, '..', 'export', 'servo.glb'))
for o in list(bpy.data.objects):
    if o.type == 'MESH' and not o.name.startswith('servo_'):
        bpy.data.objects.remove(o)
C = Vector((0, 0, 0.0275))
LID = ('servo_case_lid', 'servo_screw_case_a', 'servo_screw_case_b', 'servo_screw_case_c', 'servo_screw_case_d', 'servo_board',
       'servo_trim_resistor', 'servo_lead_plug')
ground = None
done = {}


def rig(warm):
    global ground
    for o in list(bpy.data.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o)
    for l in list(bpy.data.lights):
        bpy.data.lights.remove(l)
    RV.studio(samples=SPP, warm=warm)
    if ground is None:
        ground = RV.ground(-0.0002, (0.028, 0.028, 0.03))


def opened(on):
    for n in LID:
        o = bpy.data.objects.get(n)
        if o:
            o.hide_render = on


for warm, k in ((True, '_warm'), (False, '')):
    rig(warm)
    opened(False)
    done['close' + k] = RV.render(os.path.join(OUT, 'glb_close%s.png' % k), RV.close_cam(C, dist=0.30, down=32, yaw=-60, name='ga' + k, fit=0.105), (1200, 800), SPP)
    done['bench' + k] = RV.render(os.path.join(OUT, 'glb_bench%s.png' % k), RV.bench_cam(C, yaw=-70, name='gn' + k), (1200, 800), SPP)
    opened(True)
    done['open' + k] = RV.render(os.path.join(OUT, 'glb_open%s.png' % k), RV.close_cam(C + Vector((0.006, 0, 0.004)), dist=0.30, down=52, yaw=-65, name='gb' + k, fit=0.092), (1200, 800), SPP)
opened(False)
keys = ['close_warm', 'bench_warm', 'open_warm', 'close', 'bench', 'open']
RV.contact_sheet([done[k] for k in keys], os.path.join(OUT, 'glb_views.png'), cols=3,
                 labels=['exported GLB, baked 2048, clean set, 0.3 m, WARM key (kit rig)', 'the same, bench camera 0.6 m, WARM',
                         'lid and board hidden, WARM', 'clean set, 0.3 m, neutral (kit rig)', 'bench camera 0.6 m, neutral',
                         'lid and board hidden, neutral'])
print('GLBVIEW done')
