"""Free, licensed human-base audition. Execute through live Blender MCP.

Requires MPFB 2.0.17 (local Blender extension) and the source assets recorded in
blender/sources/makehuman. Leaves the accepted world scene and exports intact.
"""
import bpy, math, os, json
from pathlib import Path
from mathutils import Vector
from bl_ext.user_default.mpfb.services import HumanService, TargetService, LocationService

ROOT = Path('/Users/carl.draper/Documents/code/ao2')
SOURCE = ROOT / 'blender/sources/makehuman'
NAME = 'Character_Audition'
old = bpy.data.scenes.get(NAME)
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.context.window.scene = bpy.data.scenes['AthenHill_AuthoredWorld']
    bpy.data.scenes.remove(old)
scene = bpy.data.scenes.new(NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Character_Audition_World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.18, .21, .24, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .35

macro = TargetService.get_default_macro_info_dict()
macro.update(gender=1.0, age=.62, muscle=.72, weight=.46, proportions=.62, height=.5,
             race={'caucasian': 1., 'asian': 0., 'african': 0.})
body = HumanService.create_human(macro_detail_dict=macro)
body.name = 'CHR_colonist_base_mpfb'
targets = {'head/head-square': .22, 'head/head-rectangular': .12,
           'chin/chin-width-incr': .18, 'chin/chin-bones-incr': .16,
           'chin/chin-prominent-incr': .12, 'eyebrows/eyebrows-trans-down': .08,
           'eyebrows/eyebrows-trans-forward': .12, 'nose/nose-scale-depth-incr': .10,
           'cheek/l-cheek-bones-incr': .10, 'cheek/r-cheek-bones-incr': .10}
for target, value in targets.items():
    path = Path(LocationService.get_mpfb_data('targets')) / (target + '.target.gz')
    if not path.exists():
        raise FileNotFoundError(path)
    TargetService.load_target(body, str(path), weight=value)
rig = HumanService.add_builtin_rig(body, 'game_engine')
rig.name = 'RIG_colonist_mpfb'
HumanService.set_character_skin(str(SOURCE / 'skins/middleage_caucasian_male/middleage_caucasian_male.mhmat'),
                               body, skin_type='GAMEENGINE', material_instances=False)
for asset, kind in [('eyes/low-poly', 'Eyes'), ('eyebrows/eyebrow001', 'Eyebrows'),
                    ('clothes/grinsegold_beard_sigmund_wip', 'Clothes'),
                    ('hair/elvs_grump_hair', 'Hair')]:
    path = next((SOURCE / asset).glob('*.mhclo'))
    HumanService.add_mhclo_asset(str(path), body, asset_type=kind,
                              subdiv_levels=0, material_type='GAMEENGINE')

# Freeze the fitted macro/asset shape before local styling or material regions.
# Editing raw base vertices while fit keys remain active distorts the result.
for obj in list(scene.objects):
    if obj.type == 'MESH' and obj.data.shape_keys:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body
for modifier in list(body.modifiers):
    if modifier.type == 'MASK':
        bpy.ops.object.modifier_apply(modifier=modifier.name)

def simple_material(name, color, roughness=.65, metal=0.):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metal
    return mat

# A fitted, dark under-suit covers the skin below neck and wrists. Armour will
# replace much of this visible surface; real facial/hand topology stays intact.
suit = simple_material('MAT_colonist_undersuit', (.028, .035, .033), .84)
body.data.materials.append(suit)
for poly in body.data.polygons:
    c = sum((body.data.vertices[i].co for i in poly.vertices), Vector()) / len(poly.vertices)
    skin = c.z > rig.data.bones['neck_01'].head_local.z - .025 or (abs(c.x) > .478 and c.z < 1.14)
    if not skin:
        poly.material_index = 1

for obj in scene.objects:
    if obj.type != 'MESH':
        continue
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if 'grump_hair' in obj.name:
        # Reduce the tall pompadour while retaining authored sweeping strands.
        scalp_top = max(v.co.z for v in body.data.vertices if abs(v.co.x) < .1)
        for v in obj.data.vertices:
            if v.co.z > scalp_top:
                v.co.z = scalp_top + (v.co.z - scalp_top) * .62
    for mat in obj.data.materials:
        shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not shader:
            continue
        shader.inputs['Emission Color'].default_value = (0, 0, 0, 1)
        shader.inputs['Emission Strength'].default_value = 0
        shader.inputs['Metallic'].default_value = 0
        shader.inputs['Roughness'].default_value = .59 if obj == body else .74
        shader.inputs['Specular IOR Level'].default_value = .3
        if obj.name.endswith('.low-poly'):
            shader.inputs['Roughness'].default_value = .13
            shader.inputs['Specular IOR Level'].default_value = .5
            shader.inputs['Coat Weight'].default_value = .3
        if any(word in obj.name for word in ['hair', 'beard', 'moustache']):
            source = shader.inputs['Base Color'].links[0].from_socket if shader.inputs['Base Color'].is_linked else None
            if source:
                mix = mat.node_tree.nodes.new('ShaderNodeMixRGB')
                mix.blend_type = 'MULTIPLY'
                mix.inputs[0].default_value = 1
                mix.inputs[2].default_value = (.14, .10, .072, 1)
                mat.node_tree.links.new(source, mix.inputs[1])
                mat.node_tree.links.new(mix.outputs[0], shader.inputs['Base Color'])
            mat.surface_render_method = 'DITHERED'
            mat.use_transparency_overlap = False

bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(depsgraph)
low = min((evaluated.matrix_world @ v.co).z for v in evaluated.data.vertices)
high = max((evaluated.matrix_world @ v.co).z for v in evaluated.data.vertices)
rig.scale = (1.8 / (high - low),) * 3
rig.location.z = -low * rig.scale.z

ground_mat = simple_material('MAT_audition_ground', (.105, .12, .13), .9)
bpy.ops.mesh.primitive_plane_add(size=200)
ground = bpy.context.object
ground.name = 'AUDITION_ground'
ground.data.materials.append(ground_mat)

def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()

for name, position, energy, size, color in [
    ('Key', (-3, -4, 5), 600, 4, (1., .87, .7)),
    ('Fill', (3, -2, 3), 180, 3, (.65, .79, 1.)),
    ('Rim', (1, 3, 4), 750, 3, (.65, .79, 1.)),
]:
    data = bpy.data.lights.new('AUDITION_' + name, 'AREA')
    data.energy, data.shape, data.size, data.color = energy, 'DISK', size, color
    obj = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(obj)
    obj.location = position
    aim(obj, (0, 0, 1))
data = bpy.data.cameras.new('AUDITION_portrait')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
camera.location = (.48, -1.65, 1.74)
data.lens = 72
aim(camera, (0, -.035, 1.64))
scene.camera = camera
scene.render.resolution_x, scene.render.resolution_y = 768, 1024
folder = ROOT / 'blender/previews/character-replacement'
folder.mkdir(exist_ok=True, parents=True)
scene.render.filepath = str(folder / '04_free_base_portrait.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'blender/scenes/12_character_audition.blend'))
print(json.dumps({'scene': scene.name, 'portrait': scene.render.filepath,
                  'height': 1.8, 'source': 'MakeHuman Community / MPFB 2.0.17',
                  'state': 'source audition, armour and runtime integration pending'}))
