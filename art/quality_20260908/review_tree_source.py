"""Run through the live Blender MCP; preserve the downloaded original blend."""
import bpy, pathlib, json, math
from mathutils import Vector

ROOT = pathlib.Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/quality_20260908/tree'
SOURCE = ROOT / 'refs/quality_20260908/tree/jacaranda_tree/jacaranda_tree_4k.blend'
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
if pathlib.Path(bpy.data.filepath) != SOURCE:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False, use_scripts=False)
scene = bpy.context.scene
for obj in bpy.data.objects:
    obj.hide_render = obj.name != 'jacaranda_tree_LOD0'
for collection in bpy.data.collections:
    collection.hide_render = False
    collection.hide_viewport = False
def enable_layer(layer):
    layer.exclude = False
    layer.hide_viewport = False
    for child in layer.children:
        enable_layer(child)
enable_layer(bpy.context.view_layer.layer_collection)
tree = bpy.data.objects['jacaranda_tree_LOD0']
tree.hide_set(False)
points = [tree.matrix_world @ v.co for v in tree.data.vertices]
mins = [min(p[i] for p in points) for i in range(3)]
maxs = [max(p[i] for p in points) for i in range(3)]
base = [p for p in points if p.z < mins[2] + .5]
print(json.dumps({'bounds': [mins, maxs], 'baseBounds': [[min(p[i] for p in base) for i in range(3)], [max(p[i] for p in base) for i in range(3)]]}))
world = bpy.data.worlds.new('Ward source review world')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.40, .53, .70, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
scene.world = world
stage = bpy.data.collections.new('Ward source review stage')
scene.collection.children.link(stage)
def link(obj):
    stage.objects.link(obj)
    return obj
sun_data = bpy.data.lights.new('Review sun', 'SUN')
sun_data.energy = 2.4
sun_data.angle = math.radians(2)
sun_data.color = (1, .86, .68)
sun = link(bpy.data.objects.new('Review sun', sun_data))
sun.rotation_euler = tuple(math.radians(v) for v in (34, -25, -32))
ground_data = bpy.data.meshes.new('Review ground')
ground_data.from_pydata([(-60,-60,mins[2]-.025),(60,-60,mins[2]-.025),(60,60,mins[2]-.025),(-60,60,mins[2]-.025)], [], [(0,1,2,3)])
ground = link(bpy.data.objects.new('Review ground', ground_data))
mat = bpy.data.materials.new('Review neutral stone')
mat.diffuse_color = (.31,.27,.21,1)
mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.31,.27,.21,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .85
ground.data.materials.append(mat)
camera = link(bpy.data.objects.new('Ward tree source camera', bpy.data.cameras.new('Ward tree source camera')))
scene.camera = camera
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.device = 'GPU'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'CUDA'
except Exception:
    scene.cycles.device = 'CPU'
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
camera.data.lens = 45
views = [('source-whole', (26,-33,15), (0,0,9)), ('source-trunk', (6,-8,3.0), (0,0,3.7)), ('source-roots', (3.5,-4.5,1.8), (0,0,.75))]
for name, position, target in views:
    camera.location = position
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = str(OUT / (name+'.png'))
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'tree-source-review.blend'))
print('Source review saved; original is unchanged.')
