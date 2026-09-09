"""Run through the existing live Blender MCP. Original Ward utility-fixture family."""
import bpy, bmesh, math, json, random
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2'); O=R/'art/quality_20260908/lamps'
# The preceding tree document was explicitly saved and Blender ownership released.
scene=bpy.data.scenes.get('Ward lamp family') or bpy.data.scenes.new('Ward lamp family')
assert scene.get('ward_asset') in [None,'utility-lamps']
assert not scene.objects or scene.get('ward_asset')=='utility-lamps' or all(ob.name.startswith(('Post ','Wall ','Preview ground','Studio ','Fixture review')) for ob in scene.objects)
scene['ward_asset']='utility-lamps'
bpy.context.window.scene=scene
for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
rng=random.Random(908264); objects=[]; family='Post'; group='Base'
def B(p):return Vector((p[0],-p[2],p[1]))
def U(p):return [round(p.x,6),round(p.z,6),round(-p.y,6)]
M={}
for name,col in {'Paint':(.25,.225,.19),'Base':(.22,.195,.165),'Steel':(.32,.34,.34),'Bronze':(.37,.285,.16),'Rubber':(.047,.045,.041),'Enamel':(.31,.34,.31),'Dust':(.30,.275,.235),'Oxide':(.24,.145,.078),'LampEmission':(.78,.70,.51)}.items():
 m=bpy.data.materials.get('WardLamp_'+name) or bpy.data.materials.new('WardLamp_'+name);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=.65
 if name=='LampEmission':
  bs.inputs['Emission Color'].default_value=(1,.71,.36,1);bs.inputs['Emission Strength'].default_value=1.5
 else:
  for suffix,socket,noncolor in [('_BaseColor.png','Base Color',False),('_MetalSmooth.png',None,True),('_Normal.png',None,True)]:
   p=O/'textures'/(name+suffix)
   if not p.exists():continue
   node=m.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(p),check_existing=True);node.image.reload()
   if noncolor:node.image.colorspace_settings.name='Non-Color'
   if socket:
    m.node_tree.links.new(node.outputs['Color'],bs.inputs[socket])
    if name=='Dust':m.node_tree.links.new(node.outputs['Alpha'],bs.inputs['Alpha']);m.surface_render_method='DITHERED'
   elif 'Normal' in suffix:
    normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(node.outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
   else:
    split=m.node_tree.nodes.new('ShaderNodeSeparateColor');m.node_tree.links.new(node.outputs['Color'],split.inputs['Color']);m.node_tree.links.new(split.outputs['Red'],bs.inputs['Metallic'])
    inv=m.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;m.node_tree.links.new(node.outputs['Alpha'],inv.inputs[1]);m.node_tree.links.new(inv.outputs[0],bs.inputs['Roughness'])
 M[name]=m
def finish(ob,name,mat,bevel=0):
 ob.name=family+' '+name;ob['family']=family;ob['group']=group;ob['region']=mat
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.type=='CURVE':bpy.ops.object.convert(target='MESH');ob=bpy.context.object
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=ob.modifiers.new('Manufactured edge radius','BEVEL');mod.width=bevel;mod.segments=3
  bpy.ops.object.modifier_apply(modifier=mod.name)
 me=ob.data;me.materials.clear();me.materials.append(M[mat])
 # Metric box projection per plane, with different offsets on each part to avoid repeated marks.
 uv=me.uv_layers.active or me.uv_layers.new(name='UV0 metres')
 off=(rng.random()*7,rng.random()*7)
 for face in me.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]))
  for li in face.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   uv.data[li].uv=((v.y if axis==0 else v.x)/.75+off[0],(v.y if axis==2 else v.z)/.75+off[1])
  face.use_smooth=True
 mod=ob.modifiers.new('Weighted manufactured normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 bpy.ops.object.modifier_apply(modifier=mod.name);objects.append(ob);return ob
def box(name,p,size,mat='Paint',bevel=.004):
 bpy.ops.mesh.primitive_cube_add(size=1,location=B(p));ob=bpy.context.object;ob.dimensions=(size[0],size[2],size[1]);return finish(ob,name,mat,min(bevel,min(size)/4))
def cylinder(name,p,r,depth,mat='Paint',axis=(0,1,0),r2=None,verts=48,bevel=.003):
 bpy.ops.mesh.primitive_cone_add(vertices=verts,radius1=r,radius2=r if r2 is None else r2,depth=depth,location=B(p));ob=bpy.context.object
 ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(B(axis).normalized())
 return finish(ob,name,mat,bevel)
def tube(name,points,r=.012,mat='Paint'):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=2;c.bevel_depth=r;c.bevel_resolution=3
 sp=c.splines.new('POLY');sp.points.add(len(points)-1)
 for a,p in zip(sp.points,points):a.co=(*B(p),1)
 ob=bpy.data.objects.new(name,c);scene.collection.objects.link(ob);return finish(ob,name,mat)
def ring(name,p,r,minor,mat='Steel',axis=(0,1,0),seg=64):
 bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=minor,major_segments=seg,minor_segments=8,location=B(p));ob=bpy.context.object
 ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(B(axis).normalized())
 return finish(ob,name,mat)
