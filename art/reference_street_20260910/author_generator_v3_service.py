"""Live Blender: separate metric side-service repair, preserving complete V2 core.
Original source/review objects, mesh data and PBR files are not edited. New parts
are authored construction, not independent axis scaling of an imported model.
"""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source'
assert not O.exists(),'Preserve prior authored source revision'
H=bpy.data.objects['GENERATOR_V2_SOURCE'];OLD=bpy.data.scenes['Generator v2 source inspection']
S=bpy.data.scenes.new('Generator v3 side service authoring');bpy.context.window.scene=S
S.unit_settings.system='METRIC';S.unit_settings.scale_length=1
S.render.engine='CYCLES';S.cycles.samples=24;S.cycles.use_denoising=True;S.cycles.device='GPU'
S.render.resolution_x=1400;S.render.resolution_y=1100;S.render.resolution_percentage=100
S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGBA'
S.view_settings.view_transform='AgX';S.view_settings.exposure=0;S.world=OLD.world
for o in OLD.objects:
 if o==H:continue
 c=o.copy();S.collection.objects.link(c)
 if o==OLD.camera:S.camera=c
C=bpy.data.collections.new('Generator v3 editable source parts');S.collection.children.link(C)
core=H.copy();core.name='GENERATOR_V3_RETAINED_CORE';C.objects.link(core);core.hide_render=False
parts=[];ports=[]
def own(o,name,mat):
 o.name=name
 for c in list(o.users_collection):c.objects.unlink(o)
 C.objects.link(o)
 if mat:o.data.materials.clear();o.data.materials.append(mat)
 parts.append(o)
 return o

def material(name,color,metal,rough,bump=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;k=m.node_tree.links;p=n.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 if bump:
  g=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=95;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.55
  k.new(g.outputs['Position'],noise.inputs['Vector']);b=n.new('ShaderNodeBump');b.inputs['Strength'].default_value=.13;b.inputs['Distance'].default_value=bump
  k.new(noise.outputs['Fac'],b.inputs['Height']);k.new(b.outputs['Normal'],p.inputs['Normal'])
 return m
paint=material('Service tank ochre paint',(.43,.205,.040),.025,.58,.00018)
steel=material('Service cradle dark painted steel',(.050,.055,.050),.08,.56,.00010)
edge=material('Service hardware exposed steel',(.185,.195,.190),.86,.34,.000045)
copper=material('Service cooling tube copper',(.48,.205,.090),.98,.32,.00004)
rubber=material('Service hoses and gaskets rubber',(.017,.020,.016),0,.73,.00009)
brass=material('Service pipe unions dull brass',(.27,.20,.085),.9,.37,.00005)
wear=material('Localized ochre rub-through',(.085,.095,.084),.64,.63,.00008)

def activate(o):
 for x in S.objects:x.select_set(False)
 o.select_set(True);bpy.context.view_layer.objects.active=o

def bevel(o,width=.002,segments=3):
 activate(o);m=o.modifiers.new('Machined edge radius','BEVEL');m.width=width;m.segments=segments;m.harden_normals=True
 bpy.ops.object.modifier_apply(modifier=m.name)
 for p in o.data.polygons:p.use_smooth=True
 w=o.modifiers.new('Area weighted construction normals','WEIGHTED_NORMAL');w.keep_sharp=True;w.weight=50
 bpy.ops.object.modifier_apply(modifier=w.name)
 return o

def box(name,center,size,mat=steel,r=.002):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=own(bpy.context.object,name,mat);o.scale=size
 activate(o);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 return bevel(o,min(r,min(size)*.35),3)

def cylinder(name,a,b,r,mat=steel,vertices=48,bevel_width=.001):
 a,b=Vector(a),Vector(b);d=b-a
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,end_fill_type='NGON',location=(a+b)/2)
 o=own(bpy.context.object,name,mat);o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
 if bevel_width:bevel(o,bevel_width,3)
 return o

def pipe(name,points,r,mat,cyclic=False,resolution=4):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=resolution;curve.bevel_depth=r;curve.bevel_resolution=4;curve.use_fill_caps=not cyclic
 spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
 for p,v in zip(spline.points,points):p.co=(*v,1)
 spline.use_cyclic_u=cyclic
 o=bpy.data.objects.new(name,curve);S.collection.objects.link(o);own(o,name,None);o.data.materials.append(mat)
 activate(o);bpy.ops.object.convert(target='MESH')
 for p in o.data.polygons:p.use_smooth=True
 return o

def ring(name,center,axis,r,wire,mat):
 axis=Vector(axis).normalized();u=axis.cross(Vector((0,0,1)))
 if u.length<.1:u=axis.cross(Vector((0,1,0)))
 u.normalize();v=axis.cross(u);center=Vector(center)
 return pipe(name,[center+r*(math.cos(t*math.tau/64)*u+math.sin(t*math.tau/64)*v)for t in range(64)],wire,mat,True)

