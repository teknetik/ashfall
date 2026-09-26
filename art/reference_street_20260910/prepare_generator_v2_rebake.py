"""STAGED: after source/candidate geometry review, replace distorted near UVs.
Based on crate V4's selected-to-active source PBR projection. Source positions,
source UVs and original maps stay intact. Metric rays must be checked against
thin grille/coil spacing; defaults are starting settings, not a projection pass.
"""
import sys
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *

assert globals().get('GENERATOR_NEAR_GEOMETRY_APPROVED', False) is True, 'Repair/reject geometry failures before attempting to conceal them with textures'
scene = bpy.data.scenes[SCENE]
bpy.context.window.scene = scene
high = bpy.data.objects[scene['generator_source_object']]
near = bpy.data.objects[scene['generator_near_object']]
out = Path(scene['generator_near_output'])
assert not (out / 'rebake-setup.json').exists(), 'Preserve prior bake setup'
assert all(abs(high.matrix_world[r][c] - near.matrix_world[r][c]) < 1e-6 for r in range(4) for c in range(4))
assert np.allclose(np.array(high.matrix_world), np.eye(4), atol=1e-6), 'The bake ray distances require the prepared metric objects'
extrusion = float(globals().get('GENERATOR_CAGE_EXTRUSION_METRES', .0015))
ray_distance = float(globals().get('GENERATOR_MAX_RAY_METRES', .006))
assert 0 < extrusion < ray_distance <= .02
source_contract()
for obj in scene.objects:
    obj.select_set(False)
near.hide_set(False)
near.select_set(True)
bpy.context.view_layer.objects.active = near
while near.data.uv_layers:
    near.data.uv_layers.remove(near.data.uv_layers[0])
near.data.uv_layers.new(name='UVMap')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.006, area_weight=.5, correct_aspect=True, scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
material = bpy.data.materials.new('Generator v2 near rebaked PBR')
material.use_nodes = True
near.data.materials.clear()
near.data.materials.append(material)
settings = cycles_settings(scene, samples=8)
scene.render.bake.use_selected_to_active = True
scene.render.bake.use_clear = True
scene.render.bake.margin = 24
scene.render.bake.cage_extrusion = extrusion
scene.render.bake.max_ray_distance = ray_distance
scene.render.bake.normal_space = 'TANGENT'
scene.render.bake.normal_r, scene.render.bake.normal_g, scene.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
(out / 'model_textures').mkdir(exist_ok=True)
scene['generator_near_uv_state'] = 'New UVMap awaits four selected-to-active source bakes'
write_new(out / 'rebake-setup.json', {'source': str(SOURCE.relative_to(REPO)), 'sourceFbxSha256': sha(SOURCE / 'model.fbx'),
    'sourceTriangles': FBX_TRIANGLES, 'retainedGlbTriangles': 1945352, 'nearTriangles': len(near.data.loop_triangles),
    'uv': 'Smart Project66deg, island margin0.006, area weight0.5; original source UV untouched',
    'bake': 'Cycles selected-to-active; EMIT for nondirectional albedo/scalars; tangent +X/+Y/+Z normal including source original normal map',
    'resolution': [4096, 4096], 'marginPixels': 24, 'cageExtrusionMetres': extrusion, 'maxRayDistanceMetres': ray_distance,
    'geometryRepairedByBake': False, 'projectionAcceptance': False, 'sourceOriginalMapDimensions': {'base_color': [4096,4096], 'normal': [4096,4096], 'metallic': [2048,2048], 'roughness': [2048,2048]},
    'settings': settings, 'blenderMemory': memory_record()})
bpy.data.libraries.write(str(out / 'generator-v2-rebake-setup.blend'), {scene}, fake_user=True)
print(json.dumps({'output': str(out), 'high': high.name, 'near': near.name, 'rayMetres': ray_distance, 'memory': memory_record()}))
