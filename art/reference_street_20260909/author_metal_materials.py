"""Execute through live Blender MCP; no headless Blender or Unity mutations.

ACTION='AUTHOR' (default) creates a separate editable bake studio, source .blend
and import contract. ACTION='BAKE', BAKE_FAMILY='ShutterSteel' or 'AgedSteel'
bakes four full 4096 maps, then saves the studio. Prior outputs are never replaced.
The shutter material is deliberately registered to existing world-scale UV0;
it is not a generic V-periodic tile. See metal-import-contract.json.
"""
import bpy
import hashlib
import json
import math
import time
from pathlib import Path

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/reference_street_20260909'
STUDIO = 'Reference street metal studio v1'
PLANE = 'Reference four metre metal bake tile'
SOURCE = ROOT / 'refs/quality_20260909/building-materials/rusty_metal_sheet'
ACTION = globals().get('ACTION', 'AUTHOR')
BAKE_FAMILY = globals().get('BAKE_FAMILY', 'ShutterSteel')


def author():
    assert STUDIO not in bpy.data.scenes, 'Preserve the existing studio'
    assert not (OUT / 'metal-studio-v1.blend').exists(), 'Preserve prior source'
    OUT.mkdir(parents=True, exist_ok=True)
    scene = bpy.data.scenes.new(STUDIO)
    bpy.context.window.scene = scene
    scene.unit_settings.system = 'METRIC'
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
        for device in prefs.devices:
            device.use = device.type == 'CUDA'
        scene.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
    except Exception:
        scene.cycles.device = 'CPU'
    mesh = bpy.data.meshes.new(PLANE)
    mesh.from_pydata([(-2,-2,0), (2,-2,0), (2,2,0), (-2,2,0)], [], [(0,1,2,3)])
    mesh.update()
    uv = mesh.uv_layers.new(name='UV0 four metre world scale')
    for loop, coord in zip(mesh.loops, [(0,0), (1,0), (1,1), (0,1)]):
        uv.data[loop.index].uv = coord
    plane = bpy.data.objects.new(PLANE, mesh)
    scene.collection.objects.link(plane)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)

    def material(family):
        mat = bpy.data.materials.new('Reference street ' + family)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        nodes, links = nt.nodes, nt.links

        def node(kind, name):
            obj = nodes.new(kind)
            obj.name = obj.label = name
            return obj

        def wire(value, socket):
            if hasattr(value, 'node'):
                links.new(value, socket)
            elif isinstance(value, (float, int)) and hasattr(socket.default_value, '__len__'):
                socket.default_value = [value] * len(socket.default_value)
            else:
                socket.default_value = value

        def calc(op, a, b=0, name=None):
            obj = node('ShaderNodeMath', name or op)
            obj.operation = op
            wire(a, obj.inputs[0]); wire(b, obj.inputs[1])
            return obj.outputs[0]

        def ramp(value, low, high, name):
            obj = node('ShaderNodeMapRange', name)
            obj.clamp = True
            obj.inputs['From Min'].default_value = low
            obj.inputs['From Max'].default_value = high
            wire(value, obj.inputs['Value'])
            return obj.outputs['Result']

        def mix(a, b, factor, name):
            obj = node('ShaderNodeMixRGB', name)
            obj.blend_type = 'MIX'
            wire(factor, obj.inputs[0]); wire(a, obj.inputs[1]); wire(b, obj.inputs[2])
            return obj.outputs[0]

        tex = node('ShaderNodeTexCoord', 'Existing UV0')
        separate = node('ShaderNodeSeparateXYZ', 'Four metre tile axes')
        links.new(tex.outputs['UV'], separate.inputs[0])
        u_angle = calc('MULTIPLY', separate.outputs['X'], math.tau)
        v_angle = calc('MULTIPLY', separate.outputs['Y'], math.tau)
        trig = [calc('COSINE', u_angle), calc('SINE', u_angle),
                calc('COSINE', v_angle), calc('SINE', v_angle)]

        def noise(xscale, yscale, name, detail=3):
            # Torus coordinates avoid the horizontal seam where the shutter's
            # negative world Z coordinates wrap the four metre tile.
            xyz = node('ShaderNodeCombineXYZ', name + ' torus')
            for i, scale in enumerate([xscale, xscale, yscale]):
                wire(calc('MULTIPLY', trig[i], scale), xyz.inputs[i])
            obj = node('ShaderNodeTexNoise', name)
            obj.noise_dimensions = '4D'
            links.new(xyz.outputs[0], obj.inputs['Vector'])
            wire(calc('MULTIPLY', trig[3], yscale), obj.inputs['W'])
            obj.inputs['Scale'].default_value = 1
            obj.inputs['Detail'].default_value = detail
            obj.inputs['Roughness'].default_value = .68
            return obj.outputs['Fac']

        def image_map(suffix, name, colour):
            obj = node('ShaderNodeTexImage', name)
            obj.image = bpy.data.images.load(str(SOURCE / ('rusty_metal_sheet_' + suffix + '_4k.png')), check_existing=True)
            obj.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
            obj.extension = 'REPEAT'
            links.new(tex.outputs['UV'], obj.inputs['Vector'])
            return obj.outputs['Color']

        photo = image_map('diff', 'CC0 oxide colour', True)
        photo_normal = image_map('nor_gl', 'CC0 oxide microrelief', False)
        macro = noise(.75, 1.3, 'Subtle uneven paint fading', 2)
        meso = noise(6, 14, 'Broken edge exposure', 3)
        fine = noise(43, 96, 'Fine oxidation pits', 2)
        scratch = noise(9, 190, 'Short horizontal abrasion', 2)
        tiny = noise(165, 190, 'Fine coating grain', 2)

        edge = 0
        if family == 'ShutterSteel':
            # Source slat lower edges are y=.506+i*.14, upper edges +.128.
            # Front UV0 is (worldZ/4, worldY/4). Compute distances in metres.
            metres_y = calc('MULTIPLY', separate.outputs['Y'], 4)
            phase = calc('PINGPONG', calc('SUBTRACT', metres_y, .506), .07,
                         'Distance from repeated lower slat edge')
            # PingPong(period .07) is 0 at each .14 boundary; a second shifted
            # field follows the upper edge, including its narrow exposed lip.
            phase_top = calc('PINGPONG', calc('SUBTRACT', metres_y, .634), .07,
                             'Distance from repeated upper slat edge')
            distance = calc('MINIMUM', phase, phase_top)
            edge = calc('SUBTRACT', 1, ramp(distance, .0018, .014,
                                           'Rust restricted to 2 to 14 mm at lips'))
            edge = calc('MULTIPLY', edge, ramp(meso, .34, .66,
                                              'Broken intermittent edge rust'))

        pits = calc('MULTIPLY', ramp(fine, .695, .79, 'Sparse small coating loss'), .44)
        scratches = calc('MULTIPLY', ramp(scratch, .70, .79, 'Fine abrasion flecks'),
                         ramp(meso, .48, .66, 'Localized handling abrasion'))
        rust = calc('MAXIMUM', calc('MULTIPLY', edge, .90), pits)
        rust = calc('MAXIMUM', rust, calc('MULTIPLY', scratches, .28))
        paint = mix((.035,.043,.044,1), (.075,.083,.079,1),
                    ramp(macro, .28, .72, 'Paint fade range'), 'Faded charcoal paint')
        paint = mix(paint, (.15,.142,.115,1), calc('MULTIPLY',
                    ramp(fine, .58, .73, 'Fine dusty speckling'), .16), 'Fine dust in coating')
        oxide = mix((.064,.027,.012,1), (.205,.091,.035,1),
                    ramp(fine, .29, .75, 'Oxide colour range'), 'Brown oxide variation')
        oxide = mix(oxide, photo, .22, 'Retained photographic oxide colour')
        color = mix(paint, oxide, rust, 'Coating loss follows slat lips')
        bare = calc('MULTIPLY', scratches, .20)
        color = mix(color, (.13,.135,.128,1), bare, 'Tiny bare metal abrasion')
        roughness = mix((.64,.64,.64,1), (.91,.91,.91,1), rust, 'Paint and oxide roughness')
        roughness = mix(roughness, (.48,.48,.48,1), bare, 'Worn metal roughness')
        metallic = calc('MULTIPLY', bare, .85)
        normal = node('ShaderNodeNormalMap', 'Restrained retained photographic relief')
        normal.inputs['Strength'].default_value = .28
        wire(photo_normal, normal.inputs['Color'])
        height = calc('SUBTRACT', calc('MULTIPLY', tiny, .17), calc('MULTIPLY', rust, .26))
        height = calc('ADD', height, calc('MULTIPLY', fine, .07))
        bump = node('ShaderNodeBump', 'Thin coating relief in metres')
        bump.inputs['Distance'].default_value = .0018
        bump.inputs['Strength'].default_value = 1
        wire(height, bump.inputs['Height']); links.new(normal.outputs[0], bump.inputs['Normal'])
        bs = node('ShaderNodeBsdfPrincipled', 'Reference street physical metal')
        wire(color, bs.inputs['Base Color']); wire(roughness, bs.inputs['Roughness'])
        wire(metallic, bs.inputs['Metallic']); links.new(bump.outputs['Normal'], bs.inputs['Normal'])
        output = node('ShaderNodeOutputMaterial', 'Material output')
        links.new(bs.outputs['BSDF'], output.inputs['Surface'])
        for name, value in [('BaseColor', color), ('Roughness', roughness), ('Metallic', metallic)]:
            emit = node('ShaderNodeEmission', 'Bake ' + name)
            wire(value, emit.inputs['Color'])
        mat['tileMetres'] = 4
        mat['normalConvention'] = 'OpenGL tangent +Y'
        mat['uvConstraint'] = 'World UV0 unchanged; shutter front U=worldZ/4, V=worldY/4'
        return mat

    materials = {family: material(family) for family in ['ShutterSteel', 'AgedSteel']}
    # An unused second material slot still participates in Cycles baking and can
    # target that material's active photographic image. Keep exactly one slot.
    plane.data.materials.append(materials['ShutterSteel'])
    rows = json.loads((ROOT / 'art/building_weathering_20260909/unity-source.json').read_text())
    shutters = [row for row in rows if 'Rolled shutter slat' in row['name']]
    assert len(shutters) == 20
    for i, row in enumerate(sorted(shutters, key=lambda r:r['bounds']['min'][1])):
        assert abs(row['bounds']['min'][1] - (.506 + i * .14)) < .00001
        assert abs(row['bounds']['max'][1] - (.634 + i * .14)) < .00001
    contract = {
        'source':'metal-studio-v1.blend', 'maps':['BaseColor','Normal','Roughness','Metallic'],
        'resolution':4096, 'normalConvention':'OpenGL tangent +Y; no green flip',
        'baseColorSpace':'sRGB', 'dataColorSpace':'linear',
        'urpPacking':'Metallic.R, 1 - Roughness in alpha; material tint white; smoothness multiplier 1',
        'textureSettings':{'maxTextureSize':4096,'mips':True,'streaming':True,'anisotropy':8,'compression':'BC7 high quality'},
        'materialTransform':{'scale':[1,1],'offset':[0,0]},
        'ShutterSteel':{'replaceMaterialOnlyOn':[r['path'] for r in shutters],
                        'uv':'Keep current FacadeMaterialPass four-metre world UV0, no remap or offset',
                        'scope':'Only Field Supply rolled shutter slats; lip stripes are registered to their exact saved heights',
                        'verticalRangeMetres':[.506,3.294], 'horizontalTileSeam':'periodic',
                        'verticalTileSeam':'not promised; safe over stated installed range'},
        'AgedSteel':{'scope':'Optional separately reviewed dark coated doors/rails/louvres; no lip stripes',
                     'uv':'4 metre material tile; preserve physical texel scale'},
        'provenance':{'license':'CC0','asset':'rusty_metal_sheet','author':'Amal Kumar',
                      'sourcePage':'https://polyhaven.com/a/rusty_metal_sheet',
                      'localSource':str(SOURCE),'authoring':'Original layered Blender nodes and unlit emission/tangent normal bakes',
                      'inputs':[{ 'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                for p in sorted(SOURCE.glob('*_4k.png'))]},
        'preservation':'All previous source maps, material studio and Unity materials remain untouched',
        'reviewStatus':'Source authoring only until bakes and native audition are reviewed'}
    (OUT/'metal-import-contract.json').write_text(json.dumps(contract,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'metal-studio-v1.blend'))
    print(json.dumps({'studio':STUDIO,'materials':['ShutterSteel','AgedSteel'],
                      'next':'Set ACTION=BAKE and BAKE_FAMILY, then execute this script again'}))


def bake(family):
    assert family in ['ShutterSteel','AgedSteel']
    scene = bpy.data.scenes[STUDIO]
    bpy.context.window.scene = scene
    plane = scene.objects[PLANE]
    for obj in scene.objects: obj.select_set(False)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    material = bpy.data.materials['Reference street '+family]
    plane.data.materials.clear()
    plane.data.materials.append(material)
    plane.active_material_index = 0
    for face in plane.data.polygons:face.material_index = 0
    assert len(plane.data.materials) == 1
    # The rejected first bake had an unused material slot with a photographic
    # image selected as its target. Disk originals were not saved by Blender,
    # but reload their pixels before any corrected bake and prove disk identity.
    contract = json.loads((OUT/'metal-import-contract.json').read_text())
    verified_inputs = []
    for source in contract['provenance']['inputs']:
        path = SOURCE/source['file']
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        assert observed == source['sha256'], 'Original source disk hash changed: '+str(path)
        verified_inputs.append({'file':str(path),'sha256':observed,'matchesAuthoredInput':True})
        for image in bpy.data.images:
            if image.source == 'FILE' and image.filepath and Path(bpy.path.abspath(image.filepath)).resolve() == path.resolve():
                image.reload()
    nt = material.node_tree
    output = nt.nodes['Material output']
    bs = nt.nodes['Reference street physical metal']
    target_dir = OUT / 'textures' / family
    target_dir.mkdir(parents=True, exist_ok=True)
    record = {'family':family,'blender':bpy.app.version_string,
              'device':scene.cycles.device,'resolution':4096,'maps':[],
              'bakeRevision':2,'materialSlotCount':len(plane.data.materials),
              'sourceReloadedFromVerifiedDisk':verified_inputs}
    for name in ['BaseColor','Normal','Roughness','Metallic']:
        path = target_dir/(name+'.png')
        assert not path.exists(), 'Preserve prior bake: '+str(path)
        img = bpy.data.images.new('Reference '+family+' '+name,4096,4096,alpha=False,float_buffer=False)
        img.colorspace_settings.name = 'sRGB' if name=='BaseColor' else 'Non-Color'
        node = nt.nodes.new('ShaderNodeTexImage')
        node.image = img
        nt.nodes.active = node
        for item in nt.nodes:item.select = item==node
        socket = bs.outputs['BSDF'] if name=='Normal' else nt.nodes['Bake '+name].outputs[0]
        nt.links.new(socket,output.inputs['Surface'])
        start = time.monotonic()
        bpy.ops.object.bake(type='NORMAL' if name=='Normal' else 'EMIT',
                            normal_space='TANGENT',normal_r='POS_X',normal_g='POS_Y',normal_b='POS_Z',
                            use_clear=True,margin=24)
        img.filepath_raw = str(path);img.file_format = 'PNG';img.save()
        record['maps'].append({'file':str(path),'seconds':round(time.monotonic()-start,3),
                               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        nt.nodes.remove(node);bpy.data.images.remove(img)
    nt.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
    (target_dir/'bake.json').write_text(json.dumps(record,indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'metal-studio-v2.blend'))
    print(json.dumps(record))


if ACTION == 'AUTHOR': author()
elif ACTION == 'BAKE': bake(BAKE_FAMILY)
else: raise ValueError('ACTION must be AUTHOR or BAKE')
