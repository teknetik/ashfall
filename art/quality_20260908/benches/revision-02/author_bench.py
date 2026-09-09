"""Original Ward reclaimed-timber bench, authored through live Blender MCP."""
import bpy, math, json, random, ast
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/benches'
scene=bpy.data.scenes.get('Ward plaza bench')or bpy.data.scenes.new('Ward plaza bench');bpy.context.window.scene=scene
assert scene.get('ward_asset') in [None,'plaza-bench']
assert not scene.objects or scene.get('ward_asset')=='plaza-bench' or all(ob.name.startswith('Bench ') for ob in scene.objects)
scene['ward_asset']='plaza-bench'
for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
objects=[];rng=random.Random(908265);family='Bench';group='Structure';M={}
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,6),round(p.z,6),round(-p.y,6)]
for name in ['Wood','EndGrain','Paint','Steel','Bronze','Rubber']:
 mat=bpy.data.materials.get('WardBench_'+name)or bpy.data.materials.new('WardBench_'+name);mat.use_nodes=True
 # Recreate this task-owned material graph so repeat source auditions do not accumulate unused image nodes.
 mat.node_tree.nodes.clear();bs=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(bs.outputs['BSDF'],output.inputs['Surface'])
 for suffix in ['BaseColor','Normal','MetalSmooth']:
  tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'textures'/(name+'_'+suffix+'.png')),check_existing=True);tex.image.reload()
  if suffix!='BaseColor':tex.image.colorspace_settings.name='Non-Color'
  if suffix=='BaseColor':
   if name=='Wood':
    tint=mat.node_tree.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(1.03,.94,.79,1);mat.node_tree.links.new(tex.outputs['Color'],tint.inputs[1]);mat.node_tree.links.new(tint.outputs[0],bs.inputs['Base Color'])
   else:mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
  elif suffix=='Normal':
   normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.42 if name=='Wood'else .7;mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
  else:
   split=mat.node_tree.nodes.new('ShaderNodeSeparateColor');mat.node_tree.links.new(tex.outputs['Color'],split.inputs[0]);mat.node_tree.links.new(split.outputs['Red'],bs.inputs['Metallic'])
   inv=mat.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;mat.node_tree.links.new(tex.outputs['Alpha'],inv.inputs[1]);mat.node_tree.links.new(inv.outputs[0],bs.inputs['Roughness'])
 M[name]=mat
def finish(ob,name,mat,bevel=0):
 ob.name=family+' '+name;ob['family']=family;ob['group']=group;ob['region']=mat
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.type=='CURVE':bpy.ops.object.convert(target='MESH');ob=bpy.context.object
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=ob.modifiers.new('Rounded safe construction edge','BEVEL');mod.width=bevel;mod.segments=4;bpy.ops.object.modifier_apply(modifier=mod.name)
 me=ob.data;me.materials.clear();me.materials.append(M[mat]);uv=me.uv_layers.active or me.uv_layers.new(name='UV0 material metres');off=(rng.random(),rng.random()*4)
 for face in me.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]))
  for li in face.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   if mat=='Wood':
    # Two-metre scan grain runs U. Select an individual board interior, avoiding photographed gaps.
    rows=[.8931,.8252,.7578,.6904,.6226,.5542,.4346,.3667,.2988,.2339,.1670,.0991]
    row=rows[int(off[0]*len(rows))%len(rows)]
    uv.data[li].uv=(v.x/2+off[1],row+(v.y if axis==2 else v.z)*.30)
   elif mat=='EndGrain':uv.data[li].uv=((v.x if axis==1 else v.y)/.16+.5+off[0]*.7,v.z/.16+.5+off[1]*.25)
   else:uv.data[li].uv=((v.y if axis==0 else v.x)/.75+off[0],(v.y if axis==2 else v.z)/.75+off[1])
  face.use_smooth=True
 mod=ob.modifiers.new('Weighted construction normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name);objects.append(ob);return ob
# Reuse original primitive construction helpers only, without executing the lamp scene script.
source=ast.parse((R/'art/quality_20260908/lamps/author_lamps.py').read_text())
for node in source.body:
 if isinstance(node,ast.FunctionDef)and node.name in ['box','cylinder','tube','ring','bolt']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'original_lamp_construction_helpers','exec'))
