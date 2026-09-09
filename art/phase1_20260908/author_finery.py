"""Finery frontage, original Blender authoring through live Blender MCP.
Matches the accepted courtyard, within the existing parcel. No runtime assembly.
"""
import bpy,math,json,random
from pathlib import Path
from mathutils import Vector,noise
ROOT=Path('/home/teknetik/code/ao2');OUT=ROOT/'art/phase1_20260908'
assert Path(bpy.data.filepath).name in ['tree-root-repaired.blend','finery-frontage.blend','']
# Previous tree work is saved on disk; this is a separate authoring document.
scene=bpy.data.scenes.get('Finery frontage') or bpy.data.scenes.new('Finery frontage')
bpy.context.window.scene=scene
for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
rng=random.Random(908102)
M={}
for name,col in {'Stone0':(.54,.43,.30),'Stone1':(.62,.51,.37),'Stone2':(.46,.38,.29),'Stone3':(.58,.49,.38),'Mortar':(.34,.29,.22),'Iron':(.12,.095,.075),'Brass':(.35,.23,.12),'Drum':(.34,.24,.15)}.items():
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=(*col,1);M[name]=m
parts=[]
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,6),round(p.z,6),round(-p.y,6)]
def uv(o,scale=.65):
 me=o.data;layer=me.uv_layers.active or me.uv_layers.new(name='UV0 material metres');off=(rng.random()*4,rng.random()*4)
 for face in me.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]))
  for i in face.loop_indices:
   v=me.vertices[me.loops[i].vertex_index].co
   layer.data[i].uv=((v.y if axis==0 else v.x)*scale+off[0],(v.y if axis==2 else v.z)*scale+off[1])
