"""Live Blender MCP: preserve v2, export its actual assigned materials and complete side views."""
import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260909/basic-general'
scene=bpy.data.scenes['Basic General architectural repair'];bpy.context.window.scene=scene
assert scene.get('basic_general_v2_complete')
assert not (O/'basic-general-meshes-v3.json').exists(),'Preserve the reviewed export.'
B=lambda p:Vector((p[0],-p[2],p[1]))
U=lambda p:[round(p.x,7),round(p.z,7),round(-p.y,7)]
parts=[o for o in scene.objects if o.type=='MESH' and o.get('group') not in [None,'Context']]
corrections=[]
for o in parts:
 slot=o.data.materials[0].get('ward_slot')
 if slot and slot!=o.get('material_slot'):
  corrections.append({'part':o.name,'before':o.get('material_slot'),'after':slot});o['material_slot']=slot
source=O/'basic-general-source-v3.blend'
bpy.data.libraries.write(str(source),{scene},fake_user=True,compress=True)
materials=json.loads((O/'material-bindings-v2.json').read_text())
code=(O/'author_basic_general.py').read_text().split('# Explicit Unity mesh interchange',1)[1]
code='# Explicit Unity mesh interchange'+code
code=code.replace('v1.json','v3.json')
exec(compile(code,'export reviewed Basic General v3','exec'))
(O/'revision-v3.json').write_text(json.dumps({'supersedes':'v2 mesh interchange only; same construction and geometry','corrections':corrections,'source':str(source)},indent=2))
cam=scene.camera
for name,pos,target,lens in [('left-full',(-10,1.85,0),(0,1.45,0),40),('right-full',(10,1.85,0),(0,1.45,0),40)]:
 cam.location=B(pos);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=lens
 scene.render.filepath=str(O/('source-v3-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps({'actualMaterialCorrections':corrections,'parts':len(parts)}))
