"""Original Ward architecture. Execute ONLY through the live Blender MCP, with ownership.
Metres, Unity +Y up / +Z front. Source and authoring remain editable, separate from runtime.
"""
import bpy, bmesh, math, json, random, hashlib
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2'); O=R/'art/quality_20260909/relay-family'; O.mkdir(exist_ok=True,parents=True)
S=O/'revision-01'; S.mkdir(exist_ok=True)
scene=bpy.data.scenes.get('Ward Relay architecture') or bpy.data.scenes.new('Ward Relay architecture')
assert scene.get('ward_asset') in [None,'relay-architecture']
scene['ward_asset']='relay-architecture'; bpy.context.window.scene=scene
for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
rng=random.Random(9092601); objects=[]; M={}; tile={}; family='relay_works'; group='Shell'; proxies=[]
def B(p): return Vector((p[0],-p[2],p[1]))
def U(p): return [round(p.x,6),round(p.z,6),round(-p.y,6)]
def tex(m,p,socket,kind='color'):
 if not Path(p).exists(): raise FileNotFoundError(p)
 nt=m.node_tree; bs=nt.nodes.get('Principled BSDF'); n=nt.nodes.new('ShaderNodeTexImage'); n.image=bpy.data.images.load(str(p),check_existing=True)
 if kind!='color': n.image.colorspace_settings.name='Non-Color'
 if kind=='normal':
  nn=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(n.outputs['Color'],nn.inputs['Color']); nt.links.new(nn.outputs['Normal'],bs.inputs['Normal'])
 elif kind=='packed':
  sp=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(n.outputs['Color'],sp.inputs[0]);nt.links.new(sp.outputs['Red'],bs.inputs['Metallic'])
  inv=nt.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;nt.links.new(n.outputs['Alpha'],inv.inputs[1]);nt.links.new(inv.outputs[0],bs.inputs['Roughness'])
 else: nt.links.new(n.outputs['Color'],bs.inputs[socket])
 return n
for name,asset,scale,tint in [('WardPlaster','beige_wall_001',3,(1,1,1)),('WardStone','rock_surface',2,(1,1,1)),('WardConcrete','rough_concrete',1.23,(1,1,1)),('WardWornSteel','rusty_metal_sheet',2,(1,1,1))]:
 m=bpy.data.materials.new('Relay_'+name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*tint,1)
 base=R/'refs/quality_20260909/building-materials'/asset
 n=tex(m,base/(asset+'_diff_4k.png'),'Base Color')
 if tint!=(1,1,1):
  mult=m.node_tree.nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(*tint,1);m.node_tree.links.new(n.outputs['Color'],mult.inputs[1]);m.node_tree.links.new(mult.outputs[0],bs.inputs['Base Color'])
 tex(m,base/(asset+'_nor_gl_4k.png'),None,'normal');tex(m,base/(asset+'_rough_4k.png'),'Roughness','linear')
 bs.inputs['Metallic'].default_value=0 # Source is coated paint and rust, both dielectric.
 M[name]=m;tile[name]=scale
for name,src,col in [('WardPaint','Paint',(.25,.225,.19)),('WardSteel','Steel',(.32,.34,.34)),('WardBrass','Bronze',(.37,.285,.16)),('WardRubber','Rubber',(.047,.045,.041))]:
 m=bpy.data.materials.new('Relay_'+name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1)
 base=R/'art/quality_20260908/lamps/textures';tex(m,base/(src+'_BaseColor.png'),'Base Color');tex(m,base/(src+'_Normal.png'),None,'normal');tex(m,base/(src+'_MetalSmooth.png'),None,'packed')
 M[name]=m;tile[name]=.75
