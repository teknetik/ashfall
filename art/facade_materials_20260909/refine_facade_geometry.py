"""Refine the accepted weathering source, preserving the prior scene and assets."""
import bpy,bmesh,ast,json,math,random
from mathutils import Vector
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'art/facade_materials_20260909';P=R/'art/building_weathering_20260909'
assert not (O/'facade-surfaces-v1.blend').exists(),'Keep prior sources'
rows=json.loads((P/'unity-source.json').read_text());byname={r['name']:r for r in rows};by_path={r['path']:r for r in rows}
old=bpy.data.scenes['Ward Field Supply and Finery weathering v3-base'];scene=bpy.data.scenes.new('Refined facade surfaces v1');scene.unit_settings.system='METRIC';bpy.context.window.scene=scene
copies={}
for ob in old.objects:
 new=ob.copy()
 if ob.data:new.data=ob.data.copy()
 new['export_name']=ob.name;scene.collection.objects.link(new);copies[ob.name]=new
scene.world=old.world;scene.camera=copies[old.camera.name];scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=16
refs={o['source_path']:o for o in copies.values()if 'source_path'in o};rng=random.Random(909331)
M={family:bpy.data.materials['Facade layered '+family]for family in ['Plaster','Stone','Steel']}
def B(v):return Vector((v[0],-v[2],v[1]))
def U(v):return [round(v.x,6),round(v.z,6),round(-v.y,6)]
def family_for(row):
 name=row['materials'][0]['name']
 if name in ['WardPlaster','Finery mineral plaster']:return 'Plaster'
 if name in ['WardStone','Finery cut stone']:return 'Stone'
 if 'Rolled shutter slat'in row['name']or name.startswith('Finery shutter '):return 'Steel'
 return None
targets={};disabled=[];substrates=[]
for row in rows:
 family=family_for(row)
 if not family:continue
 ob=refs[row['path']];me=bpy.data.meshes.new(row['name']+' refined');ii=row['indices'];me.from_pydata([B(v)for v in row['positions']],[],[ii[i:i+3]for i in range(0,len(ii),3)]);me.update()
 # Retain the original construction and its smooth bevel normals.
 for face in me.polygons:face.use_smooth=True
 me.normals_split_custom_set_from_vertices([B(v)for v in row['normals']])
 ob.data=me;me.materials.append(M[family]);ob['material_key']=family;ob['reference_only']=False;targets[row['path']]=ob
for name,ob in copies.items():
 if name.startswith(('Clinging plaster flake','Hairline fracture','Fracture branch','Side wall fracture','Shutter flaked coating')):
  ob.hide_render=True;disabled.append('Field Supply and Finery weathering/'+ob.get('family','field_supply')+'/'+name)
 if ' exposed substrate 'in name:ob.hide_render=True

def outline(w,h):
 phase=[rng.uniform(0,math.tau)for _ in range(5)];poly=[]
 for i in range(128):
  a=math.tau*i/128;r=1+.14*math.sin(3*a+phase[0])+.075*math.sin(7*a+phase[1])+.035*math.sin(17*a+phase[2])+.014*math.sin(37*a+phase[3])
  poly.append((math.cos(a)*w*.5*r,math.sin(a)*h*.5*r))
 return poly
def prism(name,center,u,n,poly,front,back):
 c=Vector(center);u=Vector(u);n=Vector(n);count=len(poly)
 vertices=[B(c+u*x+Vector((0,y,0))+n*d)for d in [front,back]for x,y in poly]
 faces=[tuple(range(count)),tuple(range(count,count*2))]+[(i,(i+1)%count,(i+1)%count+count,i+count)for i in range(count)]
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);return ob
def bevel(ob,width):
 bpy.context.view_layer.objects.active=ob;mod=ob.modifiers.new('Small worn fracture bevel','BEVEL');mod.width=width;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.65
 bpy.ops.object.modifier_apply(modifier=mod.name)
def damage(name,center,w,h,n=(-1,0,0),u=(0,0,-1)):
 row=byname[name];ob=refs[row['path']];poly=outline(w,h)
 cut=prism('Temporary organic damage cutter',center,u,n,poly,.12,-.045);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Irregular missing plaster','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 # Retain the existing substrate object identity and placement while replacing its shape.
 candidates=[(key,o)for key,o in copies.items()if key.startswith(name+' exposed substrate ')and o.get('revision_replaced')is not True]
 assert candidates,name
 key,prior=min(candidates,key=lambda kv:(sum((kv[1].data.vertices[0].co[k]-B(center)[k])**2 for k in range(3))))
 prior['revision_replaced']=True
 sub=prism('Refined substrate '+str(len(substrates)),center,u,n,[(x*.995,y*.995)for x,y in poly],-.0445,-.049);bevel(sub,.0006);sub.data.materials.append(M['Stone']);sub['material_key']='Stone';sub['family']=row['family'];sub['export_name']=key
 sub['source_path']='Field Supply and Finery weathering/'+row['family']+'/'+key;targets[sub['source_path']]=sub;substrates.append(sub)