def bolt(name,p,r=.015,axis=(0,1,0)):
 cylinder(name+' washer',p,r*1.5,.004,'Steel',axis,verts=32,bevel=.0005)
 pp=Vector(p)+Vector(axis)*.010;cylinder(name+' hex head',pp,r,.014,'Steel',axis,verts=6,bevel=.0015)
def patch(name,points,mat='Dust'):
 # Localised opaque paint/dust film, laid less than 1mm above the actual part surface.
 pts=[B(p)for p in points];expected=B((0,0,1)if max(p[2]for p in points)-min(p[2]for p in points)<.00001 else(0,1,0))
 centre=sum(pts,Vector())/len(pts);normal=sum(((pts[j]-centre).cross(pts[(j+1)%len(pts)]-centre)for j in range(len(pts))),Vector())
 if normal.dot(expected)<0:pts.reverse()
 me=bpy.data.meshes.new(name);me.from_pydata(pts,[],[tuple(range(len(pts)))]);me.update()
 ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob=finish(ob,name,mat)
 if mat=='Dust':
  axis=1 if abs(expected.z)>.5 else 2
  axes=(0,axis);mins=[min(v.co[a]for v in ob.data.vertices)for a in axes];maxs=[max(v.co[a]for v in ob.data.vertices)for a in axes]
  for li in range(len(ob.data.loops)):
   q=ob.data.vertices[ob.data.loops[li].vertex_index].co;ob.data.uv_layers.active.data[li].uv=[(q[a]-lo)/max(.000001,hi-lo)for a,lo,hi in zip(axes,mins,maxs)]
 return ob
def saddle(y):
 global group
 group='Wiring'
 f=(y-.53)/3.64;cx=.072-.020*f;cz=-.054+.013*f
 radial=Vector((cx,0,cz)).normalized();tan=Vector((-radial.z,0,radial.x));r=.083-.022*((y-.25)/4)
 ts=[-.032,-.026,-.020,-.014,-.009,0,.009,.014,.020,.026,.032];vs=[]
 for layer in [0,.002]:
  for yy in [y-.012,y+.012]:
   for t in ts:
    rr=math.sqrt(max(.001,r*r-t*t))+.001+.018*math.exp(-((t/.014)**4))+layer
    vs.append(B(radial*rr+tan*t+Vector((0,yy,0))))
 n=len(ts);faces=[]
 for k in range(n-1):
  faces.extend([(k,k+1,n+k+1,n+k),(2*n+k,3*n+k,3*n+k+1,2*n+k+1),(k,2*n+k,2*n+k+1,k+1),(n+k,n+k+1,3*n+k+1,3*n+k)])
 faces.extend([(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)])
 me=bpy.data.meshes.new('Saddle');me.from_pydata(vs,[],faces);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();ob=bpy.data.objects.new('Saddle',me);scene.collection.objects.link(ob);finish(ob,'Formed conduit saddle '+str(y),'Bronze')
 for t in [-.026,.026]:
  foot=radial*math.sqrt(r*r-t*t)+tan*t;normal=foot.normalized();p=foot+normal*.004+Vector((0,y,0))
  cylinder('Saddle captive screw '+str(y)+' '+str(t),p,.0055,.005,'Steel',normal,verts=12,bevel=.0007)
