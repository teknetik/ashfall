"""Review renders of the procedural clips (prep_models.py) on the delivered rigs and of the sentinel's body/wheel split.
Headless Blender 5.2, Cycles CPU. renders/review_<rig>_<clip>_<k>.png, renders/review_sentinel_*.png.
Usage: ~/.local/state/ward-programme/blender.sh review_clips.py"""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
HERE = Path(__file__).resolve().parent; OUT = HERE / 'renders'
sys.path.insert(0, str(HERE)); from inspect_models import reset, look, render, import_glb, mesh_bounds  # noqa


def clip_views(rig, clip, fracs, yaw=40, dist=4.0):
    sc, cam = reset(); objs = import_glb(HERE / rig / 'build' / 'clips' / f'{clip}.glb')
    arm = next(o for o in objs if o.type == 'ARMATURE'); act = arm.animation_data.action; fr = act.frame_range
    sc.render.resolution_x = 520; sc.render.resolution_y = 600
    for k, f in enumerate(fracs):
        sc.frame_set(int(round(fr[0] + (fr[1] - fr[0]) * f))); bpy.context.view_layer.update()
        look(cam, Vector((0.3, 0, 0.9)), dist, yaw, 10); render(f'review_{rig}_{clip}_{k}')


for rig in ('warden', 'reaper'):
    clip_views(rig, 'attack', [0.0, 0.3, 0.42, 0.5, 0.56, 0.75])
    clip_views(rig, 'death', [0.0, 0.25, 0.45, 0.65, 0.85, 1.0], yaw=60)
    clip_views(rig, 'hit', [0.0, 0.25, 0.6])
    clip_views(rig, 'idle', [0.0, 0.5])
# sentinel: body + wheel, wheel turned 60 degrees to show the split, and from below the fork
sc, cam = reset(); objs = import_glb(HERE / 'sentinel' / 'build' / 'PostSentinel_geo.glb')
wheel = next(o for o in objs if o.name.startswith('Wheel')); wheel.rotation_mode = 'XYZ'
sc.render.resolution_x = 520; sc.render.resolution_y = 600
for k, deg in enumerate((0, 60)):
    wheel.rotation_euler = (math.radians(deg), 0, 0); bpy.context.view_layer.update()
    look(cam, Vector((0.2, 0, 0.95)), 4.0, 40, 8); render(f'review_sentinel_split_{k}')
look(cam, Vector((0.0, 0, 0.25)), 1.4, 60, -8); render('review_sentinel_wheel_close')
look(cam, Vector((-0.15, 0, 0.7)), 1.6, -60, 0); render('review_sentinel_rifle')
print('REVIEW DONE')
