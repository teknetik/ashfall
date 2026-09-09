"""Original measured Basic General architecture. Execute through live Blender MCP.

All public coordinates are Unity metres relative to (8,.5,15.1), front +Z.
Only this new Blender scene is authored. Existing city and source files are untouched.
"""
import bpy, math, random, json, hashlib
from pathlib import Path
from mathutils import Vector

R=Path('/home/teknetik/code/ao2'); O=R/'art/quality_20260909/basic-general'
scene=bpy.data.scenes.get('Basic General architectural repair')
if scene is not None:
    raise RuntimeError('Preserve existing source; create a deliberate versioned revision instead of rerunning authoring.')
scene=bpy.data.scenes.new('Basic General architectural repair');bpy.context.window.scene=scene
rng=random.Random(909401);parts=[];M={};materials=[]

def B(p): return Vector((p[0],-p[2],p[1]))
def U(p): return [round(p.x,7),round(p.z,7),round(-p.y,7)]
def image(path,data=False):
    im=bpy.data.images.load(str(path),check_existing=True)
    if data: im.colorspace_settings.name='Non-Color'
    return im
def material(name,col=(1,1,1),tile=1,rough=.65,metal=0,base=None,normal=None,roughmap=None,packed=None):
    m=bpy.data.materials.new('General '+name);m.use_nodes=True;m['ward_slot']=name;m['tile_metres']=tile
    m.diffuse_color=(*col,1);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    def tex(path,data=False):
        t=n.new('ShaderNodeTexImage');t.image=image(path,data);return t
    if base:
        t=tex(base);mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*col,1);l.new(t.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
    if normal:
        t=tex(normal,True);nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.65 if name.startswith('WardStone') else .55;l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    if roughmap:l.new(tex(roughmap,True).outputs['Color'],p.inputs['Roughness'])
    if packed:
        t=tex(packed,True);sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Red'],p.inputs['Metallic']);inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;l.new(t.outputs['Alpha'],inv.inputs[1]);l.new(inv.outputs[0],p.inputs['Roughness'])
    M[name]=m;materials.append({'slot':name,'tileMetres':tile,'tint':list(col),'base':str(base)if base else None,'normal':str(normal)if normal else None,'roughness':str(roughmap)if roughmap else rough,'metal':metal,'metalSmooth':str(packed)if packed else None});return m

library=R/'refs/quality_20260909/building-materials'
for slot,asset,tile in [('WardStone','rock_surface',2),('WardPlaster','beige_wall_001',3),('WardConcrete','rough_concrete',1.23)]:
    a=library/asset;material(slot,tile=tile,base=a/(asset+'_diff_4k.png'),normal=a/(asset+'_nor_gl_4k.png'),roughmap=a/(asset+'_rough_4k.png'))
steel=R/'art/quality_20260908/lamps/textures'
for slot,prefix in [('Steel','Steel'),('OxidizedSteel','Oxide'),('Brass','Bronze'),('Enamel','Enamel')]:
    material(slot,tile=.75,base=steel/(prefix+'_BaseColor.png'),normal=steel/(prefix+'_Normal.png'),packed=steel/(prefix+'_MetalSmooth.png'))
material('Mortar',(.23,.205,.17),rough=.95)
material('SignPaint',(.013,.026,.025),rough=.64,metal=.0)
material('Lettering',(.80,.71,.49),rough=.71)
material('Canvas',(.66,.29,.19),tile=.4,rough=.91,normal=R/'refs/quality_20260909/basic-general/materials/fabric_pattern_07/fabric_pattern_07_nor_gl_4k.jpg')
material('CanvasPatch',(.54,.45,.29),tile=.4,rough=.92,normal=R/'refs/quality_20260909/basic-general/materials/fabric_pattern_07/fabric_pattern_07_nor_gl_4k.jpg')
material('Thread',(.39,.27,.14),rough=.96)
material('Rubber',(.019,.026,.024),rough=.84)
material('Bottle',(.21,.28,.24),rough=.3,metal=.1)
material('Label',(.69,.63,.43),rough=.81)
practical=material('WarmGlass',(.65,.43,.14),rough=.32)
practical.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value=(1,.52,.16,1)
practical.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value=.6

def uv(o,tile=1):
    me=o.data;layer=me.uv_layers.active or me.uv_layers.new(name='UV0 metres')
    off=(rng.random()*5,rng.random()*5)
    for f in me.polygons:
        axis=max(range(3),key=lambda a:abs(f.normal[a]))
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            a,b=(p.y,p.z)if axis==0 else ((p.x,p.z)if axis==1 else(p.x,p.y))
            layer.data[li].uv=(a/tile+off[0],b/tile+off[1])
def finish(o,name,mat,group):
    o.name=name;o['group']=group;o['material_slot']=mat;o.data.materials.append(M[mat]);uv(o,M[mat]['tile_metres']);parts.append(o)
    return o
def box(name,c,size,mat='WardStone',group='Masonry',bevel=.009):
    bpy.ops.object.select_all(action='DESELECT');bpy.ops.mesh.primitive_cube_add(size=1,location=B(c));o=bpy.context.object;o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('Crafted edge radius','BEVEL');mod.width=min(bevel,min(size)*.2);mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in o.data.polygons:f.use_smooth=True
    mod=o.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat,group)