def bolt(name,center,axis=(1,0,0),radius=.008):
 p=Vector(center);a=Vector(axis).normalized()
 cylinder(name+' washer',p-a*.001,p+a*.0015,radius*1.5,edge,32,.0005)
 return cylinder(name+' hex head',p+a*.0015,p+a*.007,radius,edge,6,.0007)

# Lathed, closed, domed vessel along Blender Y. Geometry carries the curvature.
profile=[(-.374,0),(-.371,.040),(-.363,.071),(-.349,.094),(-.328,.108),(-.305,.115),(.305,.115),(.328,.108),(.349,.094),(.363,.071),(.371,.040),(.374,0)]
verts=[];faces=[];rings=[]
for y,r in profile:
 if r==0:
  rings.append([len(verts)]);verts.append((.775,y,.80))
 else:
  rings.append(list(range(len(verts),len(verts)+96)))
  verts.extend([(.775+r*math.cos(t*math.tau/96),y,.80+r*math.sin(t*math.tau/96))for t in range(96)])
for a,b in zip(rings,rings[1:]):
 if len(a)==1:faces.extend([(a[0],b[(i+1)%96],b[i])for i in range(96)])
 elif len(b)==1:faces.extend([(a[i],a[(i+1)%96],b[0])for i in range(96)])
 else:faces.extend([(a[i],a[(i+1)%96],b[(i+1)%96],b[i])for i in range(96)])
mesh=bpy.data.meshes.new('Domed service vessel mesh');mesh.from_pydata(verts,[],faces);mesh.update()
tank=bpy.data.objects.new('Strapped ochre service tank',mesh);S.collection.objects.link(tank);own(tank,tank.name,paint)
# Correct predictable outward winding on the closed lathe using signed volume.
import bmesh
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
for p in mesh.polygons:p.use_smooth=True
for y in (-.303,.303):ring('Tank rolled end seam '+str(y),(.775,y,.80),(0,1,0),.1155,.0015,wear)
# Two real wrap bands, wide flat strip mesh conforming around the vessel.
for y in (-.225,.225):
 v=[];f=[]
 for yy in (y-.015,y+.015):
  for i in range(96):
   a=i*math.tau/96;v.append((.775+.1175*math.cos(a),yy,.80+.1175*math.sin(a)))
 for i in range(96):f.append((i,(i+1)%96,(i+1)%96+96,i+96))
 me=bpy.data.meshes.new('Formed tank strap');me.from_pydata(v,[],f);me.update();o=bpy.data.objects.new('Tank strap '+str(y),me);S.collection.objects.link(o);own(o,o.name,edge)
 activate(o);mod=o.modifiers.new('Two millimetre steel band','SOLIDIFY');mod.thickness=.002;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
 bevel(o,.0006,2)
 box('Tank strap mounting ear '+str(y),(.746,y,.669),(.10,.045,.016),steel,.002)
 bolt('Tank strap M8 fixing '+str(y),(.796,y,.668),(0,0,-1),.008)
 box('Tank isolating saddle '+str(y),(.735,y,.681),(.075,.049,.016),rubber,.002)
# Filler neck, gasket and grippable cap, physically joined to vessel top.
cylinder('Tank filler neck',(.775,-.12,.901),(.775,-.12,.930),.030,edge,64,.001)
ring('Filler rubber seal',(.775,-.12,.930),(0,0,1),.032,.0025,rubber)
cylinder('Tank filler cap',(.775,-.12,.931),(.775,-.12,.952),.040,steel,64,.002)
for i in range(12):
 a=i*math.tau/12;c=(.775+.040*math.cos(a),-.12+.040*math.sin(a),.942)
 cylinder('Filler grip '+str(i),(c[0],c[1],.935),(c[0],c[1],.949),.003,edge,12,.0006)
# A surrounding rounded rectangular guard, kept inside the canonical envelope.
ylim=.414;zlo=.092;zhi=.974;corner=.060
path=[]
for cy,cz,start in [(ylim-corner,zhi-corner,0),(-ylim+corner,zhi-corner,90),(-ylim+corner,zlo+corner,180),(ylim-corner,zlo+corner,270)]:
 for j in range(17):
  a=math.radians(start+j*90/16);path.append((.915,cy+corner*math.cos(a),cz+corner*math.sin(a)))
pipe('Continuous side service cage',path,.021,steel,True)
# Four rigid bolted ties join the service cage to original frame, plus grounded skid.
for y in (-.17,.17):
 for z in (.15,.655):
  a=(.585,y,z);b=(.903,math.copysign(.37,y),z)
  cylinder('Cradle tie '+str((y,z)),a,b,.021,steel,32,.001)
  box('Cradle tie root plate '+str((y,z)),(.627,y,z),(.013,.066,.068),steel,.002)
  bolt('Cradle tie upper fastener '+str((y,z)),(.636,y,z+.019))
  bolt('Cradle tie lower fastener '+str((y,z)),(.636,y,z-.019))