for name,col,rough,metal in [('WardCloth',(.26,.066,.034),.94,0),('WardGlass',(.024,.045,.048),.28,0),('WardLetter',(.64,.53,.32),.65,.45),('WardGasket',(.017,.014,.011),.94,0),('WardLampGlass',(.78,.47,.14),.35,0),('WardScale',(.23,.31,.40),.65,0)]:
 m=bpy.data.materials.new('Relay_'+name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if name=='WardCloth':
  base=R/'refs/quality_20260909/basic-general/materials/fabric_pattern_07';tex(m,base/'fabric_pattern_07_nor_gl_4k.jpg',None,'normal');tex(m,base/'fabric_pattern_07_rough_4k.jpg','Roughness','linear')
 if name=='WardLampGlass':bs.inputs['Emission Color'].default_value=(1,.56,.2,1);bs.inputs['Emission Strength'].default_value=.4
 M[name]=m;tile[name]=.4 if name=='WardCloth' else 1

def finish(ob,name,mat,bevel=0,offset=None):
 ob.name=family+' '+name;ob['family']=family;ob['group']=group;ob['region']=mat
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 if ob.type in ['CURVE','FONT']:bpy.ops.object.convert(target='MESH');ob=bpy.context.object
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=ob.modifiers.new('Intentional edge radius','BEVEL');mod.width=bevel;mod.segments=3;mod.affect='EDGES';bpy.ops.object.modifier_apply(modifier=mod.name)
 me=ob.data;me.materials.clear();me.materials.append(M[mat]);uv=me.uv_layers.active or me.uv_layers.new(name='UV0 physical tile')
 off=offset or (rng.uniform(0,11),rng.uniform(0,11));scale=tile[mat]
 for face in me.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]))
  for li in face.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co
   uv.data[li].uv=((v.y if axis==0 else v.x)/scale+off[0],(v.y if axis==2 else v.z)/scale+off[1])
  face.use_smooth=True
 mod=ob.modifiers.new('Construction normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 objects.append(ob);return ob

def box(name,p,size,mat='WardPaint',bevel=.008):
 bpy.ops.mesh.primitive_cube_add(size=1,location=B(p));ob=bpy.context.object;ob.dimensions=(size[0],size[2],size[1]);return finish(ob,name,mat,min(bevel,min(size)*.23))
def cyl(name,p,r,depth,mat='WardSteel',axis=(0,1,0),verts=32,r2=None,bevel=.002):
 bpy.ops.mesh.primitive_cone_add(vertices=verts,radius1=r,radius2=r if r2 is None else r2,depth=depth,location=B(p));ob=bpy.context.object
 ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(B(axis).normalized());return finish(ob,name,mat,min(bevel,depth*.2))
def tube(name,points,r=.022,mat='WardSteel',bevres=2):
 c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=1;c.bevel_depth=r;c.bevel_resolution=bevres
 sp=c.splines.new('POLY');sp.points.add(len(points)-1)
 for a,p in zip(sp.points,points):a.co=(*B(p),1)
 ob=bpy.data.objects.new(name,c);scene.collection.objects.link(ob);return finish(ob,name,mat)
def pipe(name,a,b,r=.035,mat='WardSteel'): return tube(name,[a,b],r,mat)
def bolt(name,p,axis=(0,0,1),r=.014):
 cyl(name+' washer',p,r*1.6,.003,'WardSteel',axis,verts=16,bevel=.0005)
 cyl(name+' hex',Vector(p)+Vector(axis)*.009,r,.015,'WardSteel',axis,verts=6,bevel=.001)
def ring(name,p,r,minor=.012,mat='WardSteel',axis=(0,0,1)):
 bpy.ops.mesh.primitive_torus_add(major_radius=r,minor_radius=minor,major_segments=32,minor_segments=8,location=B(p));ob=bpy.context.object;ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(B(axis).normalized());return finish(ob,name,mat)
def text(name,string,p,width,height,mat='WardLetter'):
 c=bpy.data.curves.new(name,'FONT');c.body=string;c.align_x='CENTER';c.align_y='CENTER';c.size=1;c.extrude=.002;c.bevel_depth=.0005;c.bevel_resolution=1;c.resolution_u=6
 font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf')
 if font.exists():c.font=bpy.data.fonts.load(str(font),check_existing=True)
 ob=bpy.data.objects.new(name,c);scene.collection.objects.link(ob);ob.location=B(p);ob.rotation_euler=(math.pi/2,0,0)
 bpy.context.view_layer.update();s=min(width/max(.001,ob.dimensions.x),height/max(.001,ob.dimensions.z));ob.scale=(s,s,s);return finish(ob,name,mat)
def plate(name,p,size,mat='WardPaint',fasten=True):
 box(name,p,size,mat,.014)
 if fasten:
  for x in [-1,1]:
   for y in [-1,1]:bolt(name+f' {x} {y}',(p[0]+x*(size[0]/2-.065),p[1]+y*(size[1]/2-.065),p[2]+size[2]/2+.002),r=.011)
def proxy(name,p,size): proxies.append(dict(family=family,name=name,center=list(p),size=list(size)))
def masonry_pier(name,x,z,width,depth,height):
 rows=math.ceil(height/.56)
 for row in range(rows):
  h=min(.56,height-row*.56)-.018
  if h<=0:continue
  box(name+f' stone {row}',(x,row*.56+h*.5,z),(width,h,depth),'WardStone',.022)
def louver(name,p,width,height,depth=.22,axis='front'):
 # All geometry is authored as a front-facing cassette; complete cassette can rotate as a unit.
 start=len(objects)
 plate(name+' recessed back',(p[0],p[1],p[2]-.04),(width,height,.07),'WardGasket',False)
 for sx in [-1,1]:box(name+' jamb '+str(sx),(p[0]+sx*(width/2-.03),p[1],p[2]+.01),(.06,height+.10,depth),'WardPaint',.006)
 for sy in [-1,1]:box(name+' rail '+str(sy),(p[0],p[1]+sy*(height/2+.02),p[2]+.01),(width+.06,.07,depth),'WardPaint',.006)
 n=max(3,round(height/.12))
 for i in range(n):
  ob=box(name+f' blade {i}',(p[0],p[1]-height/2+(i+.5)*height/n,p[2]+.055),(width-.08,.065,.13),'WardPaint',.003);ob.rotation_euler.x=math.radians(18)
 for sx in [-1,1]:
  for sy in [-1,1]:bolt(name+f' flange {sx} {sy}',(p[0]+sx*(width/2-.02),p[1]+sy*(height/2+.02),p[2]+depth/2+.015),r=.009)
 if axis!='front':
  angle=-math.pi/2 if axis=='left' else math.pi/2
  # Rotation around intended cassette centre in Unity space.
  center=B(p);rot=__import__('mathutils').Matrix.Rotation(angle,4,'Z')
  for ob in objects[start:]:ob.matrix_world=__import__('mathutils').Matrix.Translation(center)@rot@__import__('mathutils').Matrix.Translation(-center)@ob.matrix_world

def door(name,x,z,width=1.7,height=2.3):
 global group
 group='Entrance'
 # Masonry reveal is a 0.30m deep cavity with distinct inset door and rubber seals.
 for sx in [-1,1]:
  box(name+f' masonry reveal {sx}',(x+sx*(width/2+.15),height/2,z+.10),(.30,height,.52),'WardStone',.018)
  box(name+f' steel jamb {sx}',(x+sx*(width/2-.025),height/2,z+.015),(.09,height,.22),'WardPaint',.007)
 box(name+' header',(x,height+.12,z+.10),(width+.60,.24,.56),'WardStone',.022)
 box(name+' head seal',(x,height-.035,z+.008),(width,.07,.20),'WardGasket',.003)
 box(name+' threshold',(x,.028,z+.18),(width+.28,.056,.63),'WardConcrete',.009)
 for leaf,sx in enumerate([-1,1]):
  w=width/2-.045;cx=x+sx*width/4
  box(name+f' leaf {leaf}',(cx,height/2,z-.085),(w,height-.07,.10),'WardPaint',.012)
  box(name+f' leaf seal {leaf}',(cx,height/2,z-.065),(w+.025,height-.038,.035),'WardGasket',.003)
  box(name+f' inset inner {leaf}',(cx,height/2,z-.038),(w-.035,height-.11,.035),'WardPaint',.008)
  for yy,hh in [(.49,.58),(1.49,.91)]:
   box(name+f' stamped panel {leaf} {yy}',(cx,yy,z-.008),(w-.16,hh,.026),'WardSteel',.012)
  box(name+f' kick plate {leaf}',(cx,.175,z+.014),(w-.055,.20,.018),'WardWornSteel',.004)
  for yy in [.26,1.09,2.03]:
   hx=cx+sx*(w/2-.015);box(name+f' hinge strap {leaf} {yy}',(hx-sx*.045,yy,z+.013),(.13,.075,.025),'WardSteel',.003)
   cyl(name+f' hinge barrel {leaf} {yy}',(hx,yy,z+.032),.032,.15,'WardSteel',verts=20)
   for by in [-.04,.04]:bolt(name+f' hinge bolt {leaf} {yy} {by}',(hx-sx*.075,yy+by,z+.03),r=.008)
  hx=x+sx*.105
  box(name+f' handle escutcheon {leaf}',(hx,1.05,z+.024),(.115,.36,.034),'WardSteel',.007)
  tube(name+f' pull handle {leaf}',[(hx,.96,z+.044),(hx,.98,z+.12),(hx,1.19,z+.12),(hx,1.21,z+.044)],.017,'WardBrass')
 proxy(name+' closed door',(x,height/2,z-.085),(width,height,.16))
 group='Shell'

def canopy(width=5.9,front=4.25,rear=2.72,height=2.80):
 global group
 group='Awning'
 # Sewn cloth sag runs between continuous front/rear tubes, ends pinned in reinforced pockets.
 nx=48;nz=24;vs=[];faces=[]
 for j in range(nz+1):
  t=j/nz;z=rear+(front-rear)*t
  for i in range(nx+1):
   u=i/nx;x=(u-.5)*width
   y=height+.38*(1-t)-.10*math.sin(math.pi*t)+.023*math.sin(u*math.pi*12)*math.sin(math.pi*t)
   vs.append(B((x,y,z)))
 for j in range(nz):
  for i in range(nx):a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
 me=bpy.data.meshes.new('Sewn canvas');me.from_pydata(vs,[],faces);me.update();ob=bpy.data.objects.new('Sewn canvas',me);scene.collection.objects.link(ob);ob=finish(ob,'Tensioned red cloth','WardCloth')
 sol=ob.modifiers.new('Woven fabric thickness','SOLIDIFY');sol.thickness=.004;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=sol.name)
 for z,y in [(rear,height+.38),(front,height)]:pipe('Canvas pocket rail '+str(z),(-width/2-.08,y,z),(width/2+.08,y,z),.029,'WardPaint')
 for xx in [-width/2,width/2]:
  plate('Wall anchor plate '+str(xx),(xx,height+.31,rear-.035),(.20,.29,.09),'WardPaint')
  pipe('Awning diagonal arm '+str(xx),(xx,2.15,rear),(xx,height,front),.032,'WardSteel')
  pipe('Awning upper arm '+str(xx),(xx,height+.30,rear),(xx,height,front),.025,'WardSteel')
  cyl('Clevis pivot '+str(xx),(xx,height,front),.053,.09,'WardSteel',axis=(1,0,0),verts=24)
 # Reinforced seam strips follow actual cloth surface at 3 panel joins.
 for xx in [-width/4,0,width/4]:
  pts=[]
  for j in range(nz+1):
   t=j/nz;u=xx/width+.5;y=height+.38*(1-t)-.10*math.sin(math.pi*t)+.023*math.sin(u*math.pi*12)*math.sin(math.pi*t)
   pts.append((xx,y+.005,rear+(front-rear)*t))
  tube('Sewn seam '+str(xx),pts,.006,'WardCloth',1)
 # Short weighted valance is separate sewn material with folded hem, not a paper edge.
 for i in range(12):
  x=(i-5.5)*width/12;box('Valance cloth '+str(i),(x,height-.09,front+.008),(width/12+.005,.18,.006),'WardCloth',.001)
 tube('Weighted hem',[(-width/2,height-.18,front+.012),(width/2,height-.18,front+.012)],.009,'WardCloth',1)
 group='Shell'

