"""Live Blender MCP: clear the Hall nameplate and conform the banner emblem."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/quality_20260909/vanguard-hall');out=O/'revision-02';assert not out.exists();out.mkdir()
scene=bpy.data.scenes['Ward Vanguard Hall repair'];bpy.context.window.scene=scene
B=lambda p:Vector((p[0],-p[2],p[1]))
U=lambda p:[round(p.x,6),round(p.z,6),round(-p.y,6)]
changes=[]
for ob in scene.objects:
 if ob.get('group')=='Readable hall name':ob.location+=B((0,0,.105));changes.append(ob.name)
 if ob.get('group')=='Attached red hall banner':
  ob.location+=B((0,0,.16));changes.append(ob.name)
  if 'Original twin stripe' in ob.name:
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=28,use_grid_fill=True)
   for v in bm.verts:
    x=v.co.x;y=v.co.z;z=-.378+.025*math.sin(x*3+y*1.7)+.014*math.sin(y*7)*math.cos(x*2)+.007
    v.co.y=-z
   bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
   # Newly tessellated applique uses the same physical textile scale as its backing.
   uv=ob.data.uv_layers.active
   for f in ob.data.polygons:
    for li in f.loop_indices:
     v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x/.4,v.z/.4)
  if 'Banner masonry mounting' in ob.name:
   # Extend the standoff back to its masonry rather than floating the bracket.
   for v in ob.data.vertices:v.co.y*=1.95
   ob.location+=B((0,0,-.08))
# Export actual authored objects; studio, source and the 1.8m guard are excluded.
data=[]
for ob in scene.objects:
 if ob.type!='MESH' or not ob.get('group') or not ob.get('region'):continue
 me=ob.data;me.calc_loop_triangles();vs=[];ns=[];uv=[];ii=[];unique={};nm=ob.matrix_world.to_3x3().inverted().transposed()
 for tri in me.loop_triangles:
  for li in tri.loops:
   p=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co);n=U((nm@me.corner_normals[li].vector).normalized());t=[round(float(v),6)for v in me.uv_layers.active.data[li].uv];key=tuple(p+n+t)
   if key not in unique:unique[key]=len(vs);vs.append(p);ns.append(n);uv.append(t)
   ii.append(unique[key])
 data.append(dict(name=ob.name,group=ob['group'],material=ob['region'],positions=vs,normals=ns,uv=uv,indices=ii))
(out/'hall-meshes.json').write_text(json.dumps(data,separators=(',',':')))
(out/'revision.json').write_text(json.dumps({'supersedes':'Initial source nameplate/banner intersections; original retained','changes':changes,'parts':len(data),'triangles':sum(len(p['indices'])//3 for p in data),'status':'Source revision; no native acceptance'},indent=2))
bpy.data.libraries.write(str(out/'hall-repaired.blend'),{scene},fake_user=True,compress=True)
views=[('front',(15,10,25),(0,6,-1),48),('door',(3.7,1.65,5.1),(0,1.7,-.1),43),('banner',(4.5,6.0,6.5),(0,5.05,-.2),48),('front-pedestrian',(0,1.75,29),(0,6.3,-1),42)]
(out/'review-cameras.json').write_text(json.dumps([dict(name=n,position=p,target=t,lens=l)for n,p,t,l in views],indent=2))
cam=scene.camera
for name,p,t,l in views:
 cam.location=B(p);cam.rotation_euler=(B(t)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=l;scene.render.filepath=str(out/('source-'+name+'.png'));bpy.ops.render.render(write_still=True)
print('Hall source v2 complete')