def cylinder(name,c,radius,depth,mat='Steel',group='Hardware',axis=(0,1,0),vertices=32):
    bpy.ops.object.select_all(action='DESELECT');bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=B(c));o=bpy.context.object;o.rotation_euler=B(axis).to_track_quat('Z','Y').to_euler();bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mod=o.modifiers.new('Machined edge','BEVEL');mod.width=min(.0025,depth*.15);mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
    for f in o.data.polygons:f.use_smooth=True
    mod=o.modifiers.new('Planar cap normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat,group)
def line(name,points,radius=.018,mat='Steel',group='Hardware'):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=2;curve.bevel_depth=radius;curve.bevel_resolution=3;curve.resolution_u=8
    s=curve.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points,points):p.co=(*B(co),1)
    o=bpy.data.objects.new(name,curve);scene.collection.objects.link(o);bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');return finish(o,name,mat,group)
def bolt(name,c,axis=(0,0,1),mat='Steel',r=.011):
    cylinder(name+' washer',c,r*1.6,.003,mat,axis=axis,vertices=24)
    p=Vector(c)+Vector(axis)*.006;cylinder(name+' hex',p,r,.012,mat,axis=axis,vertices=6)
def text(name,body,c,size,maxwidth,mat='Lettering',face='front',group='Signs'):
    curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.align_x='CENTER';curve.size=size;curve.extrude=.0008;curve.bevel_depth=.0003;curve.bevel_resolution=1;curve.resolution_u=8
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf')
    if font.exists():curve.font=bpy.data.fonts.load(str(font),check_existing=True)
    o=bpy.data.objects.new(name,curve);scene.collection.objects.link(o);o.location=B(c);o.rotation_euler=(math.pi/2,0,0 if face=='front'else math.pi)
    bpy.context.view_layer.update()
    if o.dimensions.x>maxwidth:o.scale*=maxwidth/o.dimensions.x
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');return finish(o,name,mat,group)

# Stone piers and side walls align with the preserved collision, with mortared joints.
for side in [-1,1]:
    x=side*2.4
    box('Side masonry core '+str(side),(x,1.2,-.5),(.38,2.4,1.8),'Mortar',bevel=.003)
    for row in range(5):
        y=.24+row*.48
        for j,z in enumerate([-1.12,-.52,.08]):
            box('Side stone %s %s %s'%(side,row,j),(x,y,z),(.42,.466,.588),'WardStone',bevel=.008+rng.random()*.004)
    box('Pier head bearing '+str(side),(x,2.47,-.46),(.5,.14,1.94),'WardConcrete',bevel=.013)
    box('Front reveal plaster '+str(side),(side*2.173,1.2,-.48),(.028,2.14,1.45),'WardPlaster','Walls',.003)

# Rear wall is a solid supported enclosure. Its former stretched red surface is gone.
box('Rear wall core',(0,1.5,-1.36),(5.2,3,.52),'WardPlaster','Walls',.006)
for row in range(2):
    for j in range(8):
        x=-2.273+j*.649
        box('Rear footing stone %s %s'%(row,j),(x,.15+row*.30,-1.919),(.635,.286,.044),'WardStone',bevel=.004)
for x in [-2.40,2.40]:
    for row in range(6):
        box('Rear corner quoin %s %s'%(x,row),(x,.25+row*.50,-1.9),(.42,.486,.12),'WardStone',bevel=.008)