def revolve(name,c,profile,mat,segments=64,rib=0):
 # A closed ring profile produces wall thickness instead of one-sided paper surfaces.
 vs=[];faces=[];rows=[]
 for radius,y in profile:
  if radius < .000001:
   rows.append([len(vs)]);vs.append(B((c[0],c[1]+y,c[2])));continue
  row=[]
  for j in range(segments):
   a=j*2*math.pi/segments;rr=radius+(rib*(.5+.5*math.cos(a*16)) if radius>.03 else 0)
   row.append(len(vs));vs.append(B((c[0]+math.cos(a)*rr,c[1]+y,c[2]+math.sin(a)*rr)))
  rows.append(row)
 for i in range(len(profile)):
  a,b=rows[i],rows[(i+1)%len(rows)]
  if len(a)==len(b)==1:continue
  for j in range(segments):
   k=(j+1)%segments
   if len(a)==1:faces.append((a[0],b[k],b[j]))
   elif len(b)==1:faces.append((a[j],a[k],b[0]))
   else:faces.append((a[j],a[k],b[k],b[j]))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update();ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);return finish(ob,name,mat)
def light_head(cx,cy,cz,s=1):
 global group
 group='Lamp head';c=(cx,cy,cz)
 def p(x,y,z):return (cx+x*s,cy+y*s,cz+z*s)
 # Spun enamel hood with folded 9 mm rim and visible metal thickness.
 profile=[(.073,.25),(.085,.22),(.145,.19),(.236,.08),(.257,.056),(.257,.047),(.234,.055),(.139,.174),(.079,.211),(.065,.242)]
 revolve('Spun rain hood',c,[(r*s,y*s)for r,y in profile],'Enamel')
 cylinder('Service cap',p(0,.277,0),.083*s,.055*s,'Paint',r2=.065*s)
 ring('Cap gasket',p(0,.245,0),.074*s,.007*s,'Rubber')
 cylinder('Porcelain socket',p(0,.145,0),.048*s,.095*s,'Steel')
 for y in [.113,.13,.148]:ring('Socket thread %.3f'%y,p(0,y,0),.049*s,.003*s,'Bronze')
 # Opal glass is a volumetric ribbed capsule. Ceramic LED replacement core is internal.
 profile=[(.046,.108),(.064,.077),(.087,.030),(.087,-.082),(.075,-.117),(.05,-.14),(.014,-.151),(0,-.145),(0,.10)]
 revolve('Ribbed opal glass',c,[(r*s,y*s)for r,y in profile],'LampEmission',rib=.0012*s)
 for yy,rr in [(.036,.132),(-.115,.112)]:ring('Cage guard hoop %.3f'%yy,p(0,yy,0),rr*s,.008*s,'Steel')
 for j in range(6):
  a=j*math.pi/3;points=[]
  for yy,rr in [(.058,.174),(.035,.134),(-.09,.118),(-.155,.084),(-.18,.021)]:points.append(p(math.cos(a)*rr,yy,math.sin(a)*rr))
  tube('Guard rib '+str(j),points,.006*s,'Steel')
  bolt('Hood retaining bolt '+str(j),p(math.cos(a)*.178,.062,math.sin(a)*.178),.009*s)
 cylinder('Cage drain nut',p(0,-.186,0),.026*s,.022*s,'Bronze',verts=12)
 for a in [0,math.pi]:
  box('Hood service latch '+str(a),p(math.cos(a)*.181,.069,0),(.036*s,.038*s,.014*s),'Bronze',.003)
 # Dust lies on the rain lip and cap seam; rust follows a few exposed rim chips.
 for k,(start,end) in enumerate([(.20,.71),(1.64,2.03),(3.32,3.89),(4.95,5.21)]):
  points=[]
  for j in range(8):
   a=start+(end-start)*j/7;rr=.246+.002*math.sin(j*3.1+k);hy=.08-(rr-.236)*(.024/.021)+.0007;points.append(p(math.cos(a)*rr,hy,math.sin(a)*rr))
  for j in reversed(range(8)):
   a=start+(end-start)*j/7;rr=.255+.001*math.sin(j*2.4+k);hy=.08-(rr-.236)*(.024/.021)+.0007;points.append(p(math.cos(a)*rr,hy,math.sin(a)*rr))
  patch('Rain lip dust deposit '+str(k),points,'Dust')
 for k,a in enumerate([.22,.28,.36,1.68,1.80,3.34,3.59,5.21]):
  rr=.236;yy=.081;points=[]
  for da,dr in [(-.035,0),(-.027,.009),(.011,.015),(.029,.007),(.036,0),(.005,-.004)]:
   da*=.28+(k%3)*.04;dr*=.23+(k%2)*.04
   radius=rr+dr;hy=.08-dr*(.024/.021)+.0008;points.append(p(math.cos(a+da)*radius,hy,math.sin(a+da)*radius))
  patch('Enamel rim paint loss '+str(k),points,'Oxide')

