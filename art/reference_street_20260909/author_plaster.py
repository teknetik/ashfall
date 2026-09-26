"""Author the reference street plaster in the live Blender MCP session.

Run this file once to create an independent editable bake studio and export the
material/placement contract. Then call bake_reference_plaster('Plaster') and
bake_reference_plaster('MineralRunoff') through the same live MCP connection.
No existing source, Unity asset, wall geometry, collider or scene is changed.
"""
import hashlib
import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260909'
SOURCE = ROOT / 'refs/quality_20260909/building-materials'
SCENE_NAME = 'Reference street plaster studio 20260909'
BLEND_PATH = OUT / 'reference-plaster-studio-v1.blend'
assert not BLEND_PATH.exists(), 'Preserve the existing source; author a new revision.'
assert SCENE_NAME not in bpy.data.scenes, 'The reference plaster studio already exists.'
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.data.scenes.new(SCENE_NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 8
scene.cycles.use_denoising = False
scene.render.bake.margin = 24
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'CUDA'
    scene.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
except Exception:
    scene.cycles.device = 'CPU'


def make_surface(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    def node(kind, label):
        value = nt.nodes.new(kind)
        value.name = label
        value.label = label
        value.location = ((len(nt.nodes) % 8) * 240, -(len(nt.nodes) // 8) * 170)
        return value

    def link(value, socket):
        if hasattr(value, 'node'):
            nt.links.new(value, socket)
        else:
            if isinstance(value, (int, float)) and hasattr(socket.default_value, '__len__'):
                value = [value] * len(socket.default_value)
            socket.default_value = value

    def calc(operation, a, b=0, name=None):
        n = node('ShaderNodeMath', name or operation)
        n.operation = operation
        link(a, n.inputs[0])
        link(b, n.inputs[1])
        return n.outputs[0]

    def ramp(value, low, high, name):
        n = node('ShaderNodeMapRange', name)
        n.clamp = True
        n.interpolation_type = 'SMOOTHERSTEP'
        link(value, n.inputs['Value'])
        n.inputs['From Min'].default_value = low
        n.inputs['From Max'].default_value = high
        return n.outputs['Result']

    def mix(a, b, factor, name):
        n = node('ShaderNodeMixRGB', name)
        n.blend_type = 'MIX'
        link(factor, n.inputs[0])
        link(a, n.inputs[1])
        link(b, n.inputs[2])
        return n.outputs[0]

    uv = node('ShaderNodeTexCoord', 'Existing four metre UV0')
    axes = node('ShaderNodeSeparateXYZ', 'UV axes')
    link(uv.outputs['UV'], axes.inputs[0])

    def photo(asset, suffix, name, srgb=True):
        n = node('ShaderNodeTexImage', name)
        path = SOURCE / asset / (asset + '_' + suffix + '_4k.png')
        n.image = bpy.data.images.load(str(path), check_existing=True)
        n.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        n.extension = 'REPEAT'
        link(uv.outputs['UV'], n.inputs['Vector'])
        return n.outputs['Color']

    # Closed periodic coordinates prevent new procedural layers creating tile seams.
    turns = [calc('MULTIPLY', axes.outputs[i], math.tau) for i in range(2)]
    circle = [calc('COSINE', turns[0]), calc('SINE', turns[0]),
              calc('COSINE', turns[1]), calc('SINE', turns[1])]
    periodic = node('ShaderNodeCombineXYZ', 'Closed periodic material coordinates')
    for i in range(3):
        link(circle[i], periodic.inputs[i])

    def noise(scale, label, detail=3):
        n = node('ShaderNodeTexNoise', label)
        n.noise_dimensions = '4D'
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = .67
        link(periodic.outputs[0], n.inputs['Vector'])
        link(circle[3], n.inputs['W'])
        return n.outputs['Fac']

    bs = node('ShaderNodeBsdfPrincipled', 'Reference physical surface')
    output = node('ShaderNodeOutputMaterial', 'Reference material output')
    link(bs.outputs['BSDF'], output.inputs['Surface'])

    def outputs(color, roughness, normal=None, alpha=1):
        link(color, bs.inputs['Base Color'])
        link(roughness, bs.inputs['Roughness'])
        link(0, bs.inputs['Metallic'])
        link(alpha, bs.inputs['Alpha'])
        if normal is not None:
            link(normal, bs.inputs['Normal'])
        for label, value in [('BaseColor', color), ('Roughness', roughness),
                             ('Metallic', 0), ('Alpha', alpha)]:
            e = node('ShaderNodeEmission', 'Bake ' + label)
            link(value, e.inputs['Color'])
        return mat

    if name.endswith('Plaster'):
        source = photo('beige_wall_001', 'diff', 'CC0 photographic lime plaster')
        aggregate = photo('rough_concrete', 'diff', 'CC0 mineral substrate colour')
        normal_image = photo('beige_wall_001', 'nor_gl', 'CC0 plaster source normal', False)
        source_roughness = photo('beige_wall_001', 'rough', 'CC0 plaster roughness', False)
        broad = noise(.95, 'Uneven limewash batches', 2)
        middle = noise(4.1, 'Connected old repair margins')
        grain = noise(65, 'Small mineral grain')
        fine = noise(190, 'Fine plaster pinholes', 2)

        # Colour targets are scene-linear reflectance, not baked lighting.
        weather = ramp(broad, .32, .71, 'Patchy warm mineral exposure')
        colour = mix(source, (.42, .327, .225, 1), .23, 'Warm but neutral lime plaster')
        colour = mix(colour, (.245, .184, .119, 1),
                     calc('MULTIPLY', weather, .36), 'Uneven mineral patina')
        repair_mask = ramp(calc('ADD', middle, calc('MULTIPLY', broad, .30)),
                           .66, .745, 'Soft surviving limewash boundaries')
        undercoat = mix(aggregate, (.28, .224, .151, 1), .48, 'Warm exposed mineral binder')
        colour = mix(colour, undercoat, calc('MULTIPLY', repair_mask, .62),
                     'Old repair patches retained within plaster')
        pale = ramp(noise(1.8, 'Partial limewash brush repairs', 2), .60, .73,
                    'Sparse lighter repairs')
        colour = mix(colour, (.56, .453, .323, 1), calc('MULTIPLY', pale, .20),
                     'Thin surviving limewash')

        # A warped, connected cell-edge network, gated to limited worn areas.
        # At a four metre tile, the main mask gives roughly 1–3 mm fine lines.
        warp = node('ShaderNodeTexNoise', 'Subtle fracture direction distortion')
        warp.noise_dimensions = '4D'
        warp.inputs['Scale'].default_value = 3.2
        warp.inputs['Detail'].default_value = 3
        link(periodic.outputs[0], warp.inputs['Vector'])
        link(circle[3], warp.inputs['W'])
        warp_size = node('ShaderNodeVectorMath', 'Small physical fracture irregularity')
        warp_size.operation = 'SCALE'
        link(warp.outputs['Color'], warp_size.inputs[0])
        warp_size.inputs['Scale'].default_value = .11
        distorted = node('ShaderNodeVectorMath', 'Warped connected fracture coordinates')
        distorted.operation = 'ADD'
        link(periodic.outputs[0], distorted.inputs[0])
        link(warp_size.outputs[0], distorted.inputs[1])
        edges = node('ShaderNodeTexVoronoi', 'Connected mineral hairline network')
        edges.voronoi_dimensions = '3D'
        edges.feature = 'DISTANCE_TO_EDGE'
        edges.inputs['Scale'].default_value = 2.5
        edges.inputs['Randomness'].default_value = 1
        link(distorted.outputs[0], edges.inputs['Vector'])
        line = calc('SUBTRACT', 1, ramp(edges.outputs['Distance'], .003, .010,
                    'Fine millimetre line width'))
        local = ramp(noise(1.25, 'Localized failing plaster zones', 3), .51, .66,
                     'Fine cracking limited to weathered zones')
        crack = calc('MULTIPLY', line, local, 'Localized connected fissures')
        colour = mix(colour, (.105, .075, .044, 1), calc('MULTIPLY', crack, .60),
                     'Brown mineral fissure colour, no black painted lines')
        pore = ramp(fine, .68, .80, 'Sparse small pores')
        colour = mix(colour, (.18, .13, .075, 1), calc('MULTIPLY', pore, .16),
                     'Fine exposed pores')

        source_normal = node('ShaderNodeNormalMap', 'Photographic fine plaster relief')
        source_normal.inputs['Strength'].default_value = .58
        link(normal_image, source_normal.inputs['Color'])
        height = calc('ADD', calc('MULTIPLY', grain, .20), calc('MULTIPLY', fine, .08))
        height = calc('SUBTRACT', height, calc('MULTIPLY', repair_mask, .24))
        height = calc('SUBTRACT', height, calc('MULTIPLY', crack, .44))
        bump = node('ShaderNodeBump', 'Fine relief below two millimetres')
        bump.inputs['Distance'].default_value = .004
        bump.inputs['Strength'].default_value = 1
        link(height, bump.inputs['Height'])
        link(source_normal.outputs[0], bump.inputs['Normal'])
        roughness = calc('MINIMUM', 1, calc('ADD',
                        calc('MULTIPLY', source_roughness, .70), .25))
        roughness = calc('ADD', roughness, calc('MULTIPLY', repair_mask, .035))
        mat['tileMetres'] = 4.0
        mat['normalConvention'] = 'OpenGL +Y tangent'
        mat['description'] = 'Limewash, uneven mineral binder, fine localized connected fissures.'
        return outputs(colour, roughness, bump.outputs['Normal'])

    # Transparent runoff uses its own local UV. The top follows a cornice or sill;
    # a narrow wandering mineral fan fades below it and at every texture border.
    x, y = axes.outputs['X'], axes.outputs['Y']
    warp = node('ShaderNodeTexNoise', 'Runoff local capillary variation')
    warp.inputs['Scale'].default_value = 5.8
    warp.inputs['Detail'].default_value = 4
    link(uv.outputs['UV'], warp.inputs['Vector'])
    scale = node('ShaderNodeVectorMath', 'Long mineral streaks')
    scale.operation = 'MULTIPLY'
    link(uv.outputs['UV'], scale.inputs[0])
    scale.inputs[1].default_value = (45, 2.1, 1)
    streak_noise = node('ShaderNodeTexNoise', 'Irregular vertical sediment fingers')
    streak_noise.inputs['Scale'].default_value = 1
    streak_noise.inputs['Detail'].default_value = 3
    link(scale.outputs[0], streak_noise.inputs['Vector'])
    center = calc('ADD', x, calc('MULTIPLY',
                       calc('SUBTRACT', warp.outputs['Fac'], .5), .12))
    distance = calc('ABSOLUTE', calc('SUBTRACT', center, .5))
    width = calc('ADD', .15, calc('MULTIPLY', y, .20))
    width_ratio = calc('DIVIDE', distance, width)
    fan = calc('SUBTRACT', 1, ramp(width_ratio, .35, 1, 'Feathered sediment fan edges'))
    tail = ramp(y, .03, .64, 'Runoff dissolves toward the foot')
    top_fade = calc('SUBTRACT', 1, ramp(y, .98, 1, 'No rectangular top edge'))
    fingers = ramp(streak_noise.outputs['Fac'], .27, .74, 'Variable streak density')
    fingers = calc('ADD', .17, calc('MULTIPLY', fingers, .83))
    mask = calc('MULTIPLY', fan, calc('MULTIPLY', tail, fingers))
    mask = calc('MULTIPLY', mask, top_fade)
    alpha = calc('MULTIPLY', mask, .31, 'Restrained runoff opacity')
    colour = mix((.10, .060, .025, 1), (.23, .145, .064, 1),
                 warp.outputs['Fac'], 'Mineral deposit reflectance')
    mat['tileMetres'] = 0
    mat['description'] = 'Original transparent mineral runoff, kept at selected sill/coping joints.'
    mat.surface_render_method = 'DITHERED'
    return outputs(colour, .97, alpha=alpha)


materials = {family: make_surface('Reference street ' + family)
             for family in ('Plaster', 'MineralRunoff')}
mesh = bpy.data.meshes.new('Four metre reference plaster bake tile')
mesh.from_pydata([(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [], [(0, 1, 2, 3)])
mesh.update()
uv = mesh.uv_layers.new(name='UV0')
for loop, coord in zip(mesh.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    uv.data[loop.index].uv = coord
plane = bpy.data.objects.new('Reference plaster four metre bake tile', mesh)
scene.collection.objects.link(plane)
mesh.materials.append(materials['Plaster'])


def B(value):
    return Vector((value[0], -value[2], value[1]))


placements = [
    # These thin mineral deposits start at existing joints, outside door/window openings.
    ('Field gable coping joint', 'field_supply', (17.7485, 5.09, -10.75), .38, .34, (-1, 0, 0), (0, 0, -1)),
    ('Field upper lintel joint', 'field_supply', (17.8685, 4.36, -6.70), .28, .49, (-1, 0, 0), (0, 0, -1)),
    ('Field poster pier coping', 'field_supply', (17.8685, 3.075, -11.95), .35, .43, (-1, 0, 0), (0, 0, -1)),
    ('Finery front coping joint left', 'finery', (16.7135, 7.48, -18.10), .36, .51, (-1, 0, 0), (0, 0, -1)),
    ('Finery front coping joint right', 'finery', (16.7135, 7.48, -16.40), .31, .51, (-1, 0, 0), (0, 0, -1)),
    ('Finery upper jamb joint left', 'finery', (16.7985, 6.28, -19.27), .33, .61, (-1, 0, 0), (0, 0, -1)),
    ('Finery upper jamb joint right', 'finery', (16.7985, 6.23, -16.60), .29, .68, (-1, 0, 0), (0, 0, -1)),
    ('Finery north coping joint', 'finery', (22.75, 6.45, -14.1985), .53, .65, (0, 0, 1), (1, 0, 0)),
]
details = []
for name, family, center, width, height, normal, right in placements:
    c, u, up = Vector(center), Vector(right), Vector((0, 1, 0))
    positions = [list(c + u * a * width + up * b * height)
                 for a, b in ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))]
    winding = (0, 1, 2, 3) if u.cross(up).dot(Vector(normal)) > 0 else (3, 2, 1, 0)
    indices = [0, 1, 2, 0, 2, 3] if winding[0] == 0 else [0, 2, 1, 0, 3, 2]
    local_mesh = bpy.data.meshes.new(name + ' editable surface film')
    local_mesh.from_pydata([B(v) for v in positions], [], [winding])
    local_mesh.update()
    local_uv = local_mesh.uv_layers.new(name='UV0 local deposit')
    coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop in local_mesh.loops:
        local_uv.data[loop.index].uv = coords[loop.vertex_index]
    local_mesh.materials.append(materials['MineralRunoff'])
    obj = bpy.data.objects.new(name, local_mesh)
    scene.collection.objects.link(obj)
    obj['family'] = family
    obj['placementPurpose'] = 'Transparent mineral stain follows an existing construction joint.'
    obj.hide_render = True  # Do not include world-space placement meshes in tile bakes.
    details.append(dict(name=name, family=family, material='MineralRunoff',
                        positions=positions, normals=[list(normal)] * 4,
                        uv=coords, indices=indices,
                        castShadows=False, receiveShadows=True, collider=False))

source_meshes = json.loads((ROOT / 'art/facade_materials_20260909/facade-meshes-v2.json').read_text())
target_paths = [row['sourcePath'] for row in source_meshes if row['material'] == 'Plaster']
record = dict(
    created='2026-09-09', blender=bpy.app.version_string,
    reference='/home/teknetik/Downloads/Codex Image Sep 9, 2026, 07_38_57 PM.png',
    sourceBlend=str(BLEND_PATH.relative_to(ROOT)),
    supersedes='Plaster material assignment only, on the listed 35 existing source renderers.',
    targetSourcePaths=target_paths, tileMetres=4, resolution=4096,
    authoring='Original Blender nodes; no downloaded new resource, generated image, or copied pixels from the user reference.',
    sourceAssets=[
        dict(asset='beige_wall_001', license='CC0', authors=['Dimitrios Savva', 'Rico Cilliers'],
             metadata='refs/quality_20260909/building-materials/beige_wall_001'),
        dict(asset='rough_concrete', license='CC0', authors=['Dimitrios Savva'],
             metadata='refs/quality_20260909/building-materials/rough_concrete')],
    materials=dict(
        Plaster=dict(shader='Universal Render Pipeline/Lit', colorSpace='sRGB',
                     normal='OpenGL tangent +Y; linear import; do not flip green',
                     roughness='Linear; pack 1-Roughness into smoothness alpha',
                     metallic='0; never treat lime plaster as metal',
                     textureDirectory='textures/ReferencePlaster', uv='Existing UV0 at four metres; unchanged meshes.'),
        MineralRunoff=dict(shader='Universal Render Pipeline/Lit', surface='Transparent alpha blend',
                           alphaClip=False, alpha='RGBA baked BaseColor alpha',
                           baseColor=[1, 1, 1, 1], metallic=0, smoothness=.03,
                           textureDirectory='textures/MineralRunoff', castShadows=False,
                           zwrite=False, renderQueue=3000)),
    notes=['All original sources are untouched.',
           'Current placement meshes are optional transparent material films, never opaque ribbons.',
           'No gameplay roots, meshes, transforms, routes, colliders or building envelopes are replaced.',
           'No scene lighting baked into colour or scalar maps.',
           'Native sun/shade, close-up and temporal review required before visual acceptance.'])
(OUT / 'plaster-manifest.json').write_text(json.dumps(record, indent=2))
(OUT / 'plaster-details.json').write_text(json.dumps(details, separators=(',', ':')))


def bake_reference_plaster(family='Plaster'):
    """Bake one family through the live Blender session; preserve existing outputs."""
    import hashlib
    import json
    import time
    from pathlib import Path
    import bpy
    import numpy as np
    ROOT = Path('/home/teknetik/code/ao2')
    OUT = ROOT / 'art/reference_street_20260909'
    SCENE_NAME = 'Reference street plaster studio 20260909'
    BLEND_PATH = OUT / 'reference-plaster-studio-v1.blend'
    assert family in ('Plaster', 'MineralRunoff')
    target_scene = bpy.data.scenes[SCENE_NAME]
    bpy.context.window.scene = target_scene
    target_plane = target_scene.objects['Reference plaster four metre bake tile']
    for obj in target_scene.objects:
        obj.select_set(False)
    target_plane.select_set(True)
    bpy.context.view_layer.objects.active = target_plane
    target_mat = bpy.data.materials['Reference street ' + family]
    target_plane.data.materials[0] = target_mat
    nt = target_mat.node_tree
    output = nt.nodes['Reference material output']
    bs = nt.nodes['Reference physical surface']
    folder = OUT / 'textures' / ('ReferencePlaster' if family == 'Plaster' else family)
    folder.mkdir(parents=True, exist_ok=True)
    channels = ['BaseColor', 'Normal', 'Roughness', 'Metallic'] if family == 'Plaster' else ['BaseColor', 'Alpha']
    for channel in channels:
        assert not (folder / (channel + '.png')).exists(), 'Preserve previous bake: ' + channel
    baked, timings = {}, []
    try:
        for channel in channels:
            img = bpy.data.images.new('Reference ' + family + ' ' + channel,
                                      4096, 4096, alpha=True, float_buffer=False)
            img.colorspace_settings.name = 'sRGB' if channel == 'BaseColor' else 'Non-Color'
            target = nt.nodes.new('ShaderNodeTexImage')
            target.name = 'Temporary reference bake target'
            target.image = img
            nt.nodes.active = target
            for n in nt.nodes:
                n.select = n == target
            value = bs.outputs['BSDF'] if channel == 'Normal' else nt.nodes['Bake ' + channel].outputs[0]
            nt.links.new(value, output.inputs['Surface'])
            start = time.monotonic()
            bpy.ops.object.bake(type='NORMAL' if channel == 'Normal' else 'EMIT',
                                normal_space='TANGENT', normal_r='POS_X', normal_g='POS_Y',
                                normal_b='POS_Z', use_clear=True, margin=24)
            nt.nodes.remove(target)
            baked[channel] = img
            timings.append(dict(channel=channel, seconds=time.monotonic() - start))
        if family == 'MineralRunoff':
            rgba = np.empty(4096 * 4096 * 4, dtype=np.float32)
            alpha = np.empty_like(rgba)
            baked['BaseColor'].pixels.foreach_get(rgba)
            baked['Alpha'].pixels.foreach_get(alpha)
            rgba[3::4] = alpha[0::4]
            baked['BaseColor'].pixels.foreach_set(rgba)
            baked['BaseColor'].alpha_mode = 'STRAIGHT'
            baked['BaseColor'].update()
        maps = []
        for channel, img in baked.items():
            path = folder / (channel + '.png')
            img.filepath_raw = str(path)
            img.file_format = 'PNG'
            img.save()
            maps.append(dict(channel=channel, file=str(path.relative_to(ROOT)), width=4096,
                             height=4096, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                             colorSpace='sRGB' if channel == 'BaseColor' else 'linear'))
        result = dict(family=family, blender=bpy.app.version_string,
                      device=target_scene.cycles.device, maps=maps, timings=timings)
        (folder / 'bake.json').write_text(json.dumps(result, indent=2))
    finally:
        nt.links.new(bs.outputs['BSDF'], output.inputs['Surface'])
        for img in baked.values():
            bpy.data.images.remove(img)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
    print(json.dumps(result))
    return result


bpy.context.view_layer.objects.active = plane
plane.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH))
print(json.dumps(dict(scene=SCENE_NAME, materials=[m.name for m in materials.values()],
                      targetRenderers=len(target_paths), optionalRunoffFilms=len(details),
                      sourceBlend=str(BLEND_PATH), next='bake_reference_plaster("Plaster"); then bake_reference_plaster("MineralRunoff")')))
