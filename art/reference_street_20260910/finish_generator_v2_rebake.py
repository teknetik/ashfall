"""STAGED: bind the near object's own four completed PBR bakes and export candidate.
Export success is not visual acceptance. Then rerender identical source/near views
with tag rebaked and submit the close crops to the independent critic.
"""
import sys
from pathlib import Path
P = Path('/home/teknetik/code/ao2/art/reference_street_20260910')
if str(P) not in sys.path:
    sys.path.insert(0, str(P))
from generator_v2_review_common import *

scene = bpy.data.scenes[SCENE]
bpy.context.window.scene = scene
high = bpy.data.objects[scene['generator_source_object']]
near = bpy.data.objects[scene['generator_near_object']]
out = Path(scene['generator_near_output'])
assert not (out / 'model.fbx').exists(), 'Retain prior export; do not overwrite runtime geometry'
source_contract()
records = []
for channel in CHANNELS:
    record = json.loads((out / ('bake-' + channel + '.json')).read_text())
    assert record['sha256'] == sha(out / 'model_textures' / (channel + '.png'))
    assert record['dimensions'] == [4096, 4096]
    records.append(record)
material = near.data.materials[0]
nodes, links = material.node_tree.nodes, material.node_tree.links
shader = nodes.get('Principled BSDF')
for channel, socket in [('base_color','Base Color'), ('metallic','Metallic'), ('roughness','Roughness'), ('normal','Normal')]:
    texture = nodes['BAKED_' + channel]
    if channel == 'normal':
        normal = nodes.new('ShaderNodeNormalMap')
        normal.name = 'BAKED_GL_NORMAL'
        normal.uv_map = 'UVMap'
        links.new(texture.outputs['Color'], normal.inputs['Color'])
        links.new(normal.outputs['Normal'], shader.inputs[socket])
    else:
        links.new(texture.outputs['Color'], shader.inputs[socket])
for obj in scene.objects:
    obj.select_set(False)
high.hide_render = True
near.hide_render = False
near.hide_set(False)
near.select_set(True)
bpy.context.view_layer.objects.active = near
bpy.ops.export_scene.fbx(filepath=str(out / 'model.fbx'), use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
    bake_space_transform=False, add_leaf_bones=False, path_mode='AUTO', axis_forward='-Z', axis_up='Y')
scene['generator_near_uv_state'] = 'Four own PBR maps bound; matched comparison and native acceptance pending'
scene.cycles.samples = 24
bpy.data.libraries.write(str(out / 'generator-v2-rebake-authoring.blend'), {scene}, fake_user=True)
near.data.calc_loop_triangles()
write_new(out / 'runtime-manifest.json', {'source': str(SOURCE.relative_to(REPO)), 'sourceRetained': True, 'sourceTriangles': FBX_TRIANGLES, 'retainedGlbTriangles': 1945352,
    'nearTriangles': len(near.data.loop_triangles), 'sourcePbrDimensions': {'base_color':[4096,4096],'normal':[4096,4096],'metallic':[2048,2048],'roughness':[2048,2048]},
    'runtimeMapDimensions': [4096,4096], 'normalConvention': 'Tangent GL+Y', 'bakeSettings': json.loads((out / 'rebake-setup.json').read_text()),
    'method': 'Selected-to-active full detailed source PBR reprojection onto new near UV0; unlit emission color/scalars and tangent-space source normal projection.',
    'canonicalUnityXYZMetres': [1.6,1.1,.95], 'uniformFitRetained': True, 'bakes': records,
    'sha256': {str(path.relative_to(out)):sha(path) for path in [out / 'model.fbx', *sorted((out / 'model_textures').glob('*.png'))]},
    'sourceReviewAcceptedForDerivation': bool(scene.get('generator_source_approval')), 'mappingVisualAcceptance': False, 'nativeAccepted': False,
    'requires': 'Exact-position source and rebaked near comparisons, grille/eyelet/coil close inspection, native sun/shade and moving audition, measured frame-time/memory cost.',
    'blenderMemory': memory_record()})
source_contract()
print(json.dumps({'fbx': str(out / 'model.fbx'), 'nearTriangles': len(near.data.loop_triangles), 'memory': memory_record()}))
