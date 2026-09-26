"""Finish immutable crate v4 PBR derivative and retain source/authoring record."""
import bpy,json,hashlib
from pathlib import Path
R=Path('/home/teknetik/code/ao2');B=R/'meshy/ground-detail-20260910';O=B/'crate-v4-runtime'
S=bpy.data.scenes['Crate v4 source to near PBR bake'];bpy.context.window.scene=S
H=bpy.data.objects['CRATE_V4_HIGH'];L=bpy.data.objects['CRATE_V4_LOW']
for C in ['base_color','metallic','roughness','normal']:assert (O/'model_textures'/(C+'.png')).exists(),C+' bake missing'
HM=H.data.materials[0];LM=L.data.materials[0];N=HM.node_tree.nodes;K=HM.node_tree.links;OUT=N.get('Material Output')
for link in list(OUT.inputs['Surface'].links):K.remove(link)
K.new(N.get('Principled BSDF').outputs['BSDF'],OUT.inputs['Surface'])
N=LM.node_tree.nodes;K=LM.node_tree.links;P=N.get('Principled BSDF')
for C,socket in [('base_color','Base Color'),('metallic','Metallic'),('roughness','Roughness'),('normal','Normal')]:
 T=N['BAKED_'+C]
 if C=='normal':
  Q=N.new('ShaderNodeNormalMap');Q.uv_map='UVMap';K.new(T.outputs['Color'],Q.inputs['Color']);K.new(Q.outputs['Normal'],P.inputs[socket])
 else:K.new(T.outputs['Color'],P.inputs[socket])
for ob in S.objects:ob.select_set(False)
H.hide_render=True;L.select_set(True);bpy.context.view_layer.objects.active=L
bpy.ops.export_scene.fbx(filepath=str(O/'model.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,path_mode='AUTO')
bpy.data.libraries.write(str(O/'rebake-authoring.blend'),{S},fake_user=True)
L.data.calc_loop_triangles();records=[json.loads((O/('bake-'+c+'.json')).read_text()) for c in ['base_color','metallic','roughness','normal']]
hashes={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O/'model.fbx',*sorted((O/'model_textures').glob('*.png'))]}
report=dict(source='meshy/ground-detail-20260910/crate-v3',sourceRetained=True,previousRuntime='meshy/ground-detail-20260910/crate-v3-runtime',previousDefect='Strong reduction preserved surface shape but interpolated original UVs displaced straight stencil paint into triangular wedges.',nearTriangles=len(L.data.loop_triangles),geometry='Exact retained 100000-triangle v3 runtime geometry; new non-overlapping Smart Project UV0',method='High-to-low selected-to-active Cycles reprojection of original full source PBR onto final runtime UV layout; albedo/metal/rough emit bakes exclude lighting, normal bake tangent +X/+Y/+Z includes source normal texture and full source surface normal.',settings=json.loads((O/'rebake-setup.json').read_text()),bakes=records,sha256=hashes,sourceMapsRetainedFullResolution=True,runtimeMapDimensions=[4096,4096],normal='Tangent GL +Y',visualAcceptance=False,requires='Matched full source/runtime material review and native player-height moving review')
(O/'runtime-manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'triangles':report['nearTriangles'],'files':hashes}))
