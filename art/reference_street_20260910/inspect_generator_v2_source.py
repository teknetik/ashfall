"""STAGED: run in a minimal live Blender via MCP only after app handover.
Imports the untouched full FBX, makes a uniform metric review fit, records source
and topology/fit diagnostics, and saves a source-review scene. No renders or LOD
are made in this step. Render one view per call with render_generator_v2_review.py.
"""
import sys
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *
from mathutils import Matrix

OUT = Path(globals().get('GENERATOR_REVIEW_OUTPUT', str(SOURCE / 'source-review-v1')))
YAW = float(globals().get('GENERATOR_YAW_DEGREES', 0))
assert YAW in (0, 90, 180, 270), 'Review axis rotation must be an explicit right angle'
assert not OUT.exists(), 'Preserve previous review; choose a new output revision'
assert SCENE not in bpy.data.scenes, 'A generator inspection scene already exists; preserve and inspect it before loading another'
assert sum(len(mesh.polygons) for mesh in bpy.data.meshes) <= 12, 'Use the handed-over minimal Blender scene; do not pile source assets into a prior heavy session'
record = source_contract()
OUT.mkdir(parents=True)
scene = bpy.data.scenes.new(SCENE)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
settings = cycles_settings(scene)
before = set(scene.objects)
bpy.ops.import_scene.fbx(filepath=str(SOURCE / 'model.fbx'))
imported = [obj for obj in scene.objects if obj not in before]
objects = [obj for obj in imported if obj.type == 'MESH']
assert len(objects) == 1, 'Expected one Meshy static source mesh; inspect unexpected scene content before joining anything'
obj = objects[0]
obj.name = HIGH
obj.data.calc_loop_triangles()
assert len(obj.data.loop_triangles) == FBX_TRIANGLES, 'Imported FBX differs from its verified retained polygon count'
raw_matrix = obj.matrix_world.copy()
yaw_matrix = Matrix.Rotation(math.radians(YAW), 4, 'Z')
obj.matrix_world = yaw_matrix @ raw_matrix
bpy.context.view_layer.update()
vertices = world_vertices(obj)
lo, hi = vertices.min(axis=0), vertices.max(axis=0)
size = hi - lo
# Blender XYZ maps to Unity X,Z,Y. It is an envelope, not three independent scales.
canonical = np.array([1.6, .95, 1.1])
scale = float(np.min(canonical / size))
center = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
fit_matrix = Matrix.Translation(Vector((-center * scale).tolist())) @ Matrix.Scale(scale, 4)
obj.matrix_world = fit_matrix @ obj.matrix_world
bpy.context.view_layer.update()
material, dimensions = pbr_material('Generator v2 full original PBR', SOURCE / 'model_textures')
assert dimensions == record['actualMapDimensions'], 'Actual loaded map dimensions differ from the task record'
obj.data.materials.clear()
obj.data.materials.append(material)
for face in obj.data.polygons:
    face.material_index = 0
proof = topology(obj)
fitted = np.array(proof['boundsMetres'])
assert np.all(fitted[1] - fitted[0] <= canonical + 1e-6)
assert abs(fitted[0, 2]) < 1e-6
assert np.max(np.abs((fitted[1] - fitted[0]) / size - scale)) < 1e-6
scene.world = bpy.data.worlds.new('Generator neutral review sky')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.38, .43, .50, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .55
bpy.ops.mesh.primitive_plane_add(size=40)
floor = bpy.context.object
floor.name = 'Generator review ground (not export)'
floor.location.z = -.002
floor_material = bpy.data.materials.new('Generator neutral review floor')
floor_material.diffuse_color = (.19, .20, .21, 1)
floor.data.materials.append(floor_material)
for name, position, energy, size in [('Key', (-3, -4, 5), 900, 4), ('Fill', (4, -2, 3), 400, 5), ('Rim', (1, 4, 4), 650, 3)]:
    data = bpy.data.lights.new('Generator review ' + name, 'AREA')
    data.energy, data.shape, data.size = energy, 'DISK', size
    light = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(light)
    light.location = position
    light.rotation_euler = (Vector((0, 0, .55)) - light.location).to_track_quat('-Z', 'Y').to_euler()
data = bpy.data.cameras.new('Generator metric review camera')
cam = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(cam)
cam.location = (0, -4, .65)
cam.rotation_euler = (Vector((0, 0, .55)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
data.type, data.ortho_scale = 'ORTHO', 1.8
scene.camera = cam
scene['generator_review_output'] = str(OUT)
scene['generator_source_object'] = obj.name
scene['generator_near_object'] = ''
scene['generator_source_approval'] = False
scene['generator_fit_yaw_degrees'] = YAW
scene['generator_bake_units'] = 'Review in metres; apply positive uniform source transform only on derivative preparation'
write_new(OUT / 'source-topology-fit.json', {'taskId': record['task_id'], 'sourceFbxSha256': sha(SOURCE / 'model.fbx'),
    'sourceOriginalsRetained': True, 'rawImportMatrix': [list(row) for row in raw_matrix], 'yawDegrees': YAW,
    'rawReviewBoundsBlender': [lo.tolist(), hi.tolist()], 'uniformFitFactor': scale, 'canonicalUnityXYZMetres': [1.6, 1.1, .95],
    'canonicalBlenderXYZMetres': canonical.tolist(), 'fittedUnityXYZMetres': (fitted[1] - fitted[0])[[0, 2, 1]].tolist(),
    'fitProof': 'Single positive scale; X/Y/Z dimension ratios equal. Bottom-centred pivot in world metre review. Unused envelope space is retained.',
    'source': proof, 'actualPbrDimensions': dimensions, 'settings': settings, 'blenderMemory': memory_record(),
    'orientationAcceptance': 'Pending view inspection. Axis-labelled front/back are provisional until compared with original references.',
    'geometryAcceptance': False, 'nativeAccepted': False})
bpy.data.libraries.write(str(OUT / 'generator-v2-source-review.blend'), {scene}, fake_user=True)
source_contract()
print(json.dumps({'scene': scene.name, 'sourceObject': obj.name, 'output': str(OUT), 'triangles': FBX_TRIANGLES,
                  'fittedUnityXYZMetres': (fitted[1] - fitted[0])[[0, 2, 1]].tolist(), 'memory': memory_record()}))
