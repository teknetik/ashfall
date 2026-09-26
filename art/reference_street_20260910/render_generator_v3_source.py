"""Render one immutable source-review view in exclusive live Blender.
Set GENERATOR_V3_VIEW and optional GENERATOR_V3_TAG. Normal diagnostics change
only the retained core's object material slot, then restore it in finally.
"""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source'
sys.path.insert(0,str(R/'art/reference_street_20260910'))
from generator_v2_review_common import memory_record
S=bpy.data.scenes['Generator v3 side service authoring'];bpy.context.window.scene=S
V=globals().get('GENERATOR_V3_VIEW','front_oblique');TAG=globals().get('GENERATOR_V3_TAG','service-v1')
views={
 'front_oblique':((2.5,-3.4,1.8),(.10,0,.53),'PERSP',64),
 'rear_oblique':((2.5,3.4,1.7),(.10,0,.53),'PERSP',64),
 'right':((4,0,.66),(.68,0,.53),'ORTHO',1.55),
 'front':((.14,-4,.63),(.14,0,.55),'ORTHO',1.92),
 'connection_close':((1.85,-1.6,1.04),(.68,-.05,.54),'PERSP',76),
 'tank_close':((1.85,-1.5,1.42),(.76,-.07,.81),'PERSP',83),
 'grille_close':((.12,-1.4,.76),(0,-.24,.60),'PERSP',70),
}
assert V in views
out=O/'renders';out.mkdir(exist_ok=True);path=out/(V+'-'+TAG+'.png');assert not path.exists()
cam=S.camera
# Retain source review's camera datablock unchanged as well as its transform.
if cam.data.users>1:cam.data=cam.data.copy()
p,t,k,f=views[V];cam.location=p;cam.rotation_euler=(Vector(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type=k
if k=='ORTHO':cam.data.ortho_scale=f
else:cam.data.lens=f
cam.data.clip_start=.01;cam.data.clip_end=100;cam.data.dof.use_dof=False
core=bpy.data.objects['GENERATOR_V3_RETAINED_CORE'];slot=core.material_slots[0];savedlink=slot.link;savedmat=slot.material;tmp=None
normalOff=bool(globals().get('GENERATOR_V3_NORMAL_DIAGNOSTIC_OFF',False))
diagnostic=globals().get('GENERATOR_V3_MATERIAL_DIAGNOSTIC','')
assert diagnostic in ('','albedo-emission','flat-clay')
assert not normalOff or V=='grille_close','Diagnostic bounded to the requested matched grille close-up'
assert not diagnostic or V=='grille_close','Material diagnostic is bounded to the grille close-up'
try:
 if normalOff or diagnostic:
  tmp=savedmat.copy();tmp.name='Diagnostic only normal disabled'
  pbr=tmp.node_tree.nodes.get('Principled BSDF')
  for link in list(pbr.inputs['Normal'].links):tmp.node_tree.links.remove(link)
  if diagnostic=='albedo-emission':
   nodes=tmp.node_tree.nodes;links=tmp.node_tree.links
   source=pbr.inputs['Base Color'].links[0].from_socket
   emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
   links.new(source,emission.inputs['Color']);links.new(emission.outputs[0],nodes.get('Material Output').inputs['Surface'])
  elif diagnostic=='flat-clay':
   for name in ['Base Color','Metallic','Roughness']:
    for link in list(pbr.inputs[name].links):tmp.node_tree.links.remove(link)
   pbr.inputs['Base Color'].default_value=(.18,.18,.18,1);pbr.inputs['Metallic'].default_value=0;pbr.inputs['Roughness'].default_value=.62
  slot.link='OBJECT';slot.material=tmp
 S.render.filepath=str(path);bpy.ops.render.render(write_still=True)
finally:
 if tmp:
  slot.material=savedmat;slot.link=savedlink;bpy.data.materials.remove(tmp)
record={'image':str(path),'view':V,'tag':TAG,'sourceOnly':True,'sourceCoreTriangles':1927842,'coreNormalDiagnosticOff':normalOff,'originalCoreMaterialRestored':slot.material==savedmat,'position':list(cam.location),'target':t,'cameraType':k,'framing':f,'settings':{'samples':S.cycles.samples,'device':S.cycles.device,'resolution':[S.render.resolution_x,S.render.resolution_y],'exposure':S.view_settings.exposure,'viewTransform':S.view_settings.view_transform},'memory':memory_record(),'nativeAcceptance':False}
record['materialDiagnostic']=diagnostic
path.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
