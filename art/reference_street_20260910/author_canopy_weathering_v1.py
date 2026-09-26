"""Live Blender material authoring only; execute after exclusive handover.

Preserves all installed geometry/UVs and prior source files. AUTHOR creates a
small, independent material studio. BAKE writes one explicit family/channel;
REVIEW is deliberately separate so a bake is never treated as art acceptance.
"""
import bpy
import hashlib
import json
import math
import time
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260910/canopy-weathering-v1'
SOURCE = ROOT / 'refs/reference-street/20260910/cloth-candidates/book_pattern'
STUDIO = 'Finery canvas weathering material studio v1'
ACTION = globals().get('CANVAS_ACTION', 'AUTHOR')
FAMILY = globals().get('CANVAS_FAMILY', 'Membrane')
CHANNEL = globals().get('CANVAS_CHANNEL', 'BaseColor')
FAMILIES = {
    'Membrane': {'metres': [4.58, 6.5], 'resolution': [4096, 4096]},
    'Valance': {'metres': [.30, 6.5], 'resolution': [512, 8192]},
    'Seam': {'metres': [2., 2.], 'resolution': [2048, 2048]},
    'Repair': {'metres': [4.8, 6.8], 'resolution': [4096, 4096]},
    'DetailFabric': {'metres': [.3, .3], 'resolution': [4096, 4096]},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    manifest = json.loads((SOURCE / 'download-manifest.json').read_text())
    for row in manifest['maps']:
        assert digest(SOURCE / row['file']) == row['sha256'], row['file']
    return manifest


def author():
    assert not (OUT / 'canvas-weathering-source-v1.blend').exists()
    assert STUDIO not in bpy.data.scenes
    originals = inputs()
    scene = bpy.data.scenes.new(STUDIO)
    bpy.context.window.scene = scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = dev.type == 'CUDA'
        scene.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
    except Exception:
        scene.cycles.device = 'CPU'
    me = bpy.data.meshes.new(STUDIO + ' plane')
    me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
    me.update()
    uv = me.uv_layers.new(name='Map chart')
    for loop, point in zip(me.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = point
    plane = bpy.data.objects.new(STUDIO + ' plane', me)
    scene.collection.objects.link(plane)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)

    for family, spec in FAMILIES.items():
        mat = bpy.data.materials.new('Finery canvas weathering v1 ' + family)
        mat.use_nodes = True
        mat.use_fake_user = True
        nt = mat.node_tree
        ns, links = nt.nodes, nt.links
        ns.clear()

        def node(kind, name):
            q = ns.new(kind)
            q.name = q.label = name
            return q

        def wire(value, socket):
            if hasattr(value, 'node'):
                links.new(value, socket)
            elif isinstance(value, (int, float)) and hasattr(socket.default_value, '__len__'):
                socket.default_value = [value] * len(socket.default_value)
            else:
                socket.default_value = value

        def calc(op, a, b=0, name=None):
            q = node('ShaderNodeMath', name or op)
            q.operation = op
            wire(a, q.inputs[0]); wire(b, q.inputs[1])
            return q.outputs[0]

        def ramp(value, lo, hi, name):
            q = node('ShaderNodeMapRange', name)
            q.interpolation_type = 'SMOOTHSTEP'; q.clamp = True
            q.inputs['From Min'].default_value = lo
            q.inputs['From Max'].default_value = hi
            wire(value, q.inputs['Value'])
            return q.outputs['Result']

        def mix(a, b, factor, name):
            q = node('ShaderNodeMixRGB', name)
            wire(factor, q.inputs[0]); wire(a, q.inputs[1]); wire(b, q.inputs[2])
            return q.outputs[0]

        uv = node('ShaderNodeTexCoord', 'Chart coordinates')
        vec = node('ShaderNodeVectorMath', 'Metres on fabric')
        vec.operation = 'MULTIPLY'
        links.new(uv.outputs['UV'], vec.inputs[0])
        vec.inputs[1].default_value = (*spec['metres'], 1)
        axes = node('ShaderNodeSeparateXYZ', 'Fabric metre axes')
        links.new(vec.outputs[0], axes.inputs[0])
        x, y = axes.outputs['X'], axes.outputs['Y']

        def noise(sx, sy, name, detail=3):
            scale = node('ShaderNodeVectorMath', name + ' metric frequency')
            scale.operation = 'MULTIPLY'; scale.inputs[1].default_value = (sx, sy, 1)
            links.new(vec.outputs[0], scale.inputs[0])
            n = node('ShaderNodeTexNoise', name)
            links.new(scale.outputs[0], n.inputs['Vector'])
            n.inputs['Scale'].default_value = 1
            n.inputs['Detail'].default_value = detail
            n.inputs['Roughness'].default_value = .69
            return n.outputs['Fac']

        macro = noise(1.6, 1.35, 'Uneven cloth exposure', 2)
        grain = noise(38, 47, 'Worn fibre bundles', 2)
        streaks = noise(2.4, 31, 'Down-slope fabric runoff', 2)
        fade = calc('MULTIPLY', ramp(macro, .32, .68, 'Broad sun bleaching'), .33)
        deposit = 0
        abrasion = 0
        if family == 'Membrane':
            u = calc('DIVIDE', x, 4.58)
            panel = 0
            for k, boundary in enumerate([.218, .492, .757]):
                trace = calc('ADD', boundary * 6.5, calc('MULTIPLY', calc('SINE', calc('MULTIPLY', u, math.pi)), .0325 * (-1 if k == 1 else 1)))
                dist = calc('ABSOLUTE', calc('SUBTRACT', y, trace))
                edge = calc('SUBTRACT', 1, ramp(dist, .014, .075, 'Raised seam fibre abrasion ' + str(k)))
                abrasion = calc('MAXIMUM', abrasion, edge)
                panel = calc('ADD', panel, calc('MULTIPLY', ramp(y, boundary * 6.5 - .015, boundary * 6.5 + .015, 'Independent sewn panel ' + str(k)), [.028, -.044, .023][k]))
            fade = calc('ADD', fade, panel)
            front = calc('SUBTRACT', 1, ramp(calc('SUBTRACT', 4.58, x), .025, .22, 'Wind exposed front cloth'))
            abrasion = calc('MAXIMUM', abrasion, calc('MULTIPLY', front, .62))
            rear = calc('SUBTRACT', 1, ramp(x, .025, .75, 'Short runoff below attachment'))
            deposit = calc('MULTIPLY', rear, ramp(streaks, .51, .68, 'Localized attachment drips'))
        elif family == 'Valance':
            # Existing UV0 X is distance down the hem, Y is original width.
            v = calc('DIVIDE', y, 6.5)
            depth = calc('ADD', .207, calc('MULTIPLY', calc('SINE', calc('ADD', calc('MULTIPLY', v, 7.3), .4)), .036))
            depth = calc('ADD', depth, calc('MULTIPLY', calc('SINE', calc('ADD', calc('MULTIPLY', v, 17.1), 2.0)), .029))
            gaussian = calc('POWER', math.e, calc('MULTIPLY', -1, calc('POWER', calc('DIVIDE', calc('SUBTRACT', v, .66), .12), 2)))
            depth = calc('ADD', depth, calc('MULTIPLY', gaussian, .032))
            # This is author_finery_canopy_v3.hem_depth, in exact metres.
            dist = calc('ABSOLUTE', calc('SUBTRACT', x, depth))
            abrasion = calc('SUBTRACT', 1, ramp(dist, .008, .070, 'Bleached free hem'))
            deposit = calc('MULTIPLY', calc('SUBTRACT', 1, ramp(x, .012, .11, 'Dirt at rolled pocket')), ramp(streaks, .48, .67, 'Intermittent upper hem dirt'))
        elif family == 'Seam':
            fade = calc('ADD', .19, calc('MULTIPLY', fade, .5))
            abrasion = calc('MULTIPLY', ramp(grain, .36, .64, 'Frayed seam yarns'), .24)
        elif family == 'Repair':
            fade = calc('ADD', .25, calc('MULTIPLY', fade, .35))
            for k, (uc, vc, width, height, angle) in enumerate([(.68, .362, .34, .44, -.17), (.34, .814, .27, .33, .13)]):
                # The source patch UVs retain the deliberate .173/.127 m
                # offset. Invert the exact authored patch rotation.
                dx = calc('SUBTRACT', x, uc * 4.58 + .173)
                dy = calc('SUBTRACT', y, vc * 6.5 + .127)
                a = calc('ADD', calc('MULTIPLY', dx, math.cos(angle)), calc('MULTIPLY', dy, math.sin(angle)))
                b = calc('ADD', calc('MULTIPLY', dx, -math.sin(angle)), calc('MULTIPLY', dy, math.cos(angle)))
                edge_distance = calc('MINIMUM', calc('SUBTRACT', width / 2, calc('ABSOLUTE', a)), calc('SUBTRACT', height / 2, calc('ABSOLUTE', b)))
                inside = ramp(edge_distance, -.002, .001, 'Repair region ' + str(k))
                edge = calc('MULTIPLY', inside, calc('SUBTRACT', 1, ramp(edge_distance, .003, .025, 'Worn sewn repair boundary ' + str(k))))
                abrasion = calc('MAXIMUM', abrasion, edge)

        abrasion = calc('MULTIPLY', abrasion, calc('ADD', .27, calc('MULTIPLY', ramp(grain, .34, .63, 'Broken bleaching'), .73)))
        fade = calc('MINIMUM', .74, calc('ADD', fade, calc('MULTIPLY', abrasion, .49)))
        color = mix((.195, .036, .018, 1), (.345, .160, .087, 1), fade, 'Original red dye and exposed faded fibres')
        if family == 'Repair':
            color = mix(color, (.155, .080, .047, 1), .46, 'Different reclaimed repair dye lot')
        color = mix(color, (.095, .063, .035, 1), calc('MULTIPLY', deposit, .46), 'Localized dusty runoff')
        rough = calc('ADD', .78, calc('MULTIPLY', fade, .18))
        rough = calc('MAXIMUM', rough, calc('ADD', .76, calc('MULTIPLY', deposit, .19)))
        rough = calc('ADD', rough, calc('MULTIPLY', calc('SUBTRACT', grain, .5), .055))

        if family == 'DetailFabric':
            tex = node('ShaderNodeTexImage', 'Retained CC0 plain cotton diffuse')
            tex.image = bpy.data.images.load(str(SOURCE / 'book_pattern_col1_4k.png'), check_existing=True)
            tex.image.colorspace_settings.name = 'sRGB'
            links.new(uv.outputs['UV'], tex.inputs[0])
            gray = node('ShaderNodeRGBToBW', 'Cloth fibre luminance')
            links.new(tex.outputs['Color'], gray.inputs[0])
            # The diffuse chroma is excluded. A compressed luminance signal
            # around linear 0.5 retains fine fibres without tiling olive dye.
            ratio = calc('DIVIDE', calc('MAXIMUM', gray.outputs[0], .001), .0561532639)
            log = calc('LOGARITHM', ratio, 2)
            detail = calc('ADD', .5, calc('MULTIPLY', log, .075))
            color = calc('MINIMUM', .74, calc('MAXIMUM', .26, detail))
            rough = .85
        bs = node('ShaderNodeBsdfPrincipled', 'Physical canvas')
        wire(color, bs.inputs['Base Color']); wire(rough, bs.inputs['Roughness'])
        bs.inputs['Metallic'].default_value = 0
        output = node('ShaderNodeOutputMaterial', 'Material output')
        links.new(bs.outputs[0], output.inputs['Surface'])
        for channel, value in [('BaseColor', color), ('Roughness', rough), ('WearMask', fade)]:
            emit = node('ShaderNodeEmission', 'Bake ' + channel)
            wire(value, emit.inputs['Color'])
        mat['physical_map_metres'] = spec['metres']
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        'revision': 1, 'familyContracts': FAMILIES, 'originalInputs': originals,
        'normalSource': 'book_pattern_nor_gl_4k.png, original bytes, 0.3 m tile',
        'normalStrengthAudition': .48,
        'detailAlbedoStrengthAudition': .6,
        'uvContract': 'Installed UV0 in metres/.4 remains unchanged. Base ST=.4/mapMetres; detail ST=mapMetres/.3 gives the original .3 m cotton detail after base transform.',
        'materialAssignment': 'Membrane only on original main sheet; Valance only on CanopyRed additions; Seam on existing piping/seam/pocket; Repair on existing repair additions. No geometry or collider changes.',
        'reviewRequired': 'Full cloth, undercloth, hem and patches under opposed light in Blender, then matched native noon/shade and motion.',
        'scope': 'Authoring and material audition only; source maps/UVs, rigid supports, all game roots and current materials retained.',
    }
    (OUT / 'material-authoring-contract.json').write_text(json.dumps(manifest, indent=2))
    saved = {scene} | {bpy.data.materials['Finery canvas weathering v1 ' + name] for name in FAMILIES}
    bpy.data.libraries.write(str(OUT / 'canvas-weathering-source-v1.blend'), saved, fake_user=True)
    print(json.dumps({'authored': STUDIO, 'families': list(FAMILIES), 'nativeAccepted': False}))


