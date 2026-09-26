"""Live Blender source revision: continuous base and positive service cage joints.
Preserves the first authored .blend and retains revised objects hidden in scene.
"""
import bpy,math,json,ast,bmesh
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('/home/teknetik/code/ao2');O=R/'meshy/ground-detail-20260910/generator-v3-source'
assert not (O/'generator-v3-service-construction-v2.blend').exists()
S=bpy.data.scenes['Generator v3 side service authoring'];bpy.context.window.scene=S
C=bpy.data.collections['Generator v3 editable source parts'];core=bpy.data.objects['GENERATOR_V3_RETAINED_CORE'];parts=[];ports=[]
paint=bpy.data.materials['Service tank ochre paint'];steel=bpy.data.materials['Service cradle dark painted steel'];edge=bpy.data.materials['Service hardware exposed steel'];copper=bpy.data.materials['Service cooling tube copper'];rubber=bpy.data.materials['Service hoses and gaskets rubber'];brass=bpy.data.materials['Service pipe unions dull brass'];wear=bpy.data.materials['Localized ochre rub-through']
s=(R/'art/reference_street_20260910/author_generator_v3_service.py').read_text()
for f in ast.parse(s).body:
 if isinstance(f,ast.FunctionDef):exec(compile(ast.Module(body=[f],type_ignores=[]),str(O),'exec'))
retired=[]
def retire(o):
 retired.append(o.name);o.hide_render=True;o.hide_set(True);o.name='Retained service-v1 '+o.name
# Closed dense elliptical tank end caps, same overall design envelope.
old=bpy.data.objects['Strapped ochre service tank'];retire(old)
profile=[]
for i in range(25):
 a=(math.pi/2)*(1-i/24);profile.append((-.303-.071*math.sin(a),.115*math.cos(a)))
profile.append((.303,.115))
for i in range(1,25):
 a=math.pi/2*i/24;profile.append((.303+.071*math.sin(a),.115*math.cos(a)))
vs=[];fs=[];rings=[]
for y,r in profile:
 if r<1e-7:rings.append([len(vs)]);vs.append((.775,y,.80))
 else:
  rings.append(list(range(len(vs),len(vs)+96)))
  vs.extend([(.775+r*math.cos(t*math.tau/96),y,.80+r*math.sin(t*math.tau/96))for t in range(96)])
for a,b in zip(rings,rings[1:]):
 if len(a)==1:fs.extend([(a[0],b[(i+1)%96],b[i])for i in range(96)])
 elif len(b)==1:fs.extend([(a[i],a[(i+1)%96],b[0])for i in range(96)])
 else:fs.extend([(a[i],a[(i+1)%96],b[(i+1)%96],b[i])for i in range(96)])
def meshpart(name,vs,fs,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);S.collection.objects.link(o);own(o,name,mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 return o
o=meshpart('Smooth domed service tank',vs,fs,paint)
for p in o.data.polygons:p.use_smooth=True
# Positive tie/cage intersections, load-spreading sleeves and welded gussets.
for o in list(C.objects):
 if o.name.startswith('Cradle tie ('):retire(o)
for y in (-.17,.17):
 for z in (.16,.655):
  a=Vector((.585,y,z));b=Vector((.915,math.copysign(.414,y),z));axis=(b-a).normalized()
  cylinder('Joined cradle outrigger '+str((y,z)),a,b,.021,steel,48,.001)
  cylinder('Outrigger load sleeve '+str((y,z)),b-axis*.069,b+axis*.012,.028,steel,48,.0015)
  ring('Sleeve circumferential weld '+str((y,z)),b-axis*.068,axis,.028,.0014,wear)
  # A triangular 6 mm gusset joins side tube to the incoming load sleeve.
  u=axis;v=Vector((0,0,1 if z<.3 else -1));n=u.cross(v).normalized();p=b-u*.012
  tri=[p-u*.11,p+u*.008,p+v*.073];gv=[q+n*t for t in (-.003,.003)for q in tri]
  gf=[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)]
  g=meshpart('Welded outrigger gusset '+str((y,z)),gv,gf,steel);bevel(g,.001,2)
# Two continuous horizontal runners overlap the existing core base and outer skid.
for y in (-.370,.370):
 box('Core-to-service continuous base runner '+str(y),(.727,y,.067),(.405,.080,.083),steel,.005)
 box('Base runner endplate '+str(y),(.536,y,.067),(.013,.084,.087),edge,.002)
 for x in (.595,.884):bolt('Continuous base fixing '+str((x,y)),(x,y,.113),(0,0,1),.008)