for x in [-1.83,-.61,.61,1.83]:
    box('Rear recessed service panel %.2f'%x,(x,1.57,-1.914),(1.16,1.70,.023),'Enamel','Rear services',.005)
    for y in [.73,2.4]:
        box('Rear panel horizontal flange %.2f %.2f'%(x,y),(x,y,-1.937),(1.18,.033,.035),'Steel','Rear services',.004)
        for dx in [-.50,.50]:bolt('Rear panel fixing', (x+dx,y,-1.962),(0,0,-1),r=.009)
    for dx in [-.586,.586]:box('Rear panel upright flange %.2f %.2f'%(x,dx),(x+dx,1.57,-1.938),(.033,1.7,.035),'Steel','Rear services',.003)
box('Rear top coping',(0,3.025,-1.52),(5.28,.12,.86),'WardConcrete','Masonry',.014)

# Rear service fittings explain the enclosure; every pipe meets a flange or housing.
box('Aquifer service box',(-1.70,1.17,-1.998),(.56,.66,.13),'Enamel','Rear services',.015)
box('Aquifer box lid',(-1.70,1.17,-2.073),(.52,.60,.025),'Steel','Rear services',.008)
for x in [-1.91,-1.49]:
    for y in [.96,1.38]:bolt('Service lid screw',(x,y,-2.091),(0,0,-1),r=.007)
text('Rear maintenance label','AQUIFER FEED',(-1.70,1.18,-2.092),.075,.42,face='back',mat='Lettering',group='Rear services')
text('Rear maintenance label line2','KEEP CLEAR',(-1.70,1.08,-2.092),.055,.38,face='back',mat='Lettering',group='Rear services')
line('Rear supply conduit',[(-1.70,.84,-2.005),(-1.70,.71,-2.005),(-1.44,.71,-2.005),(-1.40,.66,-2.005),(-1.40,.08,-2.005)],.019,'Steel','Rear services')
for y in [.18,.56]:box('Conduit strap '+str(y),(-1.40,y,-1.987),(.092,.035,.073),'Brass','Rear services',.004)
box('Rear vent surround',(1.36,2.62,-1.937),(.76,.29,.055),'Steel','Rear services',.008)
for i in range(5):box('Rear vent louvre '+str(i),(1.36,2.514+i*.047,-1.977),(.67,.031,.055),'Enamel','Rear services',.006)

# Keep the exterior service relief inside the existing porch/parcel depth.
for o in parts:
    if o['group']=='Rear services' or o.name.startswith(('Rear footing stone','Rear corner quoin')):o.location+=B((0,0,.30))
cope=next(o for o in parts if o.name=='Rear top coping');cope.location+=B((0,0,.15));cope.scale.y=.68

# The under-awning frame spans from the existing side-wall bearings, leaving the porch clear.
for x in [-2.43,2.43]:
    box('Roof side bearer '+str(x),(x,2.55,.10),(.13,.16,3.15),'Steel','Structure',.006)
    line('Cantilever brace '+str(x),[(x,1.97,.31),(x,2.52,1.56)],.034,'Steel','Structure')
    box('Cantilever wall plate '+str(x),(x,2.06,.426),(.24,.38,.035),'Steel','Structure',.006)
    for dx in [-.072,.072]:
        for y in [1.94,2.17]:bolt('Bearer anchor',(x+dx,y,.448),r=.012)
box('Front box section lintel',(0,2.52,1.58),(5.32,.19,.23),'Steel','Structure',.009)
box('Rear roof bearer',(0,2.93,-1.17),(5.22,.16,.19),'Steel','Structure',.008)
for x in [-1.60,-.53,.53,1.60]:
    line('Awning intermediate rib '+str(x),[(x,2.97,-1.20),(x,2.88,-.52),(x,2.73,.46),(x,2.63,1.66)],.014,'Steel','Structure')

# A real thin cloth shell, divided into longitudinal panels and sewn to a perimeter hem.
def height(x,z):
    t=(z+1.22)/2.95
    return 3.015-.385*t-.054*math.sin(math.pi*t)+.009*math.sin(x*9.4)*math.sin(math.pi*t)
