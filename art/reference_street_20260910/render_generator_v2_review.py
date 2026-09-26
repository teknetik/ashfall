"""STAGED: render one generator view/variant per live-Blender MCP call.
GENERATOR_VIEW: front, back, left, right, top_oblique, grille_close,
rear_panel_close, top_fittings_close. GENERATOR_VARIANT: source or near.
GENERATOR_RENDER_TAG names immutable evidence, e.g. source, shared-uv, rebaked.
Front/back are provisional -Y/+Y labels until source reference comparison.
"""
import sys
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *

VIEW = globals().get('GENERATOR_VIEW', 'front')
VARIANT = globals().get('GENERATOR_VARIANT', 'source')
TAG = globals().get('GENERATOR_RENDER_TAG', 'source' if VARIANT == 'source' else 'shared-uv')
assert VARIANT in ('source', 'near')
assert TAG and all(c.isalnum() or c in '-_' for c in TAG)
scene = bpy.data.scenes[SCENE]
bpy.context.window.scene = scene
high = bpy.data.objects[scene['generator_source_object']]
near = bpy.data.objects.get(scene.get('generator_near_object', ''))
assert VARIANT != 'near' or near, 'Prepare the staged near candidate after source approval'
out = Path(scene['generator_review_output']) / 'renders'
out.mkdir(exist_ok=True)
path = out / (VIEW + '-' + TAG + '-' + VARIANT + '.png')
assert not path.exists(), 'Preserve prior matched-view evidence'
views = {
    'front': ((0, -4, .65), (0, 0, .55), 'ORTHO', 1.8),
    'back': ((0, 4, .65), (0, 0, .55), 'ORTHO', 1.8),
    'left': ((-4, 0, .65), (0, 0, .55), 'ORTHO', 1.65),
    'right': ((4, 0, .65), (0, 0, .55), 'ORTHO', 1.65),
    'top_oblique': ((2.4, -3.2, 2), (0, 0, .53), 'PERSP', 65),
    'grille_close': ((.12, -1.4, .76), (0, -.24, .60), 'PERSP', 70),
    'rear_panel_close': ((-.18, 1.4, .76), (0, .24, .60), 'PERSP', 70),
    'top_fittings_close': ((.75, -1.1, 1.45), (.36, 0, .99), 'PERSP', 78),
}
assert VIEW in views, 'Unknown view'
position, target, kind, framing = views[VIEW]
# A deliberate framing correction can be supplied after the whole-object views;
# record it and use the same override for both source and near comparison images.
override = globals().get('GENERATOR_CAMERA_OVERRIDE')
if override:
    position, target, kind, framing = override['position'], override['target'], override['type'], override['framing']
cam = scene.camera
cam.location = position
cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.type = kind
if kind == 'ORTHO':
    cam.data.ortho_scale = framing
else:
    cam.data.lens = framing
cam.data.clip_start = .01
cam.data.clip_end = 100
cam.data.dof.use_dof = False
high.hide_render = VARIANT != 'source'
if near:
    near.hide_render = VARIANT != 'near'
scene.render.filepath = str(path)
bpy.ops.render.render(write_still=True)
write_new(path.with_suffix('.json'), {'view': VIEW, 'variant': VARIANT, 'renderTag': TAG, 'image': str(path),
    'position': list(cam.location), 'target': list(target), 'cameraRotation': list(cam.rotation_euler), 'cameraType': kind,
    'framing': framing, 'sourceMatrix': [list(row) for row in high.matrix_world],
    'nearMatrix': [list(row) for row in near.matrix_world] if near else None, 'settings': {'samples': scene.cycles.samples,
    'device': scene.cycles.device, 'resolution': [scene.render.resolution_x, scene.render.resolution_y],
    'resolutionPercentage': scene.render.resolution_percentage, 'exposure': scene.view_settings.exposure,
    'viewTransform': scene.view_settings.view_transform}, 'blenderMemory': memory_record(),
    'comparisonMethod': 'Only model visibility changes between variants. Camera, position, exposure, lights and floor remain matched; each variant uses its own assigned PBR material.',
    'nativeAcceptance': False})
print(json.dumps({'render': str(path), 'memory': memory_record()}))
