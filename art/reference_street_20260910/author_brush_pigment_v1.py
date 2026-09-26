"""Author original pigment breakup in the live Blender material studio.

This is material authoring, not an edit to the supplied reference image. Retain
the two existing brush meshes, phrase, slat gaps and all previous source maps.
AUTHOR creates a small independent scene; BAKE writes one unlit channel.
"""
import bpy
import hashlib
import json
import math
import time
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910/brush-pigment-v1'
STUDIO = 'Field Supply worn brush pigment v1'
ACTION = globals().get('PIGMENT_ACTION', 'AUTHOR')
CHANNEL = globals().get('PIGMENT_CHANNEL', 'BaseColor')


def author():
    assert STUDIO not in bpy.data.scenes
    assert not (OUT / 'brush-pigment-source-v1.blend').exists()
    scene = bpy.data.scenes.new(STUDIO)
    bpy.context.window.scene = scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'; prefs.get_devices()
        for dev in prefs.devices: dev.use = dev.type == 'CUDA'
        scene.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
    except Exception:
        scene.cycles.device = 'CPU'
    mesh = bpy.data.meshes.new(STUDIO + ' plane')
    mesh.from_pydata([(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], [], [(0, 1, 2, 3)])
    mesh.update(); uv = mesh.uv_layers.new(name='Two metre pigment tile')
    for loop, point in zip(mesh.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = point
    obj = bpy.data.objects.new(STUDIO + ' plane', mesh); scene.collection.objects.link(obj)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    mat = bpy.data.materials.new(STUDIO); mat.use_nodes = True
    mesh.materials.append(mat)
    ns, links = mat.node_tree.nodes, mat.node_tree.links; ns.clear()

    def node(kind, name):
        n = ns.new(kind); n.name = n.label = name; return n

    def wire(value, socket):
        if hasattr(value, 'node'): links.new(value, socket)
        elif isinstance(value, (float, int)) and hasattr(socket.default_value, '__len__'):
            socket.default_value = [value] * len(socket.default_value)
        else: socket.default_value = value

    def calc(op, a, b=0, name=None):
        n = node('ShaderNodeMath', name or op); n.operation = op
        wire(a, n.inputs[0]); wire(b, n.inputs[1]); return n.outputs[0]

    def ramp(value, low, high, name):
        n = node('ShaderNodeMapRange', name); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = low; n.inputs['From Max'].default_value = high
        wire(value, n.inputs['Value']); return n.outputs['Result']

    uvn = node('ShaderNodeTexCoord', 'Retained physical UV coordinates')

    def noise(scale, name, detail=2):
        vector = node('ShaderNodeVectorMath', name + ' metric scale'); vector.operation = 'MULTIPLY'
        vector.inputs[1].default_value = (*[2 * s for s in scale], 1)
        links.new(uvn.outputs['UV'], vector.inputs[0])
        n = node('ShaderNodeTexNoise', name); n.inputs['Scale'].default_value = 1
        n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = .65
        links.new(vector.outputs[0], n.inputs['Vector']); return n.outputs['Fac']

    grain = noise((210, 230), 'Submillimetre pigment aggregate')
    chips = noise((93, 118), 'Sparse millimetre coating losses')
    brush = noise((85, 9), 'Small dry brush streaks')
    broad = noise((4.4, 5.2), 'Unequal retained paint thickness')
    # Keep most strokes continuous. Only the upper tail of a broken flake field
    # removes paint; no regular polka dots or equal coverage on every glyph.
    flake = ramp(chips, .655, .765, 'Sparse detached pigment')
    flake = calc('MULTIPLY', flake, ramp(broad, .34, .60, 'Localized paint failure'))
    brush_loss = calc('MULTIPLY', ramp(brush, .665, .78, 'Fine dry brush gaps'), .68)
    loss = calc('MAXIMUM', flake, brush_loss)
    alpha = calc('SUBTRACT', 1, calc('MINIMUM', 1, calc('MULTIPLY', loss, 2.25)))
    modulation = calc('ADD', .84, calc('ADD', calc('MULTIPLY', broad, .16), calc('MULTIPLY', grain, .08)))
    color = node('ShaderNodeMixRGB', 'Matte bone pigment with internal variation'); color.blend_type = 'MULTIPLY'
    color.inputs[0].default_value = 1; color.inputs[1].default_value = (.73, .66, .53, 1)
    links.new(modulation, color.inputs[2])
    rough = calc('ADD', .88, calc('MULTIPLY', grain, .1))
    bs = node('ShaderNodeBsdfPrincipled', 'Physical pigment')
    links.new(color.outputs[0], bs.inputs['Base Color']); wire(rough, bs.inputs['Roughness'])
    wire(alpha, bs.inputs['Alpha']); bs.inputs['Metallic'].default_value = 0
    output = node('ShaderNodeOutputMaterial', 'Output'); links.new(bs.outputs[0], output.inputs['Surface'])
    for channel, value in [('BaseColor', color.outputs[0]), ('Roughness', rough), ('Opacity', alpha)]:
        emission = node('ShaderNodeEmission', 'Bake ' + channel); wire(value, emission.inputs['Color'])
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'art/reference_street_20260909/brush-graffiti-meshes-v3.json'
    contract = {'sourceMeshExport': str(source.relative_to(ROOT)), 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'metres': [2, 2], 'resolution': [4096, 4096], 'sourceUVMetres': 4,
                'baseMapScale': [2, 2], 'baseColorTint': [1, 1, 1, 1],
                'nativeMaterial': 'Standard URP Lit, alpha clip 0.45, opaque depth, shadow casting remains disabled on the existing two meshes, metallic zero.',
                'scope': 'Pigment map candidate only; geometry, UV0, phrase, slat gaps and all source originals unchanged.',
                'reviewRequired': 'Review pigment coverage and phrase readability on the exact two meshes with the new shutter, then native noon/shade moving views. Do not infer acceptance from the bake.'}
    (OUT / 'authoring-contract.json').write_text(json.dumps(contract, indent=2))
    bpy.data.libraries.write(str(OUT / 'brush-pigment-source-v1.blend'), {scene}, fake_user=True)
    print(json.dumps({'authored': STUDIO, 'nativeAccepted': False}))


def bake():
    assert CHANNEL in ['BaseColor', 'Roughness', 'Opacity']
    path = OUT / (CHANNEL + '.png'); assert not path.exists()
    scene = bpy.data.scenes[STUDIO]; bpy.context.window.scene = scene
    obj = scene.objects[STUDIO + ' plane']
    for item in scene.objects: item.select_set(False)
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    mat = obj.data.materials[0]; nt = mat.node_tree
    image = bpy.data.images.new(STUDIO + ' ' + CHANNEL, 4096, 4096, alpha=False)
    image.colorspace_settings.name = 'sRGB' if CHANNEL == 'BaseColor' else 'Non-Color'
    target = nt.nodes.new('ShaderNodeTexImage'); target.image = image
    for n in nt.nodes: n.select = n == target
    nt.nodes.active = target
    nt.links.new(nt.nodes['Bake ' + CHANNEL].outputs[0], nt.nodes['Output'].inputs['Surface'])
    started = time.monotonic()
    try:
        bpy.ops.object.bake(type='EMIT', use_clear=True, margin=16)
        image.filepath_raw = str(path); image.file_format = 'PNG'; image.save()
    finally:
        nt.links.new(nt.nodes['Physical pigment'].outputs[0], nt.nodes['Output'].inputs['Surface'])
        nt.nodes.remove(target); bpy.data.images.remove(image)
    record = {'channel': CHANNEL, 'seconds': time.monotonic() - started, 'resolution': [4096, 4096],
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'blender': bpy.app.version_string,
              'lightingBaked': False}
    path.with_suffix('.json').write_text(json.dumps(record, indent=2)); print(json.dumps(record))


if ACTION == 'AUTHOR': author()
elif ACTION == 'BAKE': bake()
else: raise ValueError('Use AUTHOR or BAKE explicitly')
