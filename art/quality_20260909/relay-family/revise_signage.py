"""Live Blender MCP revision: fit the actual converted lettering bounds to the sign panels."""
import bpy,json,shutil
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family');old=O/'revision-01';out=O/'revision-02'
assert not out.exists(),'Preserve existing revision.'
scene=bpy.data.scenes['Ward Relay architecture'];bpy.context.window.scene=scene
out.mkdir();changes=[]
for name,width,height in [('relay_works Trade name',4.95,.29),('relay_works Service label lettering',1.06,.095)]:
 o=scene.objects[name];bpy.context.view_layer.update()
 points=[o.matrix_world@Vector(p) for p in o.bound_box]
 size=[max(p[a]for p in points)-min(p[a]for p in points)for a in range(3)]
 scale=min(width/size[0],height/size[2]);o.scale*=scale
 bpy.context.view_layer.update();changes.append({'name':name,'beforeWorldSize':size,'uniformCorrection':scale,'targetWidthHeight':[width,height]})
data=[]
U=lambda p:[round(p.x,6),round(p.z,6),round(-p.y,6)]
for ob in scene.objects:
 if ob.type!='MESH' or ob.get('family')!='relay_works':continue
 me=ob.data;me.calc_loop_triangles();vs=[];ns=[];uv=[];ii=[];unique={};normalmat=ob.matrix_world.to_3x3().inverted().transposed();uvl=me.uv_layers.active.data
 for tri in me.loop_triangles:
  for li in tri.loops:
   p=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co);n=U((normalmat@me.corner_normals[li].vector).normalized());t=[round(float(v),6)for v in uvl[li].uv];key=tuple(p+n+t)
   if key not in unique:unique[key]=len(vs);vs.append(p);ns.append(n);uv.append(t)
   ii.append(unique[key])
 data.append(dict(name=ob.name,family=ob['family'],group=ob['group'],material=ob['region'],positions=vs,normals=ns,uv=uv,indices=ii))
(out/'relay-meshes.json').write_text(json.dumps(data,separators=(',',':')))
for name in ['collider-proxies.json','review-cameras.json']:shutil.copy2(old/name,out/name)
shutil.copytree(old/'textures',out/'textures')
(out/'revision.json').write_text(json.dumps({'supersedes':'revision-01 signage fit; all construction retained','changes':changes,'parts':len(data),'triangles':sum(len(p['indices'])//3 for p in data),'status':'Source review; not native acceptance'},indent=2))
bpy.data.libraries.write(str(out/'relay-architecture.blend'),{scene},fake_user=True,compress=True)
B=lambda p:Vector((p[0],-p[2],p[1]));cam=scene.camera
for row in json.loads((out/'review-cameras.json').read_text()):
 cam.location=B(row['position']);cam.rotation_euler=(B(row['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=row['lens'];scene.render.filepath=str(out/('source-'+row['name']+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(changes))