box('Side service longitudinal skid',(.877,0,.057),(.078,.868,.058),steel,.004)
for y in (-.375,.375):
 box('Service skid sole '+str(y),(.877,y,.012),(.130,.120,.024),rubber,.003)
 box('Service skid pedestal '+str(y),(.877,y,.043),(.092,.084,.042),steel,.003)
 bolt('Skid bolted foot '+str(y),(.880,y,.067),(0,0,1),.007)
# A single continuous copper serpentine: four straight runs and real semicircular returns.
coil=[];xc=.887;end=.314;spacing=.068;top=.612
for row in range(4):
 z=top-row*spacing;left=(-end if row%2==0 else end);right=-left
 if not coil:coil.append((xc,left,z))
 coil.append((xc,right,z))
 if row<3:
  cy=right;cz=z-spacing/2
  for i in range(1,25):
   a=math.pi*i/24
   yy=cy+(1 if right>0 else -1)*(spacing/2)*math.sin(a)
   zz=cz+(spacing/2)*math.cos(a)
   coil.append((xc,yy,zz))
pipe('Continuous four-run copper cooling coil',coil,.012,copper)
for y in (-.225,.225):
 box('Cooling coil restraint '+str(y),(.903,y,.509),(.009,.026,.278),edge,.001)
 for z in (.383,.635):
  box('Cooling restraint mounting stand '+str((y,z)),(.878,y,z),(.050,.035,.022),steel,.001)
  bolt('Cooling restraint bolt '+str((y,z)),(.911,y,z),(1,0,0),.006)
# Three surface-queried inlet/return attachments on the retained engine side.
bpy.context.view_layer.update()
def core_port(label,y,z):
 inv=core.matrix_world.inverted();origin=inv@Vector((2,y,z));direction=inv.to_3x3()@Vector((-1,0,0));direction.normalize()
 hit,point,normal,index=core.ray_cast(origin,direction)
 assert hit,'Missing engine surface for '+label
 p=core.matrix_world@point;n=core.matrix_world.to_3x3().inverted().transposed()@normal;n.normalize()
 assert n.x>.65,'Inspect an unsuitable side attachment normal before making a floating flange'
 outer=p+n*.024
 cylinder(label+' engine flange',p-n*.003,outer,.025,edge,48,.001)
 cylinder(label+' hex union',outer,outer+n*.020,.018,brass,6,.001)
 ports.append({'name':label,'queriedSurfacePoint':list(p),'surfaceNormal':list(n),'faceIndex':index,'flangeSinksMetres':.003})
 return outer+n*.023
port_hot=core_port('Cooling inlet',-.05,.58)
port_return=core_port('Cooling return',.10,.44)
port_tank=core_port('Service tank feed',.10,.67)
# Catmull-Rom centreline samples, converted to a continuous ribbed rubber mesh.
def hose(name,controls,step=.0025):
 ps=[Vector(p)for p in controls];dense=[]
 for i in range(len(ps)-1):
  p0=ps[max(0,i-1)];p1=ps[i];p2=ps[i+1];p3=ps[min(len(ps)-1,i+2)]
  for j in range(40):
   t=j/40;dense.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
 dense.append(ps[-1]);lengths=[0.0]
 for a,b in zip(dense,dense[1:]):lengths.append(lengths[-1]+(b-a).length)
 count=max(8,math.ceil(lengths[-1]/step));sample=[];idx=0
 for i in range(count+1):
  d=lengths[-1]*i/count
  while idx<len(lengths)-2 and lengths[idx+1]<d:idx+=1
  f=(d-lengths[idx])/max(1e-9,lengths[idx+1]-lengths[idx]);sample.append(dense[idx].lerp(dense[idx+1],f))
 verts=[];faces=[];u=Vector((0,1,0))
 for i,p in enumerate(sample):
  tangent=(sample[min(i+1,count)]-sample[max(0,i-1)]).normalized();u=(u-tangent*u.dot(tangent)).normalized()
  if u.length<.2:u=tangent.cross(Vector((0,0,1))).normalized()
  v=tangent.cross(u);d=lengths[-1]*i/count;fade=min(1,d/.025,(lengths[-1]-d)/.025)
  radius=.0125+.0017*fade*(.5+.5*math.cos(d*math.tau/.008))**2
  for j in range(16):verts.append(p+radius*(math.cos(j*math.tau/16)*u+math.sin(j*math.tau/16)*v))
 for i in range(count):
  for j in range(16):faces.append((i*16+j,i*16+(j+1)%16,(i+1)*16+(j+1)%16,(i+1)*16+j))
 faces.append(tuple(reversed(range(16))));faces.append(tuple(range(count*16,(count+1)*16)))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);S.collection.objects.link(o);own(o,name,rubber)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 return o