def make_relay():
 global group
 # Occupied body spans z=-4.4..+2.70, leaving existing front porch clear.
 W=7.50; back=-4.30; face=2.67; roof=6.75
 group='Shell'
 box('Interior back wall',(0,3.25,back),(W,6.5,.28),'WardPlaster',.018);proxy('Back wall',(0,3.25,back),(W,6.5,.28))
 for sx in [-1,1]:
  box('Side masonry wall '+str(sx),(sx*(W/2-.14),3.25,(back+face)/2),(.28,6.5,face-back),'WardPlaster',.018);proxy('Side wall '+str(sx),(sx*(W/2-.14),3.25,(back+face)/2),(.28,6.5,face-back))
  for zz in [back+.16,face-.12]:masonry_pier('Bonded corner '+str(sx)+' '+str(zz),sx*(W/2-.19),zz,.48,.53,6.5)
 # Front ground infill flanks preserve a true inset door assembly at the unchanged centre.
 for sx in [-1,1]:
  box('Ground front structure '+str(sx),(sx*2.33,1.58,face-.10),(2.88,3.16,.30),'WardPlaster',.012);proxy('Ground front '+str(sx),(sx*2.34,1.58,face-.10),(2.94,3.16,.30))
  for x in [sx*1.48,sx*2.47]:
   plate('Repairable lower cassette '+str(x),(x,1.50,face+.055),(.94,2.12,.075),'WardPaint')
  masonry_pier('Entry pier '+str(sx),sx*1.02,face+.085,.36,.56,2.55)
 door('Workshop double entry',0,face-.02)
 box('Door transom infill',(0,2.87,face-.10),(1.82,.66,.30),'WardPlaster',.01);proxy('Door transom infill',(0,2.89,face-.10),(1.74,1.18,.30))
 # Outer sandstone plinth, shallow per-block bevels rather than enormous inflated edges.
 group='Footing'
 for sx in [-1,1]:
  for i in range(6):
   zz=back+.55+i*1.12;box('Side base course '+str(sx)+' '+str(i),(sx*3.57,.22,zz),(.43,.43,1.095),'WardStone',.023)
  for i in range(3):box('Front base course '+str(sx)+' '+str(i),(sx*(1.43+i*.82),.22,face+.12),(.795,.43,.47),'WardStone',.022)
 for i in range(7):box('Rear base course '+str(i),((i-3)*1.06,.22,back-.06),(1.035,.43,.45),'WardStone',.021)
 # Floor slab, upper wall pierced by two correctly proportioned recessed windows.
 group='Upper construction'
 box('Upper floor slab',(0,3.32,-.78),(7.68,.25,7.26),'WardConcrete',.019)
 # Front wall broken around actual window cavities; no inset plane floating over an uninterrupted wall.
 windows=[-2.15,2.15];winw=1.32;winbottom=4.25;wintop=5.68
 for x,w in [(-3.28,.94),(0,2.98),(3.28,.94)]:box('Upper front pier '+str(x),(x,4.91,face-.10),(w,3.03,.28),'WardPlaster',.015)
 for xx in windows:
  box('Window sill wall '+str(xx),(xx,(3.45+winbottom)/2,face-.10),(winw+.12,winbottom-3.45,.28),'WardPlaster',.012)
  box('Window lintel wall '+str(xx),(xx,(wintop+6.43)/2,face-.10),(winw+.12,6.43-wintop,.28),'WardPlaster',.012)
  box('Window inset glass '+str(xx),(xx,(winbottom+wintop)/2,face-.22),(winw-.16,wintop-winbottom-.16,.05),'WardGlass',.004)
  for sx in [-1,1]:box('Window deep jamb '+str(xx)+' '+str(sx),(xx+sx*winw/2,(winbottom+wintop)/2,face-.03),(.15,wintop-winbottom+.18,.39),'WardStone',.010)
  for yy in [winbottom,wintop]:box('Window sill/head '+str(xx)+' '+str(yy),(xx,yy,face+.04),(winw+.27,.14,.44),'WardStone',.014)
  box('Window steel mullion '+str(xx),(xx,(winbottom+wintop)/2,face-.16),(.048,wintop-winbottom,.11),'WardPaint',.003)
  box('Window transom '+str(xx),(xx,winbottom+.98,face-.16),(winw,.045,.11),'WardPaint',.003)
  # Closed lower shade vanes permit visible glass above, industrial/human-scale construction.
  louver('Window half blind '+str(xx),(xx,winbottom+.38,face-.02),winw-.20,.53,.13)
 proxy('Upper front',(0,4.91,face-.10),(7.5,3.03,.28))
 # Intermediate wall fastened trim channels and proper narrow stone coping, with masonry joints.
 for yy in [3.47,6.49]:
  for i in range(8):
   box('Front stone coping '+str(yy)+' '+str(i),((i-3.5)*.96,yy,face+.075),(.939,.20,.45),'WardStone',.012)
   box('Rear stone coping '+str(yy)+' '+str(i),((i-3.5)*.94,yy,back-.03),(.919,.20,.43),'WardStone',.012)
  for sx in [-1,1]:
   for i in range(7):box('Side coping '+str(yy)+' '+str(sx)+' '+str(i),(sx*3.69,yy,-3.8+i*.97),(.43,.20,.945),'WardStone',.012)
 # Roof is a usable edged slab and short parapet, no broad unbuildable stacked lip.
 group='Roof'
 box('Roof deck',(0,6.64,-.82),(7.5,.20,7.02),'WardConcrete',.017);proxy('Roof deck',(0,6.64,-.82),(7.5,.20,7.02))
 for sx in [-1,1]:box('Side parapet '+str(sx),(sx*3.57,6.96,-.82),(.30,.46,6.9),'WardPlaster',.014)
 box('Back parapet',(0,6.96,-4.16),(7.20,.46,.30),'WardPlaster',.014)
 box('Front parapet',(0,6.90,2.46),(7.20,.34,.28),'WardPlaster',.014)
 for sx in [-1,1]:
  for i in range(7):box('Parapet cap '+str(sx)+' '+str(i),(sx*3.57,7.20,-3.75+i*.98),(.43,.13,.958),'WardStone',.01)
 for zz,yy in [(-4.16,7.20),(2.46,7.08)]:
  for i in range(7):box('Parapet end cap '+str(zz)+' '+str(i),((i-3)*1.02,yy,zz),(1,.13,.43),'WardStone',.01)
 # Relay equipment has legs, vented skin and attached mast/cable -- silhouette with a reason.
 for xx in [-.82,.82]:
  for zz in [-1.70,-.20]:
   box('Relay equipment roof foot '+str(xx)+' '+str(zz),(xx,6.81,zz),(.32,.16,.32),'WardConcrete',.008)
   box('Equipment leg '+str(xx)+' '+str(zz),(xx,6.99,zz),(.09,.22,.09),'WardSteel',.004)
 box('Roof relay cabinet',(0,7.38,-.95),(1.85,.65,1.82),'WardPaint',.025)
 for xx in [-.5,.5]:louver('Roof cabinet front '+str(xx),(xx,7.39,-.015),.71,.43,.10)
 box('Equipment rain hood',(0,7.76,-.95),(2.02,.09,1.97),'WardWornSteel',.009)
 cyl('Antenna mast base',(1.50,6.78,-2.30),.16,.12,'WardSteel',verts=32)
 cyl('Antenna mast',(1.50,7.43,-2.30),.042,1.23,'WardSteel',verts=24)
 for yy in [7.34,7.62,7.9]:pipe('Relay dipole '+str(yy),(1.09,yy,-2.30),(1.91,yy,-2.30),.014,'WardSteel')
 tube('Roof power cable',[(1.50,6.82,-2.3),(1.45,6.75,-1.7),(.90,6.75,-1.3),(.89,7.24,-1.3)],.022,'WardRubber')
 # Door/upper sign is deliberately separate lettering on a framed panel at a readable human-scale height.
 group='Signage'
 plate('Trade sign backing',(0,3.80,face+.125),(5.65,.58,.12),'WardPaint')
 box('Trade sign inset',(0,3.80,face+.198),(5.36,.39,.04),'WardGasket',.004)
 text('Trade name','RELAY WORKS',(0,3.80,face+.23),4.95,.29)
 # Tiny auxiliary plate: lower-density information without a wall covered in giant symbols.
 plate('Service label',(2.40,2.57,face+.13),(1.23,.28,.035),'WardPaint',False)
 text('Service label lettering','REPAIR  /  ROUTE',(2.40,2.57,face+.151),1.06,.095)
 canopy()
 # Functional services: right wall downpipe, front grounded junction unit and supported bundles.
 group='Services'
 x=3.82;z=1.73
 pipe('Rain downpipe',(x,.31,z),(x,6.95,z),.065,'WardBrass')
 for y in [.80,2.15,3.63,5.18,6.50]:
  box('Pipe wall stand-off '+str(y),(3.73,y,z),(.18,.09,.15),'WardPaint',.003)
  ring('Pipe retaining band '+str(y),(x,y,z),.070,.008,'WardSteel',axis=(0,1,0))
  bolt('Pipe band bolt '+str(y),(3.88,y,z+.025),axis=(1,0,0),r=.01)
 tube('Rain shoe',[(x,.31,z),(x,.18,z+.12),(x,.18,z+.38)],.065,'WardBrass')
 # Front conduit terminates inside actual gland at junction top; saddles attach to the backing wall.
 plate('Utility box backplate',(-2.84,1.37,face+.18),(.47,.79,.09),'WardSteel')
 box('Utility sealed cabinet',(-2.84,1.38,face+.315),(.35,.58,.23),'WardPaint',.018)
 box('Utility door lip',(-2.84,1.38,face+.444),(.32,.53,.026),'WardSteel',.006)
 box('Utility lock',(-2.72,1.36,face+.465),(.045,.08,.023),'WardBrass',.003)
 cyl('Upper gland',(-2.84,1.75,face+.30),.037,.12,'WardSteel',verts=20)
 tube('Utility conduit',[(-2.84,1.77,face+.30),(-2.84,2.30,face+.30),(-2.86,2.42,face+.29),(-3.16,2.61,face+.29),(-3.16,6.4,face+.29)],.020,'WardSteel')
 for y in [2.84,3.30,4.22,5.22,6.16]:
  box('Conduit saddle plate '+str(y),(-3.16,y,face+.10),(.14,.105,.19),'WardPaint',.003)
  ring('Conduit saddle '+str(y),(-3.16,y,face+.29),.025,.006,'WardSteel',axis=(0,1,0))
  for sx in [-1,1]:bolt('Conduit saddle bolt '+str(y)+' '+str(sx),(-3.16+sx*.047,y,face+.20),r=.007)
 # Caged entrance practical attaches to its own service plate with an enclosed feed.
 group='Entrance light'; lx=1.25; ly=1.83; lz=face+.29
 plate('Entrance lamp backplate',(lx,ly,lz-.18),(.22,.50,.10),'WardPaint')
 pipe('Entrance lamp mounting arm',(lx,ly+.16,lz-.11),(lx,ly+.16,lz+.10),.025,'WardSteel')
 cyl('Lamp frosted glass',(lx,ly,lz+.11),.082,.28,'WardLampGlass',verts=32,bevel=.009)
 cyl('Lamp rain cap',(lx,ly+.17,lz+.11),.13,.07,'WardPaint',verts=32,r2=.09,bevel=.009)
 cyl('Lamp bottom cap',(lx,ly-.17,lz+.11),.105,.05,'WardPaint',verts=32,bevel=.006)
 for j in range(6):
  a=j*math.pi/3;px=lx+math.cos(a)*.10;pz=lz+.11+math.sin(a)*.10
  pipe('Lamp cage '+str(j),(px,ly-.15,pz),(px,ly+.14,pz),.006,'WardSteel')
 ring('Lamp cage band',(lx,ly-.04,lz+.11),.105,.007,'WardSteel',axis=(0,1,0))
 group='Services'
 # Rear service hatch and cross-wall utility run prevent a blank stretched back.
 group='Rear services'
 # Rotate front-style cassette 180° so all rear hardware genuinely faces out.
 start=len(objects)
 plate('Rear access door',(1.58,1.13,4.44),(1.10,1.80,.08),'WardPaint')
 louver('Rear ventilation',(1.58,2.44,4.45),1.16,.43,.13)
 for yy in [.70,1.52]:box('Rear service hinge '+str(yy),(2.08,yy,4.53),(.12,.18,.07),'WardSteel',.005)
 box('Rear access handle',(1.15,1.16,4.54),(.055,.21,.055),'WardSteel',.006)
 for ob in objects[start:]:ob.matrix_world=__import__('mathutils').Matrix.Rotation(math.pi,4,'Z')@ob.matrix_world
 # Side window cassettes complete both side elevations at useful floor heights.
 group='Side services'
 for sx in [-1,1]:
  for zz in [-2.28,.10]:
   louver('Side vent '+str(sx)+' '+str(zz),(sx*3.78,4.86,zz),1.36,.66,.13,'left' if sx<0 else 'right')
  # Rear service pipe rises to roof from a real base flanged foot.
  px=sx*3.84;pz=-3.53
  pipe('Rear riser '+str(sx),(px,.35,pz),(px,6.74,pz),.043,'WardSteel')
  for yy in [.45,2.2,4.1,6.28]:
   box('Rear riser anchor '+str(sx)+' '+str(yy),(sx*3.75,yy,pz),(.15,.09,.14),'WardPaint',.003)
   ring('Riser clamp '+str(sx)+' '+str(yy),(px,yy,pz),.048,.007,'WardBrass',axis=(0,1,0))