# A pressed lower tray joins the runners and outer skid, with drain access preserved.
box('Joined service base tray',(.727,0,.072),(.398,.672,.016),steel,.004)
for y in (-.316,.316):box('Tray return lip '+str(y),(.727,y,.092),(.380,.012,.038),steel,.003)
# Replace sparse cooler with a deeper continuous four-pass pack and formed carrier.
for o in list(C.objects):
 if o.name.startswith(('Continuous four-run copper','Cooling coil restraint','Cooling restraint mounting','Cooling restraint bolt','Cooling lower union','Routed cooling return hose')):retire(o)
coil=[];xc=.887;end=.314;spacing=.085;top=.612
for row in range(4):
 z=top-row*spacing;left=-end if row%2==0 else end;right=-left
 if not coil:coil.append((xc,left,z))
 coil.append((xc,right,z))
 if row<3:
  for i in range(1,33):
   a=math.pi*i/32;coil.append((xc,right+(1 if right>0 else -1)*(spacing/2)*math.sin(a),z-spacing/2+(spacing/2)*math.cos(a)))
pipe('Continuous four-pass cooler construction v2',coil,.012,copper)
for y in (-.225,.225):
 box('Formed cooling pack carrier '+str(y),(.859,y,.486),(.022,.042,.348),steel,.002)
 box('Cooling pack restraint '+str(y),(.903,y,.485),(.009,.026,.335),edge,.001)
 for z in (.328,.643):
  box('Cooling pack closed standoff '+str((y,z)),(.882,y,z),(.058,.040,.020),steel,.0015)
  bolt('Cooling pack carrier fastener '+str((y,z)),(.917,y,z),(1,0,0),.006)
  # The carrier loads transfer into the base and tank rail rather than floating.
 cylinder('Cooler base support '+str(y),(.858,y,.106),(.858,y,.330),.015,steel,32,.001)
 box('Cooler support base shoe '+str(y),(.858,y,.115),(.060,.057,.014),steel,.002)
 bolt('Cooler base shoe bolt '+str(y),(.855,y,.126),(0,0,1),.006)
p=Vector(coil[-1]);axis=Vector((0,-1,0));cylinder('Cooling lower union v2',p-axis*.005,p+axis*.023,.016,brass,6,.001);ring('Cooling lower seal v2',p+axis*.025,axis,.0127,.0018,rubber)
# Reuse the saved actual engine attachment, changing only the service-side routing.
manifest=json.loads((O/'authoring-manifest-v3.json').read_text());ap=next(p for p in manifest['attachments'] if p['name']=='Cooling return');port=Vector(ap['queriedSurfacePoint'])+Vector(ap['surfaceNormal'])*.047
hose('Routed cooling return hose v2',[(.887,-.340,.357),(.875,-.385,.302),(.79,-.28,.252),(.73,.20,.258),port+Vector((.07,.05,-.005)),port])
bpy.context.view_layer.update();active=[o for o in C.objects if o.type=='MESH' and not o.hide_render];points=[o.matrix_world@Vector(c)for o in active for c in o.bound_box];lo=Vector(tuple(min(p[i]for p in points)for i in range(3)));hi=Vector(tuple(max(p[i]for p in points)for i in range(3)))
assert hi.x-lo.x<=1.6+1e-5 and hi.y-lo.y<=.95+1e-5 and hi.z-lo.z<=1.1+1e-5
for o in active:o.data.calc_loop_triangles()
record={'revision':'generator-v3-source construction-v2','boundsBlender':[list(lo),list(hi)],'sizeUnityXYZ':[hi.x-lo.x,hi.z-lo.z,hi.y-lo.y],'activeSourceTriangles':sum(len(o.data.loop_triangles)for o in active),'activeObjects':len(active),'retiredSourceObjects':retired,'originalCoreUnchanged':True,'sourceAccepted':False,'nativeAccepted':False,'changes':['24 profile intervals per tank end instead of six; same dimensions','Four ties now terminate at guard centreline with sleeves, welded gussets and positive overlap','Two runners and pressed tray connect outer skid to the core base','Deeper four-pass copper pack with load-bearing carrier and base supports','Return hose rerouted to original verified engine connection']}
(O/'construction-v2.json').write_text(json.dumps(record,indent=2)+'\n');bpy.data.libraries.write(str(O/'generator-v3-service-construction-v2.blend'),{S},fake_user=True,path_remap='RELATIVE');print(json.dumps(record))
