"""Author the saved Relay/Air + Water surfaces through the live Blender MCP.
All dimensions are metres. Source row transforms are already in Unity world space.
"""
import bpy,bmesh,ast,json,math,random
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/relay_airwater_surfaces_20260909'
assert not (O/'relay-airwater-surfaces-v1.blend').exists(),'Preserve previous authoring'
rows=json.loads((O/'unity-source.json').read_text());rng=random.Random(909612)
scene=bpy.data.scenes.new('Relay and Air + Water surface revision');scene.unit_settings.system='METRIC';bpy.context.window.scene=scene
for node in ast.parse((R/'art/facade_materials_20260909/refine_facade_geometry.py').read_text()).body:
 if isinstance(node,ast.FunctionDef)and node.name in ['B','U','outline','prism','bevel','planar_uv','export']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'reviewed facade geometry helper','exec'))
def texture(mat,path,socket,normal=False,linear=False):
 if not path or not Path(path).exists():return
 nt=mat.node_tree;bs=nt.nodes.get('Principled BSDF');t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path),check_existing=True)
 if normal or linear:t.image.colorspace_settings.name='Non-Color'
 if normal:
  n=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(t.outputs['Color'],n.inputs['Color']);nt.links.new(n.outputs['Normal'],bs.inputs['Normal'])
 else:nt.links.new(t.outputs['Color'],bs.inputs[socket])
M={}
for family in ['Plaster','Stone','Steel']:
 m=bpy.data.materials.new('Baked facade '+family);m.use_nodes=True;M[family]=m
 p=R/'art/facade_materials_20260909/textures'/family
 texture(m,p/'BaseColor.png','Base Color');texture(m,p/'Normal.png','Normal',True);texture(m,p/'Roughness.png','Roughness',linear=True);texture(m,p/'Metallic.png','Metallic',linear=True)
references={}
def original_material(row):
 info=row['materials'][0];key=info['path']
 if key not in references:
  m=bpy.data.materials.new('Retained '+info['name']);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*info['color'],1);bs.inputs['Roughness'].default_value=.78
  if info['baseMap']:texture(m,R/'unity/AthenHill'/info['baseMap'],'Base Color')
  references[key]=m
 return references[key]
def material_for(row):
 name=row['materials'][0]['name'];n=row['name'].lower()
 if name=='WardPlaster':return 'Plaster'
 if name=='WardStone':return 'Stone'
 # Coated hardware is aged selectively; lettering, brass, rubber and bare steel retain their materials.
 if name=='WardPaint'and not any(s in n for s in ['sign','label','lamp','canvas pocket']):return 'Steel'
 if name=='WardSteel'and 'filter canister'in n:return 'Steel'
 return None
targets={};refs={};changed=[];damage_record=[];added=[]
for row in rows:
 me=bpy.data.meshes.new(row['name']);ii=row['indices'];me.from_pydata([B(v)for v in row['positions']],[],[ii[i:i+3]for i in range(0,len(ii),3)]);me.update()
 for f in me.polygons:f.use_smooth=True
 me.normals_split_custom_set_from_vertices([B(v)for v in row['normals']])
 ob=bpy.data.objects.new(row['name'],me);scene.collection.objects.link(ob);ob['export_name']=row['name'];ob['source_path']=row['path'];ob['family']=row['family'];refs[row['path']]=ob
 uv=me.uv_layers.new(name='UV0 original')
 for lp in me.loops:uv.data[lp.index].uv=row['uv'][lp.vertex_index]if row['uv']else(0,0)
 key=material_for(row)
 if key:me.materials.append(M[key]);ob['material_key']=key;targets[row['path']]=ob
 else:me.materials.append(original_material(row));ob['reference_only']=True
byname={r['name']:r for r in rows}
def prepare_boolean(ob):
 if ob in changed:return
 me=ob.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();changed.append(ob)
def damage(name,center,w,h,n=(1,0,0),u=(0,0,1)):
 row=byname[name];ob=refs[row['path']];prepare_boolean(ob);poly=outline(w,h)
 cut=prism('Temporary spall cutter',center,u,n,poly,.12,-.043);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Localized aged plaster loss','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 sub=prism(row['family']+' Exposed aggregate '+str(len(added)),center,u,n,[(x*.995,y*.995)for x,y in poly],-.0425,-.047);bevel(sub,.0006);sub.data.materials.append(M['Stone'])
 sub['material_key']='Stone';sub['family']=row['family'];sub['export_name']=sub.name;added.append(sub);targets['added/'+sub.name]=sub
 damage_record.append(dict(sourcePath=row['path'],center=center,width=w,height=h,normal=n))