# Replay the accepted locations and sizes, with more natural outlines and no polygon flakes.
for node in ast.parse((P/'author_weathering_v3.py').read_text()).body:
 if isinstance(node,ast.For)and any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='damage'for n in ast.walk(node)):
  exec(compile(ast.Module(body=[node],type_ignores=[]),'accepted damage placements','exec'))
for node in ast.parse((P/'refine_weathering_v3.py').read_text()).body:
 if isinstance(node,ast.Expr)and isinstance(node.value,ast.Call)and isinstance(node.value.func,ast.Name)and node.value.func.id=='damage':
  exec(compile(ast.Module(body=[node],type_ignores=[]),'accepted extended spalls','exec'))
for path,ob in targets.items():
 if ob.get('material_key')=='Plaster':bevel(ob,.0025)

stone_rows=[r for r in rows if r['materials'][0]['name']in ['WardStone','Finery cut stone']and r['bounds']['min'][0]<18.25 and r['bounds']['min'][1]<4]
stone_chips=[]
for i,row in enumerate(stone_rows):
 if i%5!=2:continue
 lo=row['bounds']['min'];hi=row['bounds']['max']
 if min(hi[k]-lo[k]for k in range(3))<.1:continue
 ob=refs[row['path']];c=(lo[0]+.025,lo[1]+.025,lo[2]+.02)
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=B(c));cut=bpy.context.object
 for v in cut.data.vertices:
  x,y,z=v.co;v.co*=1+.11*math.sin(5*x+3*z)+.065*math.sin(9*y-2*x)
 cut.scale=(rng.uniform(.065,.12),rng.uniform(.07,.14),rng.uniform(.05,.10));bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Eroded fractured stone corner','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True);bevel(ob,.002);stone_chips.append(row['path'])

def planar_uv(ob):
 me=ob.data;uv=me.uv_layers.new(name='UV0 four metre world scale')if not me.uv_layers else me.uv_layers.active
 for face in me.polygons:
  nx,ny,nz=U(face.normal);axis=max(range(3),key=lambda k:abs([nx,ny,nz][k]))
  for li in face.loop_indices:
   x,y,z=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co)
   a,b=((z if nx<0 else-z),y)if axis==0 else((x,-z if ny>0 else z)if axis==1 else((x if nz>0 else-x),y))
   uv.data[li].uv=(a/4,b/4)
for ob in targets.values():planar_uv(ob)

def export(path,ob):
 deps=bpy.context.evaluated_depsgraph_get();ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();uv=me.uv_layers.active;positions=[];normals=[];coords=[];indices=[]
 for tri in me.loop_triangles:
  start=len(positions)
  for li in tri.loops:
   positions.append(U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co));normals.append(U(me.corner_normals[li].vector));coords.append(list(uv.data[li].uv))
  indices.extend([start,start+1,start+2])
 ev.to_mesh_clear()
 return dict(name=ob['export_name'],sourcePath=path,family=ob.get('family'),material=ob['material_key'],positions=positions,normals=normals,uv=coords,indices=indices)
out=[export(path,ob)for path,ob in targets.items()]
(O/'facade-meshes-v1.json').write_text(json.dumps(out,separators=(',',':')))
(O/'geometry-manifest-v1.json').write_text(json.dumps(dict(blender=bpy.app.version_string,source='facade-surfaces-v1.blend',parts=len(out),triangles=sum(len(p['indices'])//3 for p in out),disabledPaths=disabled,stoneChips=stone_chips,substrates=len(substrates),tileMetres=4,notes=['Same building envelopes and accepted spall locations','128 point irregular spall outlines and small physical edge bevels','Detailed asymmetric stone cutters replace icosahedral notches','Fine cracks, pores and coating loss baked into normal and colour maps','Original paper, lettering, blood and localized drainage retained']),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'facade-surfaces-v1.blend'))
print(json.dumps({'parts':len(out),'triangles':sum(len(p['indices'])//3 for p in out),'disabledGeometricOverlays':len(disabled),'substrates':len(substrates),'stoneChips':len(stone_chips)}))