def box(name,c,size,mat='Stone1',group='Structure',bevel=.018):
 bpy.ops.mesh.primitive_cube_add(size=1,location=B(c));o=bpy.context.view_layer.objects.active;o.name=name;o['group']=group
 o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=o.modifiers.new('Construction edge bevel','BEVEL');mod.width=min(bevel,min(size)*.19);mod.segments=3
  bpy.ops.object.modifier_apply(modifier=mod.name)
 o.data.materials.append(M[mat]);uv(o,.65 if mat.startswith('Stone') else 1.0)
 for f in o.data.polygons:f.use_smooth=True
 mod=o.modifiers.new('Weighted construction normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 bpy.ops.object.modifier_apply(modifier=mod.name);parts.append(o);return o
def tube(name,points,radius=.03,mat='Iron',group='Hardware'):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2;curve.bevel_depth=radius;curve.bevel_resolution=3
 sp=curve.splines.new('POLY');sp.points.add(len(points)-1)
 for p,co in zip(sp.points,points):p.co=(*B(co),1)
 o=bpy.data.objects.new(name,curve);scene.collection.objects.link(o);o['group']=group;o.data.materials.append(M[mat]);bpy.context.view_layer.objects.active=o;o.select_set(True)
 bpy.ops.object.convert(target='MESH');uv(o,1);parts.append(o);return o
# Side and back masonry: structural thickness, separate quoin courses and copings.
box('South wall core',(20.9,3.65,-21.56),(8.2,6.3,.48),'Stone0')
box('North wall core',(20.9,3.65,-14.44),(8.2,6.3,.48),'Stone1')
box('Rear wall core',(24.76,3.65,-18),(.48,6.3,6.64),'Stone2')
box('Upper floor soffit',(20.9,3.84,-18),(7.3,.30,6.64),'Stone2')
# Front has true openings, reveals and inset closed doors/windows, rather than painted holes.
# Horizontal wall bands separate ground-floor apertures, sign fascia and upper glazing.
for i,(a,b) in enumerate([(-21.8,-18.91),(-17.09,-14.2)]):box('Front foundation band '+str(i),(17.03,.78,(a+b)/2),(.46,.56,b-a),'Stone2')
box('Front lower lintel course',(17.03,3.42,-18),(.46,1.04,7.6),'Stone0')
box('Sign fascia',(17.03,4.50,-18),(.46,.96,7.6),'Stone1')
box('Upper sill course',(17.03,5.13,-18),(.46,.30,7.6),'Stone2')
box('Upper header course',(17.03,6.83,-18),(.46,.40,7.6),'Stone0')
# Apertures in lower wall: door width 1.82m, two recessed shutter windows.
segments=[(-21.8,-21.36),(-19.92,-18.91),(-17.09,-16.08),(-14.64,-14.2)]
for i,(a,b) in enumerate(segments):box('Lower wall pier '+str(i),(17.03,1.985,(a+b)/2),(.46,1.83,b-a),'Stone1')
for i,z in enumerate([-20.64,-15.36]):
 box('Window below sill '+str(i),(17.03,1.255,z),(.46,.39,1.44),'Stone2')
 box('Window upper infill '+str(i),(17.03,2.855,z),(.46,.09,1.44),'Stone1')
# Stone jamb blocks articulate construction; restrained worn edges.
for j,z in enumerate([-21.59,-19.71,-18.91,-17.09,-16.29,-14.41]):
 for row in range(6):box('Facade jamb %d-%d'%(j,row),(16.735,.7+row*.39,z),(.35,.375,.28),['Stone0','Stone1','Stone2','Stone3'][(row+j)%4],bevel=.014)
box('Door carved lintel',(16.72,3.015,-18),(.39,.23,2.42),'Stone1')
# Closed double industrial door, clear 2.35m leaf height above the 0.5m threshold.
for i,z in enumerate([-18.453,-17.547]):
 box('Door leaf '+str(i),(17.03,1.705,z),(.10,2.35,.886),'Iron','Door',.015)
 box('Door inset worn steel '+str(i),(16.967,1.79,z),(.018,1.63,.686),'Drum','Door',.005)
 box('Door kickplate '+str(i),(16.955,.76,z),(.018,.35,.77),'Iron','Door',.006)
 for y in [.76,2.55]:
  box('Door hinge %d %.2f'%(i,y),(16.93,y,z+(-.34 if i==0 else .34)),(.11,.17,.07),'Brass','Door',.009)
 box('Door handle '+str(i),(16.83,1.52,z+(.28 if i==0 else -.28)),(.055,.29,.045),'Brass','Door',.014)
box('Door threshold cap',(16.83,.52,-18),(.53,.04,2.13),'Stone3','Door',.009)
# Deep shutter recesses with slats and external frames. No baked text or false highlights.
def window(name,z,y,width,height):
 box(name+' shaded recess',(17.20,y,z),(.05,height,width),'Iron','Windows',.005)
 for side in [-1,1]:
  box(name+' jamb '+str(side),(16.78,y,z+side*(width/2+.06)),(.36,height+.25,.12),'Stone3','Windows')
 for side in [-1,1]:
  box(name+' sill '+str(side),(16.70,y+side*(height/2+.065),z),(.52,.13,width+.28),'Stone1','Windows')
 for j in range(9):
  box(name+' louvre '+str(j),(17.03,y-height/2+(j+.5)*height/9,z),(.16,height/9*.74,width-.07),'Drum','Windows',.008)
 box(name+' mullion',(16.91,y,z),(.07,height,.05),'Iron','Windows',.006)
for i,z in enumerate([-20.64,-15.36]):window('Lower shutter '+str(i),z,2.115,1.44,1.30)
upper=[(-20.58,1.35),(-18,1.64),(-15.42,1.35)]
edges=[(-21.8,-21.255),(-19.905,-18.82),(-17.18,-16.095),(-14.745,-14.2)]
for i,(a,b) in enumerate(edges):box('Upper wall pier '+str(i),(17.03,5.955,(a+b)/2),(.46,1.35,b-a),'Stone1')
for i,(z,w) in enumerate(upper):window('Upper shutter '+str(i),z,5.955,w,1.35)
box('Front story belt',(16.86,3.98,-18),(.38,.24,7.76),'Stone3','Roof')
# Corners, story belt and roof parapet are built solids with visible thickness.
for x in [16.96,24.77]:
 for z in [-21.63,-14.37]:
  for row in range(13):
   box('Quoin %.2f %.2f %d'%(x,z,row),(x,.745+row*.48,z),(.49 if row%2 else .62,.46,.62 if row%2 else .49),'Stone'+str(row%4),'Corners',.022)
for z in [-21.82,-14.18]:box('Story belt '+str(z),(20.90,3.98,z),(8.50,.19,.26),'Stone3','Roof')
box('Roof slab',(20.90,7.07,-18),(8.6,.26,7.92),'Stone2','Roof')
box('Roof membrane',(20.9,7.215,-18),(7.91,.028,7.18),'Iron','Roof',0)
for z in [-21.68,-14.32]:box('Roof parapet side '+str(z),(20.9,7.48,z),(8.35,.58,.25),'Stone1','Roof')
for x in [16.84,24.96]:box('Roof parapet end '+str(x),(x,7.48,-18),(.25,.58,7.58),'Stone0','Roof')
for z in [-21.68,-14.32]:
 for j in range(10):box('Coping side %.2f %d'%(z,j),(17.15+j*.83,7.80,z),(.808,.12,.42),'Stone3','Roof',.014)
for x in [16.84,24.96]:
 for j in range(9):box('Coping end %.2f %d'%(x,j),(x,7.80,-21.31+j*.828),(.42,.12,.807),'Stone3','Roof',.014)
# Rooftop aquifer storage and service fittings break the repeated Relay silhouette.
bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.66,depth=1.48,location=B((22.3,7.98,-19.9)))
o=bpy.context.view_layer.objects.active;o.name='Rooftop water storage';o['group']='Services';o.data.materials.append(M['Drum']);uv(o,.6);parts.append(o)
for y in [7.37,8.59]:
 bpy.ops.mesh.primitive_torus_add(major_radius=.664,minor_radius=.025,major_segments=48,minor_segments=8,location=B((22.3,y,-19.9)))
 o=bpy.context.view_layer.objects.active;o.name='Tank band '+str(y);o['group']='Services';o.data.materials.append(M['Iron']);uv(o,1);parts.append(o)
