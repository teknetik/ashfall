"""Production PBR materials for the imported colonist; run through Blender MCP.

Source maps stay untouched. A neutral wear tile is baked from the licensed
paint scan using Blender, so the same olive vertex palette survives glTF.
"""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path('/Users/carl.draper/Documents/code/ao2')
SOURCE = ROOT / 'blender/sources'
DERIVED = ROOT / 'blender/exports/colonist-textures'


def multiply(nodes, links, a, b):
    node = nodes.new('ShaderNodeMix')
    node.data_type = 'RGBA'
    node.blend_type = 'MULTIPLY'
    node.inputs[0].default_value = 1
    links.new(a, node.inputs[6])
    if isinstance(b, tuple):
        node.inputs[7].default_value = b
    else:
        links.new(b, node.inputs[7])
    return node.outputs[2]


def neutral_wear():
    DERIVED.mkdir(parents=True, exist_ok=True)
    path = DERIVED / 'neutral_paint_wear.png'
    if path.exists():
        return bpy.data.images.load(str(path), check_existing=True)
    # A separate temporary bake scene prevents touching either world or actor.
    previous = bpy.context.window.scene
    scene = bpy.data.scenes.new('Colonist_Texture_Bake')
    bpy.context.window.scene = scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    scene.cycles.device = 'CPU'
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.object
    mat = bpy.data.materials.new('TEMP_neutral_wear')
    mat.use_nodes = True
    plane.data.materials.append(mat)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    output = nodes.new('ShaderNodeOutputMaterial')
    emission = nodes.new('ShaderNodeEmission')
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(SOURCE / 'polyhaven/blue_metal_plate/blue_metal_plate_diff_2k.png'), check_existing=True)
    bw = nodes.new('ShaderNodeRGBToBW')
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .012
    ramp.color_ramp.elements[0].color = (.32, .32, .32, 1)
    ramp.color_ramp.elements[1].position = .16
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(texture.outputs['Color'], bw.inputs[0])
    links.new(bw.outputs[0], ramp.inputs[0])
    links.new(ramp.outputs[0], emission.inputs[0])
    links.new(emission.outputs[0], output.inputs['Surface'])
    image = bpy.data.images.new('Colonist_neutral_paint_wear', 2048, 2048, alpha=False)
    target = nodes.new('ShaderNodeTexImage')
    target.image = image
    nodes.active = target
    bpy.ops.object.bake(type='EMIT', margin=0)
    image.filepath_raw = str(path)
    image.file_format = 'PNG'
    image.save()
    bpy.context.window.scene = previous
    bpy.data.objects.remove(plane, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.materials.remove(mat)
    return image


def prepare_colonist_materials(rig):
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH'
               and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
    material_set = {m for o in objects for m in o.data.materials}
    # Cached MPFB images can retain a /tmp path even when a curated mhmat is
    # loaded. Resolve every actual node to the retained source before saving.
    sources = {}
    for path in (SOURCE / 'makehuman').rglob('*'):
        if path.is_file():
            sources.setdefault(path.name, []).append(path)
    for mat in material_set:
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                matches = sources.get(Path(node.image.filepath).name, [])
                if matches:
                    node.image.filepath = str(matches[0])
                    node.image.reload()

    wear = neutral_wear()
    olive = bpy.data.materials['MAT_colonist_armour_olive']
    graphite = bpy.data.materials['MAT_colonist_armour_graphite']
    cyan = bpy.data.materials['MAT_colonist_armour_cyan']
    for mat, asset, metallic, normal_strength in [
        (olive, 'blue_metal_plate', .48, .65),
        (graphite, 'fabric_leather_01', .05, .55),
    ]:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        nodes.clear()
        output = nodes.new('ShaderNodeOutputMaterial')
        shader = nodes.new('ShaderNodeBsdfPrincipled')
        links.new(shader.outputs[0], output.inputs['Surface'])
        shader.inputs['Metallic'].default_value = metallic
        shader.inputs['Roughness'].default_value = .65
        shader.inputs['Specular IOR Level'].default_value = .4
        color = nodes.new('ShaderNodeVertexColor')
        color.layer_name = 'COLOR_0'
        uv = nodes.new('ShaderNodeUVMap')
        uv.uv_map = 'SurfaceUV'
        if mat == olive:
            albedo = nodes.new('ShaderNodeTexImage')
            albedo.image = wear
            links.new(uv.outputs[0], albedo.inputs['Vector'])
            links.new(multiply(nodes, links, color.outputs['Color'], albedo.outputs['Color']), shader.inputs['Base Color'])
        else:
            links.new(color.outputs['Color'], shader.inputs['Base Color'])
        for suffix, socket in [('rough', 'Roughness'), ('nor_gl', 'Normal')]:
            texture = nodes.new('ShaderNodeTexImage')
            texture.image = bpy.data.images.load(str(SOURCE / f'polyhaven/{asset}/{asset}_{suffix}_2k.png'), check_existing=True)
            texture.image.colorspace_settings.name = 'Non-Color'
            links.new(uv.outputs[0], texture.inputs['Vector'])
            if socket == 'Normal':
                normal = nodes.new('ShaderNodeNormalMap')
                normal.inputs['Strength'].default_value = normal_strength
                normal.uv_map = 'SurfaceUV'
                links.new(texture.outputs['Color'], normal.inputs['Color'])
                links.new(normal.outputs[0], shader.inputs[socket])
            else:
                # Broad metal is worn satin; the scan's original polished paint
                # roughness made the whole suit read like black plastic.
                if mat == olive:
                    shader.inputs[socket].default_value = .57
                else:
                    links.new(texture.outputs['Color'], shader.inputs[socket])

    for obj in objects:
        is_armour = bool(obj.get('colonistArmourV1'))
        body = any('undersuit' in m.name for m in obj.data.materials) or (any('colonist_skin' in m.name for m in obj.data.materials) and any(m == graphite for m in obj.data.materials))
        if is_armour or body:
            uv = obj.data.uv_layers.get('SurfaceUV') or obj.data.uv_layers.new(name='SurfaceUV')
            # Box projection of rest geometry avoids collapsing the sides of
            # greaves/arms. Skin and hair retain their original authored UVs.
            for p in obj.data.polygons:
                axis = max(range(3), key=lambda i: abs(p.normal[i]))
                axes = (1, 2) if axis == 0 else (0, 2) if axis == 1 else (0, 1)
                for li in p.loop_indices:
                    co = obj.matrix_world @ obj.data.vertices[obj.data.loops[li].vertex_index].co
                    frequency = 2.1 if is_armour and any(m == olive for m in obj.data.materials) else 7.0
                    uv.data[li].uv = (co[axes[0]] * frequency, co[axes[1]] * frequency)
            colors = obj.data.color_attributes.get('COLOR_0') or obj.data.color_attributes.new(name='COLOR_0', type='FLOAT_COLOR', domain='CORNER')
            if body:
                skin_index = next(i for i, m in enumerate(obj.data.materials) if 'colonist_skin' in m.name or 'body.' in m.name)
                suit_index = next(i for i, m in enumerate(obj.data.materials) if 'undersuit' in m.name or m == graphite)
                for p in obj.data.polygons:
                    c = sum((obj.data.vertices[i].co for i in p.vertices), Vector()) / len(p.vertices)
                    skin = c.z > rig.data.bones['neck_01'].head_local.z or (abs(c.x) > .478 and c.z < 1.14)
                    p.material_index = skin_index if skin else suit_index
                    suit = 'undersuit' in obj.data.materials[p.material_index].name or obj.data.materials[p.material_index] == graphite
                    for li in p.loop_indices:
                        colors.data[li].color = (.019, .025, .024, 1) if suit else (1, 1, 1, 1)
                for i, mat in enumerate(obj.data.materials):
                    if 'undersuit' in mat.name:
                        obj.data.materials[i] = graphite
            elif any(m == olive for m in obj.data.materials):
                original = obj.data.color_attributes.get('AUTHORING_COLOR')
                if original is None:
                    original = obj.data.color_attributes.new(name='AUTHORING_COLOR', type='FLOAT_COLOR', domain='CORNER')
                    for target, source in zip(original.data, colors.data):
                        target.color = source.color
                for color, source in zip(colors.data, original.data):
                    # A darker neutral olive, with authored brighter bevels.
                    r, g, b, a = source.color
                    color.color = (.155, .17, .118, a) if r > .101 else (.135, .15, .103, a)

        for mat in obj.data.materials:
            if mat in (olive, graphite, cyan):
                continue
            shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            diffuse = nodes.get('DiffuseTexture')
            is_hair = any(word in obj.name for word in ('hair', 'beard'))
            if diffuse and is_hair:
                links.new(multiply(nodes, links, diffuse.outputs['Color'], (.18, .14, .10, 1)), shader.inputs['Base Color'])
                cutoff = nodes.new('ShaderNodeMath')
                cutoff.operation = 'GREATER_THAN'
                cutoff.inputs[1].default_value = .32
                links.new(diffuse.outputs['Alpha'], cutoff.inputs[0])
                links.new(cutoff.outputs[0], shader.inputs['Alpha'])
                shader.inputs['Roughness'].default_value = .57
                mat.use_backface_culling = False
            else:
                for link in list(shader.inputs['Alpha'].links):
                    links.remove(link)
                shader.inputs['Alpha'].default_value = 1
            if 'body.' in mat.name:
                mat.name = 'MAT_colonist_skin'
            if mat.name == 'MAT_colonist_skin':
                normal_texture = nodes.get('Colonist_skin_normal') or nodes.new('ShaderNodeTexImage')
                normal_texture.name = 'Colonist_skin_normal'
                normal_texture.image = bpy.data.images.load(str(SOURCE / 'makehuman/skins/mindfront_aksel_skin/Aksel_Skin_NRM.png'), check_existing=True)
                normal_texture.image.colorspace_settings.name = 'Non-Color'
                normal = nodes.get('Colonist_skin_normal_map') or nodes.new('ShaderNodeNormalMap')
                normal.name = 'Colonist_skin_normal_map'
                normal.inputs['Strength'].default_value = .22
                links.new(normal_texture.outputs['Color'], normal.inputs['Color'])
                links.new(normal.outputs[0], shader.inputs['Normal'])
                shader.inputs['Roughness'].default_value = .64
            elif 'low-poly' in mat.name:
                mat.name = 'MAT_colonist_eyes'
            elif 'grump_hair' in mat.name:
                mat.name = 'MAT_colonist_hair'
            elif 'beard' in mat.name:
                mat.name = 'MAT_colonist_beard'
    return {'materials': sorted({m.name for o in objects for m in o.data.materials}),
            'wear': str(DERIVED / 'neutral_paint_wear.png'),
            'sourceLicences': ['MakeHuman CC0 / hair CC-BY', 'Poly Haven CC0']}