make_relay()
# Export every loop-corner normal/UV seam correctly, positions transformed into Unity metre coordinates.
data=[]
for ob in objects:
 me=ob.data;me.calc_loop_triangles();vs=[];ns=[];uv=[];ii=[];unique={};normalmat=ob.matrix_world.to_3x3().inverted().transposed();uvl=me.uv_layers.active.data
 for tri in me.loop_triangles:
  for li in tri.loops:
   loop=me.loops[li];p=U(ob.matrix_world@me.vertices[loop.vertex_index].co);n=U((normalmat@me.corner_normals[li].vector).normalized());t=[round(float(v),6)for v in uvl[li].uv];key=tuple(p+n+t)
   if key not in unique:unique[key]=len(vs);vs.append(p);ns.append(n);uv.append(t)
   ii.append(unique[key])
 data.append(dict(name=ob.name,family=ob['family'],group=ob['group'],material=ob['region'],positions=vs,normals=ns,uv=uv,indices=ii))
(S/'relay-meshes.json').write_text(json.dumps(data,separators=(',',':')))
(S/'collider-proxies.json').write_text(json.dumps(proxies,indent=2))
verts=[p for part in data for p in part['positions']]
report=dict(source='Original Blender authoring through live MCP',units='metres',front='+Z',pivot='bottom center',family=family,parts=len(data),triangles=sum(len(x['indices'])//3 for x in data),vertices=sum(len(x['positions'])for x in data),minimum=[min(p[a]for p in verts)for a in range(3)],maximum=[max(p[a]for p in verts)for a in range(3)],materials={k:dict(physicalTileMetres=tile[k])for k in M},nativeStatus='Uninstalled, unreviewed; source render is not native acceptance',sourceDrawCost='Editable components; merge by spatial material groups during Unity render-chunk rebuild',runtimeLODs='No destructive source reduction; first-source audition uses authored near mesh. Distance LOD qualification follows source/native acceptance.')
(S/'geometry-report.json').write_text(json.dumps(report,indent=2))
# Studio floor and a 1.8m measured human scale stand aside from the doorway.
group='Review only';family='review'
box('Scale plinth',(-4.60,.025,3.4),(.45,.05,.45),'WardScale',.005)
box('1.8m scale bar',(-4.60,.92,3.4),(.065,1.75,.065),'WardScale',.005)
for yy in [.5,1,1.5,1.8]:box('Scale tick '+str(yy),(-4.60,yy,3.4),(.27,.017,.04),'WardLetter',.002)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.025));floor=bpy.context.object;floor.name='Relay preview floor';floor.data.materials.append(M['WardConcrete'])
# Set floor UV physical size rather than an enormous stretched image.
for f in floor.data.polygons:
 for li in f.loop_indices:
  v=floor.data.vertices[floor.data.loops[li].vertex_index].co;floor.data.uv_layers.active.data[li].uv=(v.x/1.23,v.y/1.23)