# Cooling inlet/return connect at the actual copper tube endpoints, each with a union.
for label,p,direction in [('Cooling upper union',coil[0],(0,-1,0)),('Cooling lower union',coil[-1],(0,-1,0))]:
 p=Vector(p);axis=Vector(direction)
 cylinder(label,p-axis*.005,p+axis*.023,.016,brass,6,.001)
 ring(label+' rubber seal',p+axis*.025,axis,.0127,.0018,rubber)
hose('Routed cooling inlet hose',[port_hot,port_hot+Vector((.065,-.025,.015)),(.81,-.382,.68),(.887,-.379,.632),(.887,-.340,.612)])
hose('Routed cooling return hose',[(.887,-.340,.408),(.875,-.385,.346),(.79,-.28,.271),(.73,.20,.278),port_return+Vector((.07,.05,-.005)),port_return])
cylinder('Tank outlet boss',(.775,.255,.687),(.775,.255,.662),.020,brass,6,.001)
hose('Routed service tank feed hose',[(.775,.255,.660),(.775,.291,.620),(.718,.280,.617),port_tank+Vector((.045,.06,0)),port_tank])
# Restraints at low hose route, with no decorative loose ends.
for y in (-.20,.18):
 box('Return hose support tab '+str(y),(.740,y,.273),(.040,.035,.014),steel,.001)
 bolt('Return line support fixing '+str(y),(.746,y,.264),(0,0,-1),.005)
# Record physical construction and bounds; no asset is installed in Unity.
bpy.context.view_layer.update()
O.mkdir(parents=True)
for o in [core]+parts:o.data.calc_loop_triangles()
points=[o.matrix_world@Vector(c)for o in [core]+parts for c in o.bound_box]
lo=Vector(tuple(min(p[i]for p in points)for i in range(3)));hi=Vector(tuple(max(p[i]for p in points)for i in range(3)))
assert hi.x-lo.x<=1.6+1e-5 and hi.y-lo.y<=.95+1e-5 and hi.z-lo.z<=1.1+1e-5,'New source escaped the canonical envelope; inspect instead of axis stretching'
records=[]
for o in parts:
 o.data.calc_loop_triangles();records.append({'name':o.name,'triangles':len(o.data.loop_triangles),'material':o.data.materials[0].name,'position':list(o.location),'dimensions':list(o.dimensions)})
S['generator_v3_output']=str(O);S['generator_v3_core']=core.name;S['generator_v3_collection']=C.name
manifest={'revision':'generator-v3-source','method':'Original live Blender side service authoring around unchanged detailed V2 core','sourceCoreFbx':'meshy/ground-detail-20260910/generator-v2/model.fbx','sourceCoreTriangles':len(core.data.loop_triangles),'sourceCoreGeometryAndUVUnchanged':True,'noAxisStretch':True,'canonicalUnityXYZMetres':[1.6,1.1,.95],'boundsBlender':[list(lo),list(hi)],'sizeUnityXYZMetres':[hi.x-lo.x,hi.z-lo.z,hi.y-lo.y],'sideTank':{'axis':'BlenderY depth','center':[.775,0,.80],'barrelRadiusMetres':.115,'totalLengthMetres':.748,'strapWidthMetres':.030},'sideGuard':{'centrePlaneX':.915,'tubeRadiusMetres':.021,'depthOutsideMetres':.870},'cooler':{'continuousRuns':4,'pipeRadiusMetres':.012,'returnBendRadiusMetres':.034,'runSeparationMetres':.068},'attachments':ports,'authoredParts':records,'authoredTriangles':sum(p['triangles']for p in records),'materials':[{'name':m.name,'baseColor':list(m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value),'metallic':m.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value,'roughness':m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value}for m in [paint,steel,edge,copper,rubber,brass,wear]],'sourceAccepted':False,'nativeAccepted':False,'remaining':['Whole/side/connection source critic review','Grille rail cleanup in retained core','Matched normal-disabled diagnostic to isolate source microgrid','Near derivation only after source acceptance','Final source-to-near PBR baking and native fit/access/performance']}
(O/'authoring-manifest-v3.json').write_text(json.dumps(manifest,indent=2)+'\n')
bpy.data.libraries.write(str(O/'generator-v3-service-authoring.blend'),{S},fake_user=True,path_remap='RELATIVE')
print(json.dumps({'scene':S.name,'sourceCoreTriangles':len(core.data.loop_triangles),'authoredParts':len(parts),'authoredTriangles':manifest['authoredTriangles'],'sizeUnityXYZMetres':manifest['sizeUnityXYZMetres'],'attachments':ports,'output':str(O)}))