# Post variant: all editable components retain metre dimensions.
group='Foundation'
box('Cast concrete footing',(0,.115,0),(.46,.23,.46),'Base',.018)
box('Anchor plate',(0,.239,0),(.325,.025,.325),'Steel',.007)
for x in [-.122,.122]:
 for z in [-.122,.122]:bolt('Foundation anchor %.2f %.2f'%(x,z),(x,.257,z),.019)
group='Mast'
cylinder('Tapered steel mast',(0,2.25,0),.083,4.0,'Paint',r2=.061,verts=64)
cylinder('Cast base sleeve',(0,.382,0),.116,.28,'Base',r2=.096)
ring('Mast base gasket',(0,.52,0),.091,.01,'Rubber')
for yy in [.30,.48,2.5,4.16]:ring('Service collar %.2f'%yy,(0,yy,0),.086 if yy<1 else .072,.012,'Steel')
box('Hatch rubber seal',(0,.86,.081),(.135,.39,.018),'Rubber',.009)
box('Gasketed service hatch',(0,.86,.095),(.119,.367,.024),'Paint',.012)
for yy in [.725,.995]:bolt('Access captive screw '+str(yy),(.036,yy,.110),.008,(0,0,1))
for yy in [.75,.97]:cylinder('Access hinge '+str(yy),(-.062,yy,.09),.012,.060,'Steel')
group='Local weathering'
for k,(x,y) in enumerate([(-.056,.751),(-.057,.792),(.056,.934),(.055,.713),(-.047,1.035)]):
 patch('Hatch exposed edge '+str(k),[(x-.002,y-.014,.108),(x+.003,y-.010,.108),(x+.002,y+.006,.108),(x-.001,y+.017,.108),(x-.004,y+.004,.108)],'Steel')
patch('Hatch lower seam dust',[(-.051,.687,.1073),(-.019,.686,.1073),(.011,.689,.1073),(.051,.686,.1073),(.051,.692,.1073),(.009,.693,.1073),(-.031,.691,.1073),(-.051,.692,.1073)],'Dust')
for k,(axis,sign,start,end)in enumerate([(0,-1,-.141,.108),(1,1,-.136,.127),(0,1,-.131,-.015)]):
 points=[]
 for j in range(10):
  t=start+(end-start)*j/9;outer=.178+.004*math.sin(j*2.1+k)
  points.append((sign*outer,.231,t)if axis==0 else(t,.231,sign*outer))
 for j in reversed(range(10)):
  t=start+(end-start)*j/9;inner=.160+.003*math.sin(j*1.7+k)
  points.append((sign*inner,.231,t)if axis==0 else(t,.231,sign*inner))
 patch('Foot plate edge granular dust '+str(k),points,'Dust')