def plank(name,p,size,angle=0):
 ob=box(name,p,size,'Wood',.008);ob.rotation_euler[0]=math.radians(angle)
 for x in [-size[0]/2-.0005,size[0]/2+.0005]:
  end=box(name+' cut end '+str(x),(p[0]+x,p[1],p[2]),(.001,size[1]-.010,size[2]-.014),'EndGrain',.0002);end.rotation_euler[0]=math.radians(angle)
 return ob
def bar(name,a,b,width=.036,depth=.04,mat='Paint'):
 d=B(b)-B(a);ob=box(name,tuple((Vector(a)+Vector(b))*.5),(width,d.length,depth),mat,.005)
 # Local Blender Z is Unity Y; align the solid bar with its actual endpoints.
 ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(d.normalized());return ob
def pan_bolt(name,p,axis=(0,1,0)):
 cylinder(name+' washer',p,.009,.0017,'Steel',axis,verts=32,bevel=.0004)
 cylinder(name+' rounded head',tuple(Vector(p)+Vector(axis)*.002),.0064,.003,'Steel',axis,verts=24,bevel=.001)
group='Bolted frame'
for x in [-.77,.77]:
 for z in [-.195,.195]:
  box('Ground shoe %.2f %.2f'%(x,z),(x,.008,z),(.115,.016,.10),'Steel',.004)
  for dx in [-.039,.039]:bolt('Ground anchor %.2f %.2f %.3f'%(x,z,dx),(x+dx,.018,z),.008)
  box('Shoe welded socket %.2f %.2f'%(x,z),(x,.021,z),(.049,.010,.052),'Steel',.003)
  bar('Leg %.2f %.2f'%(x,z),(x,.018,z),(x,.385,z*.83),.041,.047)
 # Seat bearer is a real top crossmember. Diagonal side stay prevents racking.
 box('Seat bearer '+str(x),(x,.397,0),(.056,.042,.484),'Paint',.005)
 box('Lower side rail '+str(x),(x,.155,0),(.045,.041,.390),'Paint',.005)
 bar('Side diagonal '+str(x),(x,.102,-.177),(x,.373,.173),.026,.030,'Steel')
 bar('Back upright '+str(x),(x,.354,-.190),(x,.939,-.335),.039,.044)
 for y,z in [(.405,-.207),(.902,-.326)]:bolt('Back frame fixing %.2f %.2f'%(x,y),(x,y,z),.012,(1 if x>0 else -1,0,0))
box('Lower structural tie',(0,.155,0),(1.58,.041,.041),'Paint',.005)
for x in [-.736,.736]:bolt('Tie fixing '+str(x),(x,.155,.0228),.011,(0,0,1))
group='Seat'
for j,z in enumerate([-.162,0,.162]):
 y=.430+(j-1)*.002
 plank('Seat slat '+str(j),(0,y,z),(2.08,.040,.15))
 for x in [-.77,.77]:
  for dz in [-.043,.043]:pan_bolt('Seat captive fixing %d %.2f %.2f'%(j,x,dz),(x,y+.020,z+dz))
group='Backrest'
for j,y in enumerate([.582,.725,.869]):
 z=-.213-(y-.43)*.247+.043
 plank('Back slat '+str(j),(0,y,z),(2.04,.118,.034),-13.88)
 for x in [-.77,.77]:
  for dy in [-.032,.032]:pan_bolt('Back captive fixing %d %.2f %.2f'%(j,x,dy),(x,y+dy,z+.021),(0,0,1))
