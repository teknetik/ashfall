"""STAGED: create one comparison candidate only after detailed source inspection.
Set GENERATOR_SOURCE_APPROVED=True following actual source/fit critic review;
GENERATOR_NEAR_TRIANGLES is an experiment, default200000, not acceptance/budget.
The original FBX/GLB/maps and saved source inspection are retained untouched.
"""
import sys
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *
from mathutils import Matrix

assert globals().get('GENERATOR_SOURCE_APPROVED', False) is True, 'Source openings, shape and uniform fit must pass review before near authoring'
TARGET = int(globals().get('GENERATOR_NEAR_TRIANGLES', 200000))
assert 50000 <= TARGET < 1945352, 'Use an explicit defensible comparison target'
OUT = Path(globals().get('GENERATOR_NEAR_OUTPUT', str(SOURCE.parent / ('generator-v2-near-' + str(TARGET)))))
assert not OUT.exists(), 'Preserve prior near work; choose a new derivative revision'
source_contract()
scene = bpy.data.scenes[SCENE]
bpy.context.window.scene = scene
high = bpy.data.objects[scene['generator_source_object']]
assert not scene.get('generator_near_object'), 'Inspect/save this candidate before preparing another in a separate source review session'
# Flatten the already reviewed positive uniform matrix on the in-memory source
# copy. The saved detailed original and prior source review remain unchanged.
for obj in scene.objects:
    obj.select_set(False)
matrix = high.matrix_world.copy()
assert matrix.determinant() > 0
high.parent = None
high.matrix_world = matrix
high.select_set(True)
bpy.context.view_layer.objects.active = high
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
assert all(abs(high.matrix_world[row][column] - Matrix.Identity(4)[row][column]) < 1e-6 for row in range(4) for column in range(4))
near = high.copy()
near.data = high.data.copy()
near.name = 'GENERATOR_V2_NEAR_' + str(TARGET)
scene.collection.objects.link(near)
near.data.calc_loop_triangles()
source_triangles = len(near.data.loop_triangles)
assert source_triangles == FBX_TRIANGLES
high.select_set(False)
near.select_set(True)
bpy.context.view_layer.objects.active = near
modifier = near.modifiers.new('Inspected source near candidate', 'DECIMATE')
modifier.decimate_type = 'COLLAPSE'
modifier.ratio = TARGET / source_triangles
modifier.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=modifier.name)
near.data.calc_loop_triangles()
scene['generator_near_object'] = near.name
scene['generator_source_approval'] = True
scene['generator_near_output'] = str(OUT)
scene['generator_bake_units'] = 'Applied positive uniform metric review transform; source and near matrices are identity in metres'
scene['generator_near_uv_state'] = 'Inherited collapse UVs; mapping NOT accepted'
OUT.mkdir(parents=True)
proof = topology(near)
write_new(OUT / 'near-geometry-comparison.json', {'sourceFbxSha256': sha(SOURCE / 'model.fbx'), 'sourceTriangles': source_triangles,
    'requestedNearTriangles': TARGET, 'actualNearTriangles': len(near.data.loop_triangles), 'sourceRetained': True,
    'uniformMetricSourceMatrixApplied': [list(row) for row in matrix], 'near': proof,
    'normalPolicy': 'Inspect source versus candidate before deciding whether custom normals need correction; no smoothing concealment was applied.',
    'mappingPolicy': 'Collapse preserved source UV attributes but may move paint into triangles. Matched source/candidate renders are mandatory. Geometry distance alone cannot accept mapping.',
    'featureRejection': ['closed/fused grille or cooling gaps', 'lost eyelet apertures', 'flattened frame bends', 'floaters', 'changed decals or stencils', 'projection leakage across nearby parts'],
    'exportReady': False, 'nativeAccepted': False, 'blenderMemory': memory_record()})
bpy.data.libraries.write(str(OUT / 'generator-v2-near-before-rebake.blend'), {scene}, fake_user=True)
source_contract()
print(json.dumps({'source': high.name, 'near': near.name, 'triangles': len(near.data.loop_triangles), 'output': str(OUT), 'memory': memory_record()}))