for k,(x,z)in enumerate([(-.122,-.122),(.122,.122)]):
 points=[]
 for j in range(12):
  a=.35+j*.13;rr=.030+.0017*math.sin(j*2.4);points.append((x+rr*math.cos(a),.2523,z+rr*math.sin(a)))
 for j in reversed(range(12)):
  a=.35+j*.13;rr=.027+.0006*math.sin(j*3.1);points.append((x+rr*math.cos(a),.2523,z+rr*math.sin(a)))
 patch('Anchor washer oxidised seam '+str(k),points,'Oxide')
for k,a in enumerate([.4,1.8,3.2,4.7]):
 points=[]
 for da,r in [(-.28,.087),(-.16,.099),(.17,.096),(.28,.087),(.1,.083),(-.12,.083)]:points.append((math.cos(a+da)*r,.52+math.sqrt(max(0,.010**2-(r-.091)**2))+.0006,math.sin(a+da)*r))
 patch('Base collar dust '+str(k),points,'Dust')
group='Wiring'
# Conduit meets a sealed terminal gland, then travels inside the curved suspension.
tube('Mast exterior conduit',[(.072,.53,-.054),(.074,1,-.054),(.059,2.5,-.048),(.052,4.17,-.041)],.010,'Rubber')
for yy in [.68,1.55,2.5,3.46,4.08]:
 saddle(yy)
bolt('Supply gland bolt',(0,4.15,0),.015)
points=[]
for i in range(33):
 a=math.pi-(math.pi*.5)*i/32
 # Curved neck rises from shaft and bends forward smoothly.
 points.append((0,4.16+.37*math.sin(a),.37+.37*math.cos(a)))
points +=[(0,4.53,.46),(0,4.50,.52),(0,4.47,.52)]
tube('Bent steel suspension',points,.035,'Paint')
cylinder('Neck locking collar',(0,4.17,0),.063,.12,'Bronze')
light_head(0,4.19,.52)

# Wall variant: local origin is the wall mounting centre. +Z projects outwards.
family='Wall';group='Wall mounting'
box('Mount gasket',(0,0,.009),(.22,.34,.018),'Rubber',.013)
box('Wall mounting plate',(0,0,.029),(.20,.32,.022),'Paint',.015)
for x in [-.069,.069]:
 for y in [-.122,.122]:bolt('Wall masonry anchor %.2f %.2f'%(x,y),(x,y,.047),.013,(0,0,1))
box('Cable junction box',(0,-.009,.083),(.123,.168,.071),'Paint',.013)
box('Junction lid',(0,-.009,.126),(.126,.169,.012),'Steel',.007)
for x in [-.042,.042]:bolt('Junction screw '+str(x),(x,.047,.139),.006,(0,0,1))
tube('Wall riser into masonry',[(0,-.17,.074),(0,-.27,.074),(0,-.30,.058),(0,-.31,.025),(0,-.31,-.05)],.013,'Rubber')
box('Wall feed sealing plate',(0,-.31,0),(.122,.072,.022),'Paint',.006)
cylinder('Wall feed compression gland',(0,-.31,.028),.026,.034,'Bronze',(0,0,1),verts=12)
ring('Wall feed weather seal',(0,-.31,.008),.030,.005,'Rubber',(0,0,1))
for x in [-.045,.045]:bolt('Feed plate anchor '+str(x),(x,-.31,.014),.006,(0,0,1))
patch('Junction lower seam dust',[(-.055,-.092,.133),(-.018,-.094,.133),(.023,-.091,.133),(.058,-.091,.133),(.056,-.086,.133),(.008,-.087,.133),(-.044,-.086,.133)],'Dust')
ring('Weatherproof gland',(0,-.107,.082),.019,.004,'Bronze')
group='Wall bracket'
tube('Upper bracket rail',[(0,.103,.083),(0,.188,.083),(0,.26,.135),(0,.26,.35),(0,.235,.414),(0,.17,.414)],.022,'Paint')
tube('Triangular bracket stay',[(0,-.06,.072),(0,.10,.32),(0,.23,.377)],.014,'Steel')
for y in [.10,-.06]:cylinder('Bracket mounting pin '+str(y),(0,y,.076),.019,.14,'Bronze',(1,0,0))
light_head(0,-.003,.414,.76)