group='Armrests'
for x in [-.948,.948]:
 for z in [.122,-.207]:bar('Arm load transfer %.2f %.2f'%(x,z),(.77 if x>0 else -.77,.397,z),(x,.397,z),.027,.034,'Steel')
 bar('Arm upright '+str(x),(x,.385,.122),(x,.635,.122),.027,.034)
 bar('Arm rear bracket '+str(x),(x,.397,-.207),(x,.635,-.155),.027,.034)
 arm=box('Rounded timber arm '+str(x),(x,.665,-.008),(.077,.047,.404),'Wood',.012)
 # Arm grain follows its long depth axis; explicit metric UV correction.
 for f in arm.data.polygons:
  axis=max(range(3),key=lambda i:abs(f.normal[i]))
  for li in f.loop_indices:
   v=arm.data.vertices[arm.data.loops[li].vertex_index].co;arm.data.uv_layers.active.data[li].uv=((v.z if axis==1 else -v.y)/2+1.12,.5542+(v.z if axis==0 else v.x)*.30)
 for z in [-.2105,.1945]:box('Arm cut end %.2f %.2f'%(x,z),(x,.665,z),(.063,.037,.001),'EndGrain',.0002)
 for z in [-.15,.12]:pan_bolt('Arm flush fixing %.2f %.2f'%(x,z),(x,.690,z))
group='Repairs'
# One replaced slat is reinforced on its underside with an authentic bolted splice strap.
box('Salvaged underside splice',(0,.403,.162),(.28,.008,.115),'Steel',.004)
for x in [-.103,.103]:
 for z in [.13,.19]:pan_bolt('Splice fastener %.2f %.2f'%(x,z),(x,.452,z))
data=[]
for ob in objects:
 me=ob.data;me.calc_loop_triangles();v=[];n=[];uv=[];ii=[];unique={}
 for tri in me.loop_triangles:
  for li in tri.loops:
   p=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co);nn=U(ob.matrix_world.to_3x3()@me.corner_normals[li].vector);t=[round(float(q),6)for q in me.uv_layers.active.data[li].uv];key=tuple(p+nn+t)
   if key not in unique:unique[key]=len(v);v.append(p);n.append(nn);uv.append(t)
   ii.append(unique[key])
 data.append(dict(name=ob.name,group=ob['group'],material=ob['region'],positions=v,normals=n,uv=uv,indices=ii))
(O/'bench-meshes.json').write_text(json.dumps(data,separators=(',',':')))
vs=[v for p in data for v in p['positions']];summary=dict(parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),vertices=sum(len(p['positions'])for p in data),bounds=dict(min=[min(p[a]for p in vs)for a in range(3)],max=[max(p[a]for p in vs)for a in range(3)]),seatTop=.450,seatDepth=.474,seatLength=2.08,source='Original live Blender MCP construction with CC0 Wooden Planks by Charlotte Baglioni and Dario Barresi')
(O/'geometry-report.json').write_text(json.dumps(summary,indent=2))
# Independent source-studio scene, preserving all other live Blender documents.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.name='Bench preview floor';floor.data.materials.append(M['Paint'])
world=bpy.data.worlds.get('Bench studio')or bpy.data.worlds.new('Bench studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.17,.21,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,p,power,size in [('Bench key',(1,4,3),1000,4),('Bench fill',(-3,2,-2),600,3)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size;ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=B(p);ob.rotation_euler=(B((0,.4,0))-ob.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Bench source camera');cam=bpy.data.objects.new('Bench source camera',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.lens=57
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
for name,p,target in [('front',(2.65,1.5,3.1),(0,.47,0)),('rear',(-2.3,1.3,-2.8),(0,.49,-.1)),('joint',(1.68,.83,1.05),(.65,.44,.04))]:
 cam.location=B(p);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/('studio-'+name+'.png'))
 if name=='front':bpy.data.libraries.write(str(O/'bench-family.blend'),{scene},fake_user=True,compress=True)
 bpy.ops.render.render(write_still=True)
print(json.dumps(summary))