tube('Tank feed pipe',[(22.3,7.4,-19.9),(23.5,7.4,-19.9),(23.5,7.4,-14.02),(23.5,.72,-14.02)],.041,group='Services')
for y in [1.1,3.1,5.4,7.4]:box('Service pipe strap '+str(y),(23.5,y,-14.15),(.18,.04,.33),'Brass','Services',.006)
box('Roof vent curb',(19.6,7.38,-16.1),(1.2,.35,.9),'Stone2','Services')
box('Roof vent hood',(19.6,7.67,-16.1),(1.30,.26,1.0),'Drum','Services')
for j in range(7):box('Roof vent fin '+str(j),(18.91,7.60,-16.49+j*.13),(.10,.13,.04),'Iron','Services',.005)
# Export explicit per-part mesh data with authored normals, UV0 and identities.
data=[]
for o in parts:
 me=o.data;me.calc_loop_triangles();vertices,normals,tex,indices,unique=[],[],[],[],{}
 for tri in me.loop_triangles:
  for li in tri.loops:
   p=U(o.matrix_world@me.vertices[me.loops[li].vertex_index].co);n=U(o.matrix_world.to_3x3()@me.corner_normals[li].vector)
   t=[round(float(v),6) for v in me.uv_layers.active.data[li].uv];key=tuple(p+n+t)
   if key not in unique:unique[key]=len(vertices);vertices.append(p);normals.append(n);tex.append(t)
   indices.append(unique[key])
 data.append(dict(name=o.name,group=o['group'],positions=vertices,normals=normals,uv=tex,indices=indices,material=me.materials[0].name))
(OUT/'finery-mesh-data.json').write_text(json.dumps(data,separators=(',',':')))
report=dict(parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),footprint=[16.2,25,-21.8,-14.2],source='Original live Blender MCP authoring',reference='refs/courtyard_20260908/accepted-target.png',doorLeafMetres=[.886,2.35],roofY=7.86,geometry='Constructed wall openings, separate reveals/shutters, stone piers, bevelled copings, closed double door, roof services; no artificial subdivision.')
(OUT/'finery-geometry-report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'finery-frontage.blend'))
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.fbx(filepath=str(OUT/'finery-frontage.fbx'),use_selection=True,axis_forward='-Z',axis_up='Y',add_leaf_bones=False,bake_anim=False)
print(json.dumps(report))
