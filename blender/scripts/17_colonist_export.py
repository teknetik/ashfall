"""Export the reviewed optimized colonist to a candidate GLB, never the live one."""
import bpy
import json
from pathlib import Path

ROOT = Path('/Users/carl.draper/Documents/code/ao2')


def export_colonist(rig):
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH'
               and o.get('colonistOptimizeV1') == rig.name]
    if not objects:
        raise ValueError('Run 15_colonist_optimize first')
    proxies = [o for o in objects if o.get('shadowProxy')]
    assert len(proxies) == 1
    proxy = proxies[0]
    proxy.name = 'COLONIST_shadow_proxy'

    # Both cloth batches use SurfaceUV. Their unused UVMap/UV0 difference does
    # not justify a separate draw. Blender join retains layers by name.
    graphite = [o for o in objects if o != proxy and len(o.data.materials) == 1
                and o.data.materials[0].name == 'MAT_colonist_armour_graphite']
    if len(graphite) > 1:
        assert all(o.data.uv_layers.get('SurfaceUV') for o in graphite)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in graphite:
            obj.hide_set(False)
            obj.select_set(True)
        bpy.context.view_layer.objects.active = graphite[0]
        bpy.ops.object.join()
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH'
               and o.get('colonistOptimizeV1') == rig.name]

    for mat in {m for o in objects for m in o.data.materials}:
        if 'eyebrow001' not in mat.name:
            continue
        mat.name = 'MAT_colonist_eyebrows'
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
        tex = nodes['DiffuseTexture']
        mix = nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1
        mix.inputs[7].default_value = (.18, .14, .10, 1)
        links.new(tex.outputs['Color'], mix.inputs[6])
        links.new(mix.outputs[2], shader.inputs['Base Color'])
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'GREATER_THAN'
        cutoff.inputs[1].default_value = .35
        links.new(tex.outputs['Alpha'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], shader.inputs['Alpha'])
        shader.inputs['Roughness'].default_value = .7
        mat.use_backface_culling = False

    # Runtime copies: the scan normals include 16-bit PNGs (one alone is16 MB).
    # Browser normal maps need 8-bit RGB; retain the source files and bake the
    # delivery encoding through Blender's colour-managed image writer.
    image_scene = bpy.data.scenes.new('Colonist_Delivery_Images')
    image_scene.view_settings.look = 'None'
    image_scene.view_settings.exposure = 0
    image_scene.view_settings.gamma = 1
    settings = image_scene.render.image_settings
    settings.color_depth = '8'
    settings.compression = 60
    settings.quality = 92
    folder = ROOT / 'blender/exports/colonist-textures/runtime'
    folder.mkdir(parents=True, exist_ok=True)
    images = {}
    for mat in {m for o in objects for m in o.data.materials}:
        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE' or not node.image:
                continue
            source = node.image
            key = (source.filepath, source.colorspace_settings.name)
            if str(folder) in source.filepath:
                images[key] = source
            if key not in images:
                normal = source.colorspace_settings.name == 'Non-Color'
                masked = any(word in mat.name for word in ['hair', 'beard', 'eyebrows']) and not normal
                delivery = source.copy()
                max_size = 1024 if normal and 'Skin' not in source.name else 2048
                width, height = delivery.size
                if max(width, height) > max_size:
                    factor = max_size / max(width, height)
                    delivery.scale(round(width * factor), round(height * factor))
                image_scene.view_settings.view_transform = 'Raw' if normal else 'Standard'
                settings.file_format = 'PNG' if normal or masked else 'JPEG'
                settings.color_mode = 'RGBA' if masked else 'RGB'
                suffix = '.png' if normal or masked else '.jpg'
                path = folder / (Path(source.filepath).stem + suffix)
                delivery.save_render(str(path), scene=image_scene)
                loaded = bpy.data.images.load(str(path), check_existing=True)
                loaded.colorspace_settings.name = 'Non-Color' if normal else 'sRGB'
                images[key] = loaded
                bpy.data.images.remove(delivery)
            node.image = images[key]
    bpy.data.scenes.remove(image_scene)

    # Explicit browser skin conversion on export copies only. Source head
    # geometry and its original MPFB weights remain in the .blend unchanged.
    changed, maximum_removed = 0, 0.0
    for obj in objects:
        obj.data.validate(verbose=False, clean_customdata=False)
        groups = {g.index: g for g in obj.vertex_groups if g.name in rig.data.bones}
        for vertex in obj.data.vertices:
            weights = sorted([(g.group, g.weight) for g in vertex.groups
                              if g.group in groups and g.weight > 0], key=lambda x: -x[1])
            assert weights, obj.name + ' has an unweighted vertex'
            retained = weights[:4]
            total = sum(value for _, value in retained)
            maximum_removed = max(maximum_removed, sum(v for _, v in weights[4:]))
            changed += len(weights) > 4 or abs(total - 1) > 1e-5
            for group, _ in weights:
                groups[group].remove([vertex.index])
            for group, value in retained:
                groups[group].add([vertex.index], value / total, 'REPLACE')
        for group in list(obj.vertex_groups):
            if group.name not in rig.data.bones:
                obj.vertex_groups.remove(group)

    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    proxy.hide_render = False
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    destination = ROOT / 'public/assets/player-candidate.glb'
    try:
        bpy.ops.export_scene.gltf(
            filepath=str(destination), export_format='GLB', use_selection=True,
            use_active_scene=True, export_yup=True, export_apply=False,
            export_extras=True, export_animations=True, export_animation_mode='NLA_TRACKS',
            export_nla_strips=True, export_force_sampling=True, export_frame_step=1,
            export_cameras=False, export_lights=False, export_all_influences=False,
            export_image_format='AUTO')
    finally:
        proxy.hide_render = True
    # NLA-track export does not forward Action extras. Preserve the measured
    # in-place stride velocities explicitly in the glTF animation extras.
    import struct
    raw = destination.read_bytes()
    json_length = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + json_length])
    for animation in document['animations']:
        name = animation['name']
        track = next(t for t in rig.animation_data.nla_tracks if t.name == name)
        speed = track.strips[0].action.get('nominalMetersPerSecond')
        if name in ('walk', 'run'):
            assert speed and speed > 0
            animation.setdefault('extras', {})['nominalMetersPerSecond'] = speed
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    binary_chunk = raw[20 + json_length:]
    destination.write_bytes(struct.pack('<4sII', b'glTF', 2, 20 + len(encoded) + len(binary_chunk))
                            + struct.pack('<I4s', len(encoded), b'JSON') + encoded + binary_chunk)
    for obj in objects:
        obj.data.calc_loop_triangles()
    report = {'candidate': str(destination), 'bytes': destination.stat().st_size,
              'triangles': sum(len(o.data.loop_triangles) for o in objects),
              'visibleTriangles': sum(len(o.data.loop_triangles) for o in objects if o != proxy),
              'shadowProxyTriangles': len(proxy.data.loop_triangles),
              'meshes': len(objects), 'materials': sorted({m.name for o in objects for m in o.data.materials}),
              'bones': len(rig.data.bones), 'samplingFPS': bpy.context.scene.render.fps,
              'verticesConvertedToFourNormalizedWeights': changed,
              'maximumDroppedWeight': maximum_removed,
              'liveAssetReplaced': False}
    previous = json.loads(rig.get('colonistWeightConversion', '{}'))
    report['verticesConvertedToFourNormalizedWeights'] += previous.get('verticesConvertedToFourNormalizedWeights', 0)
    report['maximumDroppedWeight'] = max(maximum_removed, previous.get('maximumDroppedWeight', 0))
    rig['colonistWeightConversion'] = json.dumps({key: report[key] for key in
        ['verticesConvertedToFourNormalizedWeights', 'maximumDroppedWeight']})
    (ROOT / 'blender/previews/character-replacement/export-report.json').write_text(json.dumps(report, indent=2))
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/scenes/15_character_candidate.blend'))
    return report
