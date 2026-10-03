import bpy, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); from inspect_models import reset, look, render, import_glb  # noqa
for rig in ('warden', 'reaper'):
    sc, cam = reset(); objs = import_glb(HERE / rig / 'build' / 'clips' / 'attack.glb')
    arm = next(o for o in objs if o.type == 'ARMATURE'); fr = arm.animation_data.action.frame_range
    sc.render.resolution_x = 420; sc.render.resolution_y = 520
    for k, f in enumerate([0.0, 0.42, 0.5, 0.56]):
        sc.frame_set(int(round(fr[0] + (fr[1] - fr[0]) * f))); bpy.context.view_layer.update()
        look(cam, Vector((0.0, 0, 0.95)), 3.6, 90, 5); render(f'side_{rig}_attack_{k}')
        look(cam, Vector((0.0, 0, 0.95)), 3.6, 0, 5); render(f'front_{rig}_attack_{k}')
print('SIDE DONE')