# Preserve explicit part identities/materials and source normals. Unity uses X/Z ground, Y up.
data=[]
for ob in objects:
 me=ob.data;me.calc_loop_triangles();vs=[];ns=[];uv=[];ii=[];unique={}
 for tri in me.loop_triangles:
  for li in tri.loops:
   p=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co);n=U(ob.matrix_world.to_3x3()@me.corner_normals[li].vector)
   t=[round(float(v),6)for v in me.uv_layers.active.data[li].uv];key=tuple(p+n+t)
   if key not in unique:unique[key]=len(vs);vs.append(p);ns.append(n);uv.append(t)
   ii.append(unique[key])
 data.append(dict(name=ob.name,family=ob['family'],group=ob['group'],material=ob['region'],positions=vs,normals=ns,uv=uv,indices=ii))
(O/'lamp-meshes.json').write_text(json.dumps(data,separators=(',',':')))
summary={}
for f in ['Post','Wall']:
 rows=[x for x in data if x['family']==f];v=[p for x in rows for p in x['positions']]
 summary[f]=dict(parts=len(rows),triangles=sum(len(x['indices'])//3 for x in rows),vertices=sum(len(x['positions'])for x in rows),minimum=[min(p[a]for p in v)for a in range(3)],maximum=[max(p[a]for p in v)for a in range(3)])
(O/'geometry-report.json').write_text(json.dumps(dict(source='Original Blender MCP authoring',units='metres',families=summary,materials=list(M),normal='Authored weighted corner normals; Unity installer reconstructs tangents from UV0',acceptance='Unreviewed runtime candidate, native day/night review required'),indent=2))
# Studio preview uses the same original material regions, not native acceptance.
for ob in objects:
 if ob['family']=='Wall':ob.location+=B((1.2,2.9,0))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004));floor=bpy.context.object;floor.name='Preview ground'
floor.data.materials.append(M['Base'])
world=bpy.data.worlds.new('Lamp studio') if not bpy.data.worlds.get('Lamp studio') else bpy.data.worlds['Lamp studio'];scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.13,.15,.19,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4
for name,p,power,size in [('Studio key',(3,6,4),1100,5),('Studio fill',(-4,3,2),700,4)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size;ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=B(p);ob.rotation_euler=(B((0,2.4,0))-ob.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Fixture review camera');cam=bpy.data.objects.new('Fixture review camera',camd);scene.collection.objects.link(cam);cam.location=B((5.4,3.3,7.8));cam.rotation_euler=(B((.4,2.25,.2))-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=53;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1100;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(O/'studio-full.png')
# Write only this new scene and its dependencies; preserve all other live Blender data.
bpy.data.libraries.write(str(O/'lamp-family.blend'), {scene}, fake_user=True, compress=True)
bpy.ops.render.render(write_still=True)
for name,p,target in [('base',(1.25,1.03,1.5),(0,.63,0)),('head',(1.2,4.34,2.2),(0,4.31,.36)),('wall',(2.5,3.3,1.8),(1.2,2.9,.3))]:
 cam.location=B(p);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=56
 scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.filepath=str(O/('studio-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(summary))