def cloth(name,x0,x1,z0,z1,mat='Canvas',extra=0):
    nx=max(4,int((x1-x0)*26));nz=max(4,int((z1-z0)*26));vs=[];faces=[]
    for iz in range(nz+1):
        z=z0+(z1-z0)*iz/nz
        for ix in range(nx+1):
            x=x0+(x1-x0)*ix/nx;vs.append(B((x,height(x,z)+extra,z)))
    for iz in range(nz):
        for ix in range(nx):
            a=iz*(nx+1)+ix;faces.append((a,a+1,a+nx+2,a+nx+1))
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update();o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
    uv0=me.uv_layers.new(name='UV0 calibrated weave')
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv0.data[li].uv=(p.x/.4,-p.y/.4)
    o['group']='Canopy';o['material_slot']=mat;me.materials.append(M[mat]);parts.append(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('Sewn cloth thickness','SOLIDIFY');mod.thickness=.003;mod.offset=0;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
edges=[-2.66,-1.32,.03,1.34,2.66]
for i in range(4):cloth('Canvas panel '+str(i),edges[i],edges[i+1],-1.22,1.73)
for x in edges:
    line('Longitudinal sewn hem '+str(x),[(x,height(x,-1.22+j*2.95/60)+.004,-1.22+j*2.95/60)for j in range(61)],.0055,'Thread','Canopy')
for z in [-1.22,1.73]:
    line('Canopy end binding '+str(z),[(x,height(x,z)+.003,z)for x in [-2.66+i*5.32/80 for i in range(81)]],.009,'CanvasPatch','Canopy')
for x0,x1,z0,z1 in [(-2.28,-1.68,-.3,.30),(.51,1.18,.80,1.26)]:
    cloth('Sewn canvas repair',x0,x1,z0,z1,'CanvasPatch',.005)
    for x in [x0+.014,x1-.014]:
        for j in range(int((z1-z0)/.036)):
            z=z0+.025+j*.036;line('Repair lock stitch',[(x,height(x,z)+.009,z),(x,height(x,z+.012)+.009,z+.012)],.0012,'Thread','Canopy')
for x in [-2.62,-1.3,.04,1.32,2.62]:
    for z in [-1.21,1.71]:
        y=height(x,z);cylinder('Canopy grommet',(x,y+.004,z),.020,.004,'Brass','Canopy',vertices=32)
        line('Canopy attachment tie',[(x,y+.016,z),(x,y-.05,z+.026),(x,y-.10,z-.033),(x,y+.016,z)],.0035,'Thread','Canopy')

# A flat, separately lettered sign; no baked generated text or floating lintel slivers.
box('Sign backing frame',(0,2.31,1.73),(5.16,.47,.064),'Steel','Signs',.012)
box('Sign enamel face',(-.30,2.31,1.772),(4.50,.401,.018),'SignPaint','Signs',.004)
text('BASIC GENERAL sign','BASIC GENERAL',(-.32,2.245,1.785),.295,4.0)
box('Open indicator housing',(2.07,2.31,1.78),(.52,.40,.038),'Steel','Signs',.008)
box('Open indicator face',(2.07,2.31,1.805),(.46,.31,.012),'SignPaint','Signs',.005)
text('Open lettering','OPEN',(2.07,2.265,1.815),.115,.405,'Lettering')
for x in [-2.46,-.21,2.42]:
    for y in [2.125,2.495]:bolt('Sign mounting screw',(x,y,1.77),r=.007)
for x in [-2.35,2.35]:
    box('Sign hanger '+str(x),(x,2.50,1.69),(.06,.23,.03),'Steel','Signs',.004)

# Stock storage stays against the back wall, clear of Mira and the player approach.
for x in [-1.72,1.72]:
    box('Stock recessed cabinet '+str(x),(x,1.37,-1.044),(.79,1.22,.12),'Steel','Stock',.012)
    for y in [1.0,1.48,1.91]:box('Stock shelf '+str((x,y)),(x,y,-.945),(.74,.026,.26),'Enamel','Stock',.004)
    for row,y in enumerate([1.145,1.625]):
        for j in range(3):
            cx=x-.245+j*.235;h=.22+((j+row)%2)*.025
            cylinder('Sealed goods tin',(cx,y,-.927),.079,h,'Bottle','Stock',vertices=32)
            cylinder('Tin rolled lid',(cx,y+h/2+.004,-.927),.082,.018,'Steel','Stock',vertices=32)
            box('Tin label',(cx,y,-.846),(.102,.068,.006),'Label','Stock',.002)
            text('Stock exact label','WATER'if row==0 else'SALTS',(cx,y-.012,-.840),.020,.096,'SignPaint',group='Stock')
box('Counter repair fascia',(0,.48,-1.049),(4.25,.79,.10),'Enamel','Stock',.007)
for x in [-1.34,0,1.34]:
    box('Counter inset plate '+str(x),(x,.47,-.986),(1.27,.67,.025),'Steel','Stock',.008)
    for dx in [-.53,.53]:
        for y in [.18,.76]:bolt('Counter plate rivet',(x+dx,y,-.966),r=.007)
box('Service ledge',(0,.902,-1.052),(4.27,.062,.24),'Enamel','Stock',.012)
box('Counter working lip',(0,.94,-.927),(4.29,.04,.045),'Steel','Stock',.005)
text('Supplies service title','WATER  /  SUPPLIES  /  SALVAGE',(0,2.025,-1.082),.092,2.9,'Lettering',group='Stock')

# Two fixed under-sign lamps with real housings, end caps and cable returns.
for x in [-1.23,1.23]:
    box('Under-sign light bracket '+str(x),(x,2.548,1.472),(.46,.09,.17),'Steel','Lights',.009)
    box('Protected amber light '+str(x),(x,2.50,1.50),(.35,.039,.085),'WarmGlass','Lights',.012)
    for dx in [-.207,.207]:box('Lamp end cap',(x+dx,2.52,1.49),(.031,.08,.13),'Steel','Lights',.006)

# Authoring context only: existing slab dimensions and a neutral 1.8 m human-height marker.
context=[]
for name,c,size in [('Existing porch context',(0,-.29,.235),(5.66,.58,4.13)),('Existing step context',(0,-.375,2.70),(3.2,.25,.8))]:
    o=box(name,c,size,'WardConcrete','Context',.008);parts.remove(o);context.append(o)
marker=cylinder('1.8 m standing scale marker',(3.6,.9,.7),.20,1.8,'Enamel','Context',vertices=32);parts.remove(marker);context.append(marker)
box_marker=box('Scale marker feet',(3.6,.035,.7),(.46,.07,.36),'Enamel','Context',.015);parts.remove(box_marker);context.append(box_marker)

# Preserve the detailed editable object source before exports or image work.
source=O/'basic-general-source-v1.blend'
bpy.data.libraries.write(str(source),{scene},fake_user=True,compress=True)

# Explicit Unity mesh interchange makes handedness, per-part identities and material assignment reviewable.
records=[]
for o in parts:
    me=o.data;me.calc_loop_triangles();verts=[];norms=[];uvs=[];indices=[];unique={}
    normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
    for tri in me.loop_triangles:
        for li in tri.loops:
            vi=me.loops[li].vertex_index;p=o.matrix_world@me.vertices[vi].co;n=(normal_matrix@me.corner_normals[li].vector).normalized();t=me.uv_layers.active.data[li].uv
            key=tuple(round(v,8)for v in (*p,*n,*t))
            if key not in unique:
                unique[key]=len(verts);verts.append(U(p));norms.append(U(n));uvs.append([round(t.x,7),round(t.y,7)])
            indices.append(unique[key])
    # B/U are proper rotations. Preserve authored order, verified against Unity's built-in cube.
    records.append({'name':o.name,'group':o['group'],'material':o['material_slot'],'vertices':verts,'normals':norms,'uv0':uvs,'triangles':indices})
(O/'basic-general-meshes-v1.json').write_text(json.dumps({'pivotUnity':[8,.5,15.1],'frontUnity':[0,0,1],'parts':records},separators=(',',':')))
(O/'material-bindings-v1.json').write_text(json.dumps(materials,indent=2))
(O/'source-authoring-v1.json').write_text(json.dumps({'source':str(source),'parts':len(parts),'triangles':sum(len(r['triangles'])//3 for r in records),'original_source':'meshy/salvage-20260908/general/general.glb','original_triangles':4277,'runtime_state':'Source candidate only; no Unity integration','clearance':'Existing six authored colliders preserved; stock relief is attached to rear wall. Native approach/collision review required.'},indent=2))
print(json.dumps({'source':str(source),'parts':len(parts),'triangles':sum(len(r['triangles'])//3 for r in records)}))