def bake():
    assert FAMILY in FAMILIES
    assert CHANNEL in (['BaseColor'] if FAMILY == 'DetailFabric' else ['BaseColor', 'Roughness', 'WearMask'])
    inputs()
    path = OUT / FAMILY / (CHANNEL + '.png')
    assert not path.exists(), 'Preserve completed bakes'
    path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.data.scenes[STUDIO]; bpy.context.window.scene = scene
    plane = scene.objects[STUDIO + ' plane']
    for obj in scene.objects: obj.select_set(False)
    plane.select_set(True); bpy.context.view_layer.objects.active = plane
    mat = bpy.data.materials['Finery canvas weathering v1 ' + FAMILY]
    plane.data.materials.clear(); plane.data.materials.append(mat)
    spec = FAMILIES[FAMILY]
    plane.scale = (*spec['metres'], 1)
    nt = mat.node_tree
    img = bpy.data.images.new(FAMILY + ' ' + CHANNEL, *spec['resolution'], alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if CHANNEL == 'BaseColor' else 'Non-Color'
    target = nt.nodes.new('ShaderNodeTexImage'); target.image = img
    for n in nt.nodes: n.select = n == target
    nt.nodes.active = target
    nt.links.new(nt.nodes['Bake ' + CHANNEL].outputs[0], nt.nodes['Material output'].inputs['Surface'])
    started = time.monotonic()
    try:
        bpy.ops.object.bake(type='EMIT', use_clear=True, margin=16)
        img.filepath_raw = str(path); img.file_format = 'PNG'; img.save()
    finally:
        nt.links.new(nt.nodes['Physical canvas'].outputs[0], nt.nodes['Material output'].inputs['Surface'])
        nt.nodes.remove(target); bpy.data.images.remove(img)
    record = {'family': FAMILY, 'channel': CHANNEL, 'physicalMetres': spec['metres'], 'resolution': spec['resolution'], 'sha256': digest(path), 'seconds': time.monotonic() - started, 'blender': bpy.app.version_string, 'device': scene.cycles.device, 'lightingBaked': False}
    path.with_suffix('.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if ACTION == 'AUTHOR': author()
elif ACTION == 'BAKE': bake()
else: raise ValueError('Use AUTHOR or BAKE explicitly')
