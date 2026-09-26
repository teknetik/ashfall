import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/reference_street_20260910');S=bpy.data.scenes['Threshold v2 metric UV and source roughness'];bpy.context.window.scene=S
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='CUDA';p.get_devices()
 for d in p.devices:d.use=d.type=='CUDA'
 S.cycles.device='GPU'
except Exception:pass
S.render.resolution_x=1280;S.render.resolution_y=900;S.render.resolution_percentage=100
S.world=bpy.data.worlds.new('Threshold v2 source review sky');S.world.use_nodes=True
S.world.node_tree.nodes['Background'].inputs[0].default_value=(.33,.43,.55,1);S.world.node_tree.nodes['Background'].inputs[1].default_value=.45
D=bpy.data.lights.new('Threshold v2 review sun','SUN');D.energy=2.2;D.angle=.06
L=bpy.data.objects.new(D.name,D);S.collection.objects.link(L);L.rotation_euler=(.55,-.6,-.7)
D=bpy.data.cameras.new('Threshold v2 player height source camera');D.lens=44
C=bpy.data.objects.new(D.name,D);S.collection.objects.link(C);S.camera=C
B=lambda p:Vector((p[0],-p[2],p[1]))
records=[]
for label,position,target in [('field-supply',(12.0,1.7,-5.8),(16,.25,-9)),('finery',(12.0,1.7,-14.8),(16,.25,-18))]:
 C.location=B(position);C.rotation_euler=(B(target)-C.location).to_track_quat('-Z','Y').to_euler()
 output=O/('stone-thresholds-v2-'+label+'-source.png');assert not output.exists();S.render.filepath=str(output)
 bpy.ops.render.render(write_still=True);records.append(dict(view=label,positionUnity=position,targetUnity=target,file=output.name))
bpy.data.libraries.write(str(O/'stone-thresholds-v2-source-review.blend'),{S},fake_user=True,compress=True)
(O/'stone-thresholds-v2-source-review.json').write_text(json.dumps(dict(sourceOnly=True,nativeAcceptance=False,renderer='Cycles',samples=24,resolution=[1280,900],material='Original sandstone4K albedo/normal and roughness, fixed metric UVs',renders=records),indent=2));print(json.dumps(records))
