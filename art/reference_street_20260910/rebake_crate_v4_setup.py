"""Author a new crate UV layout in live Blender; untouched source retained.
Run setup, then rebake_crate_v4_channel.py per channel through Blender MCP.
"""
import bpy,json,math,time
from pathlib import Path
R=Path('/home/teknetik/code/ao2');B=R/'meshy/ground-detail-20260910';O=B/'crate-v4-runtime'
assert not (O/'rebake-setup.json').exists(),'Immutable derivative already set up'
O.mkdir(exist_ok=True);(O/'model_textures').mkdir(exist_ok=True)
S=bpy.data.scenes.new('Crate v4 source to near PBR bake');bpy.context.window.scene=S
S.render.engine='CYCLES';S.cycles.samples=8
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='CUDA';p.get_devices()
 for d in p.devices:d.use=d.type=='CUDA'
 S.cycles.device='GPU'
except Exception:pass
S.render.bake.use_selected_to_active=True;S.render.bake.use_clear=True;S.render.bake.margin=24
S.render.bake.cage_extrusion=.006;S.render.bake.max_ray_distance=.020
S.render.bake.normal_space='TANGENT';S.render.bake.normal_r='POS_X';S.render.bake.normal_g='POS_Y';S.render.bake.normal_b='POS_Z'
obs={}
for label,folder in [('HIGH','crate-v3'),('LOW','crate-v3-runtime')]:
 before=set(S.objects);bpy.ops.import_scene.fbx(filepath=str(B/folder/'model.fbx'))
 imported=[o for o in S.objects if o not in before and o.type=='MESH'];assert len(imported)==1
 ob=imported[0];ob.name='CRATE_V4_'+label;obs[label]=ob
 # Native import transforms are identical for the matched source and near mesh.
 ob.data.calc_loop_triangles()
 assert len(ob.data.loop_triangles)==(1953204 if label=='HIGH' else 100000)
H=obs['HIGH'];L=obs['LOW'];assert all(abs(H.matrix_world[i][j]-L.matrix_world[i][j])<1e-6 for i in range(4) for j in range(4))
for ob in S.objects:ob.select_set(False)
L.select_set(True);bpy.context.view_layer.objects.active=L
while L.data.uv_layers: L.data.uv_layers.remove(L.data.uv_layers[0])
L.data.uv_layers.new(name='UVMap')
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004,area_weight=.5,correct_aspect=True,scale_to_bounds=False)
bpy.ops.object.mode_set(mode='OBJECT')
HM=bpy.data.materials.new('Crate v4 detailed source PBR');HM.use_nodes=True;N=HM.node_tree.nodes;K=HM.node_tree.links;P=N.get('Principled BSDF')
for name,socket in [('base_color','Base Color'),('roughness','Roughness'),('metallic','Metallic'),('normal','Normal')]:
 T=N.new('ShaderNodeTexImage');T.name='SOURCE_'+name;T.image=bpy.data.images.load(str(B/'crate-v3/model_textures'/(name+'.png')),check_existing=True)
 if name!='base_color':T.image.colorspace_settings.name='Non-Color'
 if name=='normal':
  Q=N.new('ShaderNodeNormalMap');Q.name='SOURCE_GL_NORMAL';K.new(T.outputs['Color'],Q.inputs['Color']);K.new(Q.outputs['Normal'],P.inputs[socket])
 else:K.new(T.outputs['Color'],P.inputs[socket])
H.data.materials.clear();H.data.materials.append(HM)
LM=bpy.data.materials.new('Crate v4 baked near PBR');LM.use_nodes=True;L.data.materials.clear();L.data.materials.append(LM)
(O/'rebake-setup.json').write_text(json.dumps(dict(source='crate-v3/model.fbx',runtimeGeometry='crate-v3-runtime/model.fbx',sourceTriangles=1953204,runtimeTriangles=100000,geometryUnchanged=True,uv='Blender Smart Project, 66 degrees, island margin .004, area weight .5',bake='Cycles selected-to-active, emission-only color/scalars, tangent normal +X/+Y/+Z',resolution=[4096,4096],samples=8,cageExtrusionSourceUnits=.006,maxRayDistanceSourceUnits=.020,marginPixels=24,sourcePbrOriginalsRetained=True,visualAcceptance=False),indent=2))
bpy.data.libraries.write(str(O/'rebake-authoring-setup.blend'),{S},fake_user=True)
print(json.dumps({'scene':S.name,'high':H.name,'low':L.name,'uvLoops':len(L.data.uv_layers.active.data)}))
