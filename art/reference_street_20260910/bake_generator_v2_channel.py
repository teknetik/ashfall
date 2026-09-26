"""STAGED: one channel per live-Blender MCP call, after rebake setup.
Set GENERATOR_BAKE_CHANNEL to base_color, metallic, roughness or normal.
Never retry over a completed image; inspect/retain failures in a new revision.
"""
import sys
import time
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *

channel = globals().get('GENERATOR_BAKE_CHANNEL', 'base_color')
assert channel in CHANNELS
scene = bpy.data.scenes[SCENE]
bpy.context.window.scene = scene
high = bpy.data.objects[scene['generator_source_object']]
near = bpy.data.objects[scene['generator_near_object']]
out = Path(scene['generator_near_output'])
assert (out / 'rebake-setup.json').exists()
path = out / 'model_textures' / (channel + '.png')
assert not path.exists(), 'Preserve previous channel output'
source_nodes = high.data.materials[0].node_tree.nodes
links = high.data.materials[0].node_tree.links
output = source_nodes.get('Material Output')
for link in list(output.inputs['Surface'].links):
    links.remove(link)
if channel == 'normal':
    links.new(source_nodes.get('Principled BSDF').outputs['BSDF'], output.inputs['Surface'])
else:
    emission = source_nodes.get('BAKE_EMISSION') or source_nodes.new('ShaderNodeEmission')
    emission.name = 'BAKE_EMISSION'
    emission.inputs['Strength'].default_value = 1
    for link in list(emission.inputs['Color'].links):
        links.remove(link)
    links.new(source_nodes['SOURCE_' + channel].outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs[0], output.inputs['Surface'])
image = bpy.data.images.new('GENERATOR_V2_BAKED_' + channel, width=4096, height=4096, alpha=False, float_buffer=False)
image.colorspace_settings.name = 'sRGB' if channel == 'base_color' else 'Non-Color'
image.filepath_raw = str(path)
image.file_format = 'PNG'
material = near.data.materials[0]
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.name = 'BAKED_' + channel
node.image = image
for item in material.node_tree.nodes:
    item.select = False
node.select = True
material.node_tree.nodes.active = node
for obj in scene.objects:
    obj.select_set(False)
for obj in (high, near):
    obj.hide_set(False)
    obj.hide_render = False
    obj.select_set(True)
bpy.context.view_layer.objects.active = near
start = time.time()
try:
    bpy.ops.object.bake(type='NORMAL' if channel == 'normal' else 'EMIT')
    image.save()
finally:
    # Always restore source shading, including after an interrupted/failed channel.
    for link in list(output.inputs['Surface'].links):
        links.remove(link)
    links.new(source_nodes.get('Principled BSDF').outputs['BSDF'], output.inputs['Surface'])
write_new(out / ('bake-' + channel + '.json'), {'channel': channel, 'seconds': time.time() - start, 'dimensions': list(image.size),
    'colorspace': image.colorspace_settings.name, 'path': str(path), 'sha256': sha(path),
    'method': 'Full source and its original normal texture into near tangent GL+Y space' if channel == 'normal' else 'Selected-source EMIT projection without scene lighting',
    'projectionAccepted': False, 'blenderMemory': memory_record()})
# Save a recoverable session without overwriting the source review or previous channels.
bpy.data.libraries.write(str(out / ('generator-v2-after-' + channel + '.blend')), {scene}, fake_user=True)
print(json.dumps({'channel': channel, 'seconds': time.time() - start, 'output': str(path), 'memory': memory_record()}))
