"""Editable procedural PBR finishes for the Karaveen artisan stall.

Run in Blender 4.5 through the live Blender MCP; call ``create_materials()``.
This module creates/rebuilds only materials with the explicit KA_ names below.
It never creates geometry, changes the scene, or imports/exports an asset.

Cloth meshes use metre-projected UVMap coordinates for both yarn directions.
Other finishes use object coordinates authored for metres: apply object scale.
Large, physically exposed cabinet edges should receive ``bare_steel`` explicitly.
The optional per-vertex float attribute ``KA_paint_wear`` (0..1) permits local
paint chips at handles, hinges and lower panel edges. An absent attribute is zero.
There is deliberately no all-over dirt or fake directional lighting in albedo.
"""

import bpy


def _rgba(hex_color):
    rgb = [int(hex_color.lstrip('#')[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
                 for c in rgb) + (1.0,)


def _node(nodes, kind, name, xy):
    n = nodes.new(kind)
    n.name = 'KA_' + name
    n.label = name.replace('_', ' ')
    n.location = xy
    return n


def _new(name, color, metallic, roughness):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = _rgba(color)
    mat.metallic = metallic
    mat.roughness = roughness
    mat['KA_authoring'] = 'Karaveen artisan; original procedural PBR, 2026-09-10'
    mat['KA_coordinate_scale'] = 'Object coordinates in metres; apply mesh scales'
    mat.node_tree.nodes.clear()
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = _node(nodes, 'ShaderNodeOutputMaterial', 'Surface_Output', (960, 120))
    bsdf = _node(nodes, 'ShaderNodeBsdfPrincipled', 'PBR_Surface', (680, 120))
    bsdf.inputs['Base Color'].default_value = _rgba(color)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    tex = _node(nodes, 'ShaderNodeTexCoord', 'Metre_Coordinates', (-1120, 120))
    return mat, nodes, links, bsdf, tex.outputs['Object']


def _noise(nodes, links, coords, name, scale, detail, xy):
    n = _node(nodes, 'ShaderNodeTexNoise', name, xy)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = .55
    links.new(coords, n.inputs['Vector'])
    return n.outputs['Fac']


def _ramp(nodes, links, fac, name, low, high, xy, positions=(.18, .82)):
    n = _node(nodes, 'ShaderNodeValToRGB', name, xy)
    n.color_ramp.elements[0].position = positions[0]
    n.color_ramp.elements[0].color = low
    n.color_ramp.elements[1].position = positions[1]
    n.color_ramp.elements[1].color = high
    links.new(fac, n.inputs['Fac'])
    return n.outputs['Color']


def _roughness(nodes, links, fac, bsdf, low, high, xy=(340, -50)):
    value = _ramp(nodes, links, fac, 'Roughness_Variation',
                  (low, low, low, 1), (high, high, high, 1), xy)
    links.new(value, bsdf.inputs['Roughness'])


def _bump(nodes, links, height, bsdf, strength, distance, xy=(360, -260)):
    n = _node(nodes, 'ShaderNodeBump', 'Micro_Surface_Only', xy)
    n.inputs['Strength'].default_value = strength
    n.inputs['Distance'].default_value = distance
    links.new(height, n.inputs['Height'])
    links.new(n.outputs['Normal'], bsdf.inputs['Normal'])


def _canvas(name, low, high, use_uv=True):
    mat, nodes, links, bsdf, coords = _new(name, high, 0, .86)
    mat['KA_finish'] = 'Sand cotton canvas; approximately 1.6 mm heavy plain-weave repeat'
    if use_uv:
        uv = _node(nodes, 'ShaderNodeUVMap', 'Metre_Projected_Cloth_UV', (-1120, -120))
        uv.uv_map = 'UVMap'
        coords = uv.outputs['UV']
        mat['KA_coordinate_scale'] = 'UVMap planar projection in metres, not normalized 0..1'
    else:
        mat['KA_coordinate_scale'] = 'Object coordinates in metres for modeled seam curves'
    if 'Sheen Weight' in bsdf.inputs:
        bsdf.inputs['Sheen Weight'].default_value = .08
    if 'Sheen Roughness' in bsdf.inputs:
        bsdf.inputs['Sheen Roughness'].default_value = .82
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = .28
    variation = _noise(nodes, links, coords, 'Quiet_Dye_Variation', 4.8, 2.4, (-860, 360))
    color = _ramp(nodes, links, variation, 'Undyed_Canvas_Color',
                  _rgba(low), _rgba(high), (-550, 370), (.28, .72))
    _roughness(nodes, links, variation, bsdf, .81, .93)
    warp = _node(nodes, 'ShaderNodeTexWave', 'Warp_Yarn', (-860, -50))
    weft = _node(nodes, 'ShaderNodeTexWave', 'Weft_Yarn', (-860, -320))
    for wave, direction in ((warp, 'X'), (weft, 'Y')):
        wave.wave_type = 'BANDS'
        wave.bands_direction = direction
        wave.wave_profile = 'SIN'
        wave.inputs['Scale'].default_value = 195.0
        wave.inputs['Distortion'].default_value = .25
        wave.inputs['Detail'].default_value = 1.0
        wave.inputs['Detail Scale'].default_value = 1.0
        links.new(coords, wave.inputs['Vector'])
    weave = _node(nodes, 'ShaderNodeMath', 'Crossing_Yarns', (-560, -150))
    weave.operation = 'MULTIPLY'
    links.new(warp.outputs['Fac'], weave.inputs[0])
    links.new(weft.outputs['Fac'], weave.inputs[1])
    yarn_color = _ramp(nodes, links, weave.outputs[0], 'Natural_Yarn_Tone',
                       (.77, .77, .77, 1), (1, 1, 1, 1), (-280, -140), (.12, .80))
    tint = _node(nodes, 'ShaderNodeMixRGB', 'Dye_On_Woven_Yarns', (100, 350))
    tint.blend_type = 'MULTIPLY'
    tint.inputs[0].default_value = 1.0
    links.new(color, tint.inputs[1])
    links.new(yarn_color, tint.inputs[2])
    links.new(tint.outputs[0], bsdf.inputs['Base Color'])
    _bump(nodes, links, weave.outputs[0], bsdf, .62, .00042)
    return mat


def _metal(name, low, high, metallic, roughness, paint=False):
    mat, nodes, links, bsdf, coords = _new(name, high, metallic, roughness)
    variation = _noise(nodes, links, coords, 'Quiet_Finish_Variation', 5.0, 2, (-860, 400))
    color = _ramp(nodes, links, variation, 'Finish_Color',
                  _rgba(low), _rgba(high), (-570, 440))
    _roughness(nodes, links, variation, bsdf, roughness - .07, roughness + .06)
    fine = _noise(nodes, links, coords, 'Fine_Surface_Tooth', 360.0, 2, (-850, -370))
    _bump(nodes, links, fine, bsdf, .16, .00009)
    if paint:
        mat['KA_finish'] = 'Faded ochre paint; localized chips driven by KA_paint_wear'
        attr = _node(nodes, 'ShaderNodeAttribute', 'Localized_Contact_Wear', (-1100, -80))
        attr.attribute_name = 'KA_paint_wear'
        chip = _noise(nodes, links, coords, 'Millimetre_Paint_Chips', 125, 2, (-850, 110))
        chip_shape = _ramp(nodes, links, chip, 'Broken_Paint_Edges',
                           (0, 0, 0, 1), (1, 1, 1, 1), (-570, 100), (.46, .67))
        mask = _node(nodes, 'ShaderNodeMath', 'Contact_Region_Only', (-280, 130))
        mask.operation = 'MULTIPLY'
        mask.use_clamp = True
        links.new(attr.outputs['Fac'], mask.inputs[0])
        links.new(chip_shape, mask.inputs[1])
        mix = _node(nodes, 'ShaderNodeMixRGB', 'Paint_And_Exposed_Steel', (90, 360))
        mix.blend_type = 'MIX'
        links.new(mask.outputs[0], mix.inputs[0])
        links.new(color, mix.inputs[1])
        mix.inputs[2].default_value = _rgba('59574F')
        links.new(mix.outputs[0], bsdf.inputs['Base Color'])
        metal = _node(nodes, 'ShaderNodeMapRange', 'Exposed_Metal_Response', (90, 150))
        metal.inputs['To Min'].default_value = metallic
        metal.inputs['To Max'].default_value = .75
        links.new(mask.outputs[0], metal.inputs['Value'])
        links.new(metal.outputs[0], bsdf.inputs['Metallic'])
    else:
        links.new(color, bsdf.inputs['Base Color'])
    return mat


def _rubber():
    mat, nodes, links, bsdf, coords = _new('KA_Rubber_Feet', '272923', 0, .86)
    variation = _noise(nodes, links, coords, 'Rubber_Surface_Tooth', 550, 2, (-750, 150))
    color = _ramp(nodes, links, variation, 'Charcoal_Rubber',
                  _rgba('242521'), _rgba('2D2E28'), (-400, 270))
    links.new(color, bsdf.inputs['Base Color'])
    _roughness(nodes, links, variation, bsdf, .79, .90)
    _bump(nodes, links, variation, bsdf, .15, .00015)
    return mat


def _rope():
    mat, nodes, links, bsdf, coords = _new('KA_Hemp_Lashing', '766044', 0, .90)
    variation = _noise(nodes, links, coords, 'Fine_Rope_Fibres', 800, 2, (-750, 150))
    color = _ramp(nodes, links, variation, 'Hemp_Fibre_Color',
                  _rgba('746048'), _rgba('958064'), (-400, 270))
    links.new(color, bsdf.inputs['Base Color'])
    _bump(nodes, links, variation, bsdf, .20, .00014)
    return mat


def create_canvas_materials():
    """Rebuild only the three canvas finishes already bound to live geometry."""
    return {
        'canvas': _canvas('KA_Sand_Canvas', '9F835F', 'BCA07B'),
        'canvas_patch': _canvas('KA_Canvas_Repair_Patch', '967852', 'AC926F'),
        'seam': _canvas('KA_Canvas_Seam_Webbing', 'A08A66', 'BCA481', use_uv=False),
    }


def create_materials():
    """Return materials for editable stall components; safe to call repeatedly.

    Replaces node trees only on this module's ten explicit material names.
    The ``seam`` finish is slightly lighter canvas for stitched hems and webbing;
    use modeled seam curves/strips so their appearance remains construction-led.
    """
    return {
        **create_canvas_materials(),
        'frame': _metal('KA_Charcoal_Frame_Steel', '393B37', '494B45', .72, .62),
        'brass': _metal('KA_Dull_Brass_Fasteners', '8C7750', 'AA9568', .82, .51),
        'cabinet': _metal('KA_Faded_Ochre_Cabinet', '756B53', '928266', .07, .70, paint=True),
        'shelf': _metal('KA_Worn_Metal_Shelves', '494B43', '656255', .65, .62),
        'rubber': _rubber(),
        'rope': _rope(),
        'bare_steel': _metal('KA_Exposed_Edge_Steel', '56564E', '7D7A6C', .80, .53),
    }


if __name__ == '__main__':
    materials = create_materials()
    print('Karaveen artisan materials: ' + ', '.join(materials))