world=bpy.data.worlds.get('Relay review world') or bpy.data.worlds.new('Relay review world');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.20,.26,.36,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45
sun=bpy.data.lights.new('Relay warm sun','SUN');sun.energy=3;sun.angle=math.radians(1.2);sun.color=(1,.86,.69);ob=bpy.data.objects.new('Relay warm sun',sun);scene.collection.objects.link(ob);ob.rotation_euler=(math.radians(35),math.radians(-25),math.radians(-28))
ld=bpy.data.lights.new('Relay sky bounce','AREA');ld.energy=1600;ld.shape='DISK';ld.size=12;ob=bpy.data.objects.new('Relay sky bounce',ld);scene.collection.objects.link(ob);ob.location=B((-7,7,9));ob.rotation_euler=(B((0,3,0))-ob.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Relay source review camera');cam=bpy.data.objects.new('Relay source review camera',camd);scene.collection.objects.link(cam);scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
views=[('front',(0,1.75,18.7),(0,3.35,.0),43),('door',(1.2,1.70,5.1),(0,1.40,2.64),36),('door-left',(-2.3,1.55,4.15),(0,1.35,2.64),35),('door-right',(2.3,1.55,4.15),(0,1.35,2.64),35),('left',(-12,3.2,-.5),(0,3.1,-.5),39),('right',(12,3.2,-.5),(0,3.1,-.5),39),('back',(-7,2.3,-14),(0,3,-1.0),43),('awning',(4.3,1.70,5.7),(2.05,2.85,3.10),33),('roof',(7.3,9.4,11.3),(0,5.9,-.3),40)]
(S/'review-cameras.json').write_text(json.dumps([dict(name=n,position=p,target=t,lens=l)for n,p,t,l in views],indent=2))
bpy.data.libraries.write(str(S/'relay-architecture.blend'),{scene},fake_user=True,compress=True)
for name,p,target,lens in views[:1]:
 cam.location=B(p);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=lens;scene.render.filepath=str(S/('source-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(report))