# Damage follows construction joints, sill drainage and service access, with quiet areas between.
damage('relay_works Ground front structure -1',(-17.88,.77,-21.00),.88,.37)
damage('relay_works Ground front structure 1',(-17.88,3.21,-15.65),.69,.29)
damage('relay_works Upper front pier 0',(-17.89,5.62,-18.78),.61,.93)
damage('relay_works Window sill wall 2.15',(-17.89,4.19,-15.75),.73,.27)
damage('relay_works Side masonry wall -1',(-22.6,.87,-21.75),1.30,.54,(0,0,-1),(1,0,0))
damage('relay_works Side masonry wall -1',(-19.05,2.72,-21.75),.56,.67,(0,0,-1),(1,0,0))
damage('relay_works Side masonry wall 1',(-21.86,1.07,-14.25),1.40,.49,(0,0,1),(1,0,0))
damage('relay_works Interior back wall',(-25.04,1.2,-17.35),.96,.69,(-1,0,0),(0,0,-1))
damage('air_water Front masonry segment 3 0',(-17.87,.73,-7.33),1.15,.35)
damage('air_water Front masonry segment 3 1',(-17.87,3.14,-8.08),.79,.52)
damage('air_water Front masonry segment 0 0',(-17.87,1.20,-12.17),.42,.62)
damage('air_water Front masonry segment 3 3',(-17.87,6.46,-7.02),.76,.34)
damage('air_water Full wall return 3.66',(-21.21,.88,-5.2),1.45,.52,(0,0,1),(1,0,0))
damage('air_water Full wall return 3.66',(-18.92,3.07,-5.2),.57,.82,(0,0,1),(1,0,0))
damage('air_water Full wall return -3.66',(-22.64,1.08,-12.8),1.17,.55,(0,0,-1),(1,0,0))
damage('air_water Rear masonry segment 0 0',(-24.97,.91,-8.24),1.20,.47,(-1,0,0),(0,0,-1))
for ob in changed:bevel(ob,.0025)
stone_chips=[]
for family in ['relay_works','air_water']:
 candidates=[r for r in rows if r['family']==family and r['materials'][0]['name']=='WardStone'and r['bounds']['max'][0]>-18.0 and .55<r['bounds']['min'][1]<3.8 and min(r['bounds']['max'][k]-r['bounds']['min'][k]for k in range(3))>.12]
 for i,row in enumerate(candidates):
  if i%4!=1:continue
  lo=row['bounds']['min'];hi=row['bounds']['max'];c=(hi[0]-.015,lo[1]+.022,lo[2]+.02);ob=refs[row['path']];prepare_boolean(ob)
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3,radius=1,location=B(c));cut=bpy.context.object
  for v in cut.data.vertices:
   x,y,z=v.co;v.co*=1+.11*math.sin(5*x+3*z)+.065*math.sin(9*y-2*x)
  cut.scale=(rng.uniform(.055,.09),rng.uniform(.05,.11),rng.uniform(.04,.085));bpy.context.view_layer.objects.active=ob
  mod=ob.modifiers.new('Natural stone edge loss','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True);bevel(ob,.002);stone_chips.append(row['path'])
for ob in changed:
 me=ob.data;me.normals_split_custom_set([(0,0,0)]*len(me.loops))
 for f in me.polygons:f.use_smooth=max(abs(v)for v in f.normal)<.999
 me.update()
for ob in targets.values():
 planar_uv(ob)
 # Cylindrical service surfaces need a continuous wrap instead of planar seams.
 if any(k in ob.name for k in ['Filter canister','Riveted water vessel']):
  me=ob.data;verts=[U(v.co)for v in me.vertices];cx=(min(v[0]for v in verts)+max(v[0]for v in verts))/2;cz=(min(v[2]for v in verts)+max(v[2]for v in verts))/2;radius=(max(v[0]for v in verts)-min(v[0]for v in verts))/2
  for f in me.polygons:
   if abs(U(f.normal)[1])>.8:continue
   values=[]
   for li in f.loop_indices:
    x,y,z=U(me.vertices[me.loops[li].vertex_index].co);values.append((li,math.atan2(z-cz,x-cx)/math.tau,y))
   crosses=max(v[1]for v in values)-min(v[1]for v in values)>.5
   for li,a,y in values:me.uv_layers.active.data[li].uv=((a+(1 if crosses and a<0 else 0))*math.tau*radius/4,y/4)
out=[]
for path,ob in targets.items():
 part=export(path,ob)
 if path.startswith('added/'):part['sourcePath']=None
 out.append(part)
(O/'facade-meshes-v1.json').write_text(json.dumps(out,separators=(',',':')))
(O/'geometry-manifest-v1.json').write_text(json.dumps(dict(parts=len(out),replacements=len(out)-len(added),additions=len(added),triangles=sum(len(p['indices'])//3 for p in out),tileMetres=4,spalls=damage_record,stoneChips=stone_chips,source='relay-airwater-surfaces-v1.blend',texturesReused='art/facade_materials_20260909/textures',disabledPaths=[]),indent=2))
# Renderable source inspection; final acceptance is always the native game.
world=bpy.data.worlds.new('Surface review sky');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.44,.52,1);world.node_tree.nodes['Background'].inputs[1].default_value=.7;scene.world=world
sun=bpy.data.lights.new('Review sun','SUN');sun.energy=3;sun.angle=.06;light=bpy.data.objects.new('Review sun',sun);scene.collection.objects.link(light);light.rotation_euler=(.4,-.5,-.6)
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.device='GPU';prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='CUDA'
camera=bpy.data.cameras.new('Source camera');cam=bpy.data.objects.new('Source camera',camera);scene.collection.objects.link(cam);scene.camera=cam;camera.lens=45
scene.render.resolution_x=1400;scene.render.resolution_y=1050;scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(O/'relay-airwater-surfaces-v1.blend'))
for family,z in [('relay_works',-18),('air_water',-9)]:
 cam.location=B((-10.2,3.5,z+.35));target=B((-18.0,3.2,z));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/(family+'-source-front.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(dict(parts=len(out),additions=len(added),stoneChips=len(stone_chips),triangles=sum(len(p['indices'])//3 for p in out))))
