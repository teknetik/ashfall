"""Builds the MPFB2 player body for the tutorial set: phenotype, skin, eyes, brows, lashes, hair, game_engine rig
renamed to the game's skeleton names, helpers stripped, 1.80 m. Saves mpfb/body.blend + renders."""
import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from mpfblib import *
args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
TAG = args[0] if args else 'v1'
BEARD = args[1] if len(args) > 1 else ''
FACEONLY = len(args) > 2 and args[2] == 'face'
info = HS._create_default_human_info_dict()
info['phenotype'] = dict(MACRO, height=0.6, age=0.62)
info['targets'] = [{'target': 'head-square', 'value': 0.45}, {'target': 'chin-width-incr', 'value': 0.35},
                   {'target': 'chin-prominent-incr', 'value': 0.25}, {'target': 'head-age-incr', 'value': 0.25},
                   {'target': 'neck-scale-horiz-incr', 'value': 0.3},
                   {'target': 'measure-neck-height-incr', 'value': 0.3}, {'target': 'neck-scale-vert-incr', 'value': 0.1}]
if BEARD: info['clothes'] = [f'{BEARD}/{BEARD}.mhclo']
info['rig'] = 'game_engine'
info['eyes'] = 'high-poly/high-poly.mhclo'
info['eyebrows'] = 'eyebrow007/eyebrow007.mhclo'
info['eyelashes'] = 'eyelashes02/eyelashes02.mhclo'
info['hair'] = 'short02/short02.mhclo'
info['skin_mhmat'] = 'middleage_caucasian_male/middleage_caucasian_male.mhmat'
info['skin_material_type'] = 'MAKESKIN'
info['eyes_material_type'] = 'MAKESKIN'
info['alternative_materials'] = {}
bpy.ops.wm.read_homefile(use_empty=True)
st = HS.get_default_deserialization_settings(); st['subdiv_levels'] = 0
bm = HS.deserialize_from_dict(info, st)
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
print('PARTS', [(o.name, len(o.data.vertices), [m.type for m in o.modifiers], [s.material.name if s.material else None for s in o.material_slots]) for o in meshes])
for o in meshes: bake_mesh(o)
strip_helpers(bm)
rename_rig(rig, meshes)
print('SCALE', scale_to(rig, [bm] + [o for o in meshes if o != bm], 1.80))
lo, hi = eval_bounds(bm); print('HEIGHT %.3f' % (hi - lo).z)
if not FACEONLY: bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'mpfb' / f'body_{TAG}.blend'))
if not FACEONLY: render_views(str(OUT / 'mpfb' / f'body_{TAG}'), (0, 0, 0.9), 1.9, views=('front', 'side', 'back'), res=(450, 900))
head = rig.matrix_world @ rig.data.bones['Head'].head_local
render_views(str(OUT / 'mpfb' / f'face_{TAG}'), (head.x, head.y, head.z + 0.07), 0.32, views=('front', 'quarter', 'side'), res=(500, 500))
