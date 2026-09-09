"""Editable Hall reconstruction; execute only through the shared live Blender MCP."""
import bpy, bmesh, math, json, random, ast
from pathlib import Path
from mathutils import Vector

R=Path('/home/teknetik/code/ao2'); O=R/'art/quality_20260909/vanguard-hall'
scene=bpy.data.scenes.get('Ward Vanguard Hall repair') or bpy.data.scenes.new('Ward Vanguard Hall repair')
assert scene.get('ward_asset') in [None,'vanguard-hall']
assert not scene.objects or scene.get('ward_asset')=='vanguard-hall'
scene['ward_asset']='vanguard-hall'; bpy.context.window.scene=scene
for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
objects=[]; group='Structure'; family='Hall'; rng=random.Random(909261)
def B(p): return Vector((p[0],-p[2],p[1]))
def U(p): return [round(p.x,6),round(p.z,6),round(-p.y,6)]

# Retain the generated original as a hidden, normalized source in this document.
before=set(scene.objects); bpy.ops.import_scene.gltf(filepath=str(R/'meshy/salvage-20260908/hall/hall.glb'))
original=[ob for ob in scene.objects if ob not in before]
mesh_original=[ob for ob in original if ob.type=='MESH']
points=[ob.matrix_world@v.co for ob in mesh_original for v in ob.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3))); hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
source_scale=12/(hi.x-lo.x)
for ob in mesh_original:
    world=ob.matrix_world.copy()
    for v in ob.data.vertices:
        p=world@v.co; v.co=(p-Vector(((hi.x+lo.x)/2,lo.y,lo.z)))*source_scale
    ob.matrix_world.identity(); ob.name='Hall retained original source'; ob.hide_render=True; ob.hide_set(True)
    ob['source']='meshy/salvage-20260908/hall/hall.glb'; ob['source_sha256']='fa5b84841aa60f0a30c07296a526b492190b470bf41addbc915ec2113338e349'

M={}; tiles={}
shared={'WardPlaster':('beige_wall_001',3),'WardStone':('rock_surface',2),'WardConcrete':('rough_concrete',1.23),'WardWornSteel':('rusty_metal_sheet',2)}
for name in list(shared)+['Paint','Steel','Bronze','Rubber','Enamel','Dust','Cloth','BannerMark','Lettering']:
    m=bpy.data.materials.get('Hall_'+name) or bpy.data.materials.new('Hall_'+name); m.use_nodes=True; m.node_tree.nodes.clear()
    nodes=m.node_tree.nodes; links=m.node_tree.links; bs=nodes.new('ShaderNodeBsdfPrincipled'); out=nodes.new('ShaderNodeOutputMaterial'); links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(.24,.035,.017,1) if name=='Cloth' else (.55,.38,.19,1) if name=='BannerMark' else (.59,.48,.28,1) if name=='Lettering' else (.3,.3,.3,1)
    bs.inputs['Roughness'].default_value=.82 if name in ['Cloth','BannerMark'] else .5
    if name=='Lettering': bs.inputs['Metallic'].default_value=.45
    paths=[]; tiles[name]=.75
    if name in shared:
        asset,tile=shared[name]; tiles[name]=tile; root=R/'refs/quality_20260909/building-materials'/asset
        paths=[('BaseColor',root/(asset+'_diff_4k.png')),('Normal',root/(asset+'_nor_gl_4k.png')),('Roughness',root/(asset+'_rough_4k.png'))]
    elif name=='Cloth':
        tiles[name]=.4; root=R/'refs/quality_20260909/basic-general/materials/fabric_pattern_07'
        paths=[('Normal',root/'fabric_pattern_07_nor_gl_4k.jpg'),('Roughness',root/'fabric_pattern_07_rough_4k.jpg')]
    elif name not in ['Lettering','BannerMark']:
        paths=[(suffix,R/'art/quality_20260908/lamps/textures'/(name+'_'+suffix+'.png')) for suffix in ['BaseColor','Normal','MetalSmooth']]
    for kind,path in paths:
        im=bpy.data.images.load(str(path),check_existing=True); tex=nodes.new('ShaderNodeTexImage'); tex.image=im
        if kind!='BaseColor': im.colorspace_settings.name='Non-Color'
        if kind=='BaseColor':
            links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            if name=='Dust': links.new(tex.outputs['Alpha'],bs.inputs['Alpha']); m.surface_render_method='DITHERED'
        elif kind=='Normal':
            normal=nodes.new('ShaderNodeNormalMap'); normal.inputs['Strength'].default_value=1 if name in shared else .55 if name=='Cloth' else .7
            links.new(tex.outputs['Color'],normal.inputs['Color']); links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        elif kind=='Roughness': links.new(tex.outputs['Color'],bs.inputs['Roughness'])
        else:
            split=nodes.new('ShaderNodeSeparateColor'); links.new(tex.outputs['Color'],split.inputs[0]); links.new(split.outputs['Red'],bs.inputs['Metallic'])
            inv=nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1; links.new(tex.outputs['Alpha'],inv.inputs[1]); links.new(inv.outputs[0],bs.inputs['Roughness'])
    M[name]=m

def finish(ob,name,mat,bevel=0):
    ob.name=family+' '+name; ob['group']=group; ob['region']=mat
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
    if ob.type in ['CURVE','FONT']: bpy.ops.object.convert(target='MESH'); ob=bpy.context.object
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=ob.modifiers.new('Construction edge radius','BEVEL'); mod.width=bevel; mod.segments=3; bpy.ops.object.modifier_apply(modifier=mod.name)
    me=ob.data; me.materials.clear(); me.materials.append(M[mat]); uv=me.uv_layers.active or me.uv_layers.new(name='UV0 physical tile space')
    off=(rng.random()*9,rng.random()*9); tile=tiles[mat]
    for f in me.polygons:
        axis=max(range(3),key=lambda i:abs(f.normal[i]))
        for li in f.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv=((v.y if axis==0 else v.x)/tile+off[0],(v.y if axis==2 else v.z)/tile+off[1])
        f.use_smooth=True
    if len(me.polygons)>1:
        mod=ob.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL'); mod.keep_sharp=True; bpy.ops.object.modifier_apply(modifier=mod.name)
    objects.append(ob); return ob

# Original, separately authored primitive helpers; the lamp scene code is not executed.
tree=ast.parse((R/'art/quality_20260908/lamps/author_lamps.py').read_text())
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ['box','cylinder','tube','ring','bolt']:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'Ward original construction helpers','exec'))

def solid(name,vertices,faces,mat='WardPlaster',bevel=.012):
    me=bpy.data.meshes.new(name); me.from_pydata([B(p) for p in vertices],[],faces); me.update()
    bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
    ob=bpy.data.objects.new(name,me); scene.collection.objects.link(ob); return finish(ob,name,mat,bevel)

def prism(name,outline,front,back,mat='WardPlaster',bevel=.014):
    n=len(outline); v=[(x,y,z) for z in [front,back] for x,y in outline]
    faces=[tuple(range(n)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return solid(name,v,faces,mat,bevel)

def plate(name,points,normal,thickness=.035,mat='Paint',bevel=.006):
    normal=Vector(normal).normalized(); v=[tuple(Vector(p)+normal*d) for d in [0,-thickness] for p in points]
    return solid(name,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat,bevel)

def blocks(name,a,b,y,height,z,depth,mat='WardPlaster',length=1.04):
    count=max(1,math.ceil((b-a)/length)); w=(b-a)/count
    for i in range(count): box(name+' '+str(i),((a+(i+.5)*w),y,z),(w-.009,height,depth),mat,.018)

def cap(name,y,width,depth,centre_z=-2.123,mat='WardStone'):
    # Individual coping units have real thickness, bed joints, undersides and a drip edge.
    blocks(name+' front',-width/2,width/2,y,.25,centre_z+depth/2-.21,.42,mat)
    blocks(name+' rear',-width/2,width/2,y,.25,centre_z-depth/2+.21,.42,mat)
    for x in [-width/2+.20,width/2-.20]: box(name+' side '+str(x),(x,y,centre_z),(.40,.25,depth-.84),mat,.018)
    box(name+' supporting course',(0,y-.22,centre_z),(width-.28,.20,depth-.22),'WardPlaster',.02)

group='Ground masonry'
# The original plinth remains a Unity source outside this visual replacement.
for x in [-5.40,5.40]:
    box('Side wall '+str(x),(x,1.80,-2.21),(.54,3.60,3.50),'WardPlaster',.025)
    for y in [.22,1.02,1.82,2.62,3.32]:
        box('Rear quoin %.1f %.2f'%(x,y),(x,y,-3.90),(.63,.43,.47),'WardStone',.021)
        box('Front quoin %.1f %.2f'%(x,y),(x,y,-.60),(.63,.43,.47),'WardStone',.021)
# Front returns leave a real portal recess; the closed door ends the current gameplay access.
box('Front left return',(-4.30,1.77,-.64),(2.30,3.54,.42),'WardPlaster',.021)
box('Front right return',(4.30,1.77,-.64),(2.30,3.54,.42),'WardPlaster',.021)
box('Entrance upper wall',(0,3.49,-.78),(6.35,.36,.48),'WardPlaster',.018)
# Rear wall is split around the 1.22 x 2.3 m service door instead of painting an opening on solid mass.
box('Rear broad left wall',(-2.36,1.80,-3.965),(6.08,3.60,.30),'WardPlaster',.022)
box('Rear right wall',(3.88,1.80,-3.965),(3.04,3.60,.30),'WardPlaster',.022)
box('Rear service header',(1.52,2.98,-3.965),(1.68,1.24,.30),'WardPlaster',.022)
box('Interior closed floor',(0,.035,-2.16),(10.30,.07,3.08),'WardConcrete',.012)
cap('Lower cornice',3.82,12,4.246306,mat='WardStone')

group='Front portal'
outer=[(-3.10,0),(3.10,0),(3.10,2.96),(2.42,3.64),(-2.42,3.64),(-3.10,2.96)]
inner=[(-2.55,.13),(2.55,.13),(2.55,2.65),(2.02,3.18),(-2.02,3.18),(-2.55,2.65)]
for i in range(6):
    j=(i+1)%6
    prism('Portal structural segment '+str(i),[outer[i],outer[j],inner[j],inner[i]],-.025,-.55,'WardPlaster',.020)
    # Dressed stone keys expose a different material only at the coping and impact-prone sill.
box('Dressed entrance threshold',(0,.070,-.31),(5.11,.14,.55),'WardStone',.018)
for side in [-1,1]:
    x=side*4.69
    # A real vent recess between narrow stone shoulders; no elongated painted black decal.
    box('Pier back '+str(side),(x,1.72,-.47),(1.18,3.44,.26),'WardPlaster',.025)
    for dx in [-.45,.45]: box('Pier stone shoulder %.0f %.2f'%(side,dx),(x+dx,1.66,-.24),(.29,3.10,.47),'WardPlaster',.025)
    box('Pier footing '+str(side),(x,.13,-.295),(1.43,.26,.56),'WardStone',.022)
    box('Pier capital '+str(side),(x,3.36,-.295),(1.43,.31,.56),'WardStone',.022)
    box('Pier vent dark cavity '+str(side),(x,1.71,-.323),(.59,2.32,.055),'Rubber',.006)
    for y in [1.71+j*.12 for j in range(-8,9)]: box('Pier louvre %.0f %.2f'%(side,y),(x,y,-.276),(.48,.033,.073),'Paint',.005)
    for dx in [-.245,.245]: box('Pier vent frame %.0f %.2f'%(side,dx),(x+dx,1.71,-.260),(.03,2.11,.04),'Steel',.004)

group='Heavy closed double doors'
left=[(-2.525,.15),(-.015,.15),(-.015,3.155),(-2.00,3.155),(-2.525,2.63)]
right=[(.015,.15),(2.525,.15),(2.525,2.63),(2.00,3.155),(.015,3.155)]
for side,outline in [(-1,left),(1,right)]:
    prism('Door leaf '+str(side),outline,-.255,-.365,'Paint',.012)
    for x in [side*.055,side*2.42]: box('Door folded stile %.0f %.2f'%(side,x),(x,1.45,-.227),(.07,2.54,.065),'Enamel',.008)
    for y in [.27,1.02,2.11]: box('Door reinforcement %.0f %.2f'%(side,y),(side*1.27,y,-.225),(2.30,.07,.065),'Enamel',.008)
    box('Door lower kickplate '+str(side),(side*1.27,.49,-.213),(2.20,.32,.035),'Steel',.009)
    for x in [side*.30,side*2.24]:
        for y in [.39,.59,1.03,2.10]: bolt('Door captive bolt %.0f %.2f %.2f'%(side,x,y),(x,y,-.184),.013,(0,0,1))
    for y in [.57,1.56,2.47]:
        cylinder('Hinge barrel %.0f %.2f'%(side,y),(side*2.52,y,-.197),.046,.23,'Steel',verts=24,bevel=.006)
        box('Hinge jamb plate %.0f %.2f'%(side,y),(side*2.62,y,-.185),(.18,.26,.035),'Paint',.006)
        for dy in [-.078,.078]: bolt('Hinge jamb fixing %.0f %.2f %.2f'%(side,y,dy),(side*2.64,y+dy,-.157),.012,(0,0,1))
    x=side*.40
    box('Handle backing '+str(side),(x,1.34,-.194),(.17,.53,.026),'WardWornSteel',.006)
    for y in [1.17,1.52]: cylinder('Handle stand-off %.0f %.2f'%(side,y),(x,y,-.135),.026,.12,'Steel',(0,0,1),verts=24,bevel=.004)
    tube('Public door pull '+str(side),[(x,1.15,-.087),(x,1.54,-.087)],.023,'Bronze')
box('Door centre weather seal',(0,1.65,-.280),(.036,3.04,.032),'Rubber',.003)

group='Readable hall name'
box('Nameplate folded frame',(0,3.80,-.042),(6.80,.39,.025),'Bronze',.008)
box('Nameplate enamel face',(0,3.80,-.027),(6.62,.30,.018),'Paint',.006)
font=bpy.data.fonts.load(str(R/'unity/AthenHill/Assets/AthenHill/UI/Art/ColonySans.ttf'),check_existing=True)
curve=bpy.data.curves.new('VANGUARD HALL separate type','FONT'); curve.body='VANGUARD HALL'; curve.font=font; curve.align_x='CENTER'; curve.align_y='CENTER'; curve.size=.205; curve.extrude=.0015; curve.bevel_depth=.0007; curve.resolution_u=3
ob=bpy.data.objects.new('Name lettering',curve); scene.collection.objects.link(ob); ob.location=B((0,3.80,-.014)); ob.rotation_euler[0]=math.pi/2; finish(ob,'VANGUARD HALL lettering','Lettering')
for x in [-3.22,3.22]: bolt('Sign fixing '+str(x),(x,3.80,-.020),.010,(0,0,1))

def frustum(name,y0,y1,w0,w1,d0,d1,zc,mat='Paint'):
    v=[]
    for y,w,d in [(y0,w0,d0),(y1,w1,d1)]: v.extend([(-w/2,y,zc+d/2),(w/2,y,zc+d/2),(w/2,y,zc-d/2),(-w/2,y,zc-d/2)])
    return solid(name,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat,.012)

def tier(name,y0,y1,w0,w1,d0,d1,zc,rows):
    frustum(name+' structural envelope',y0,y1,w0,w1,d0,d1,zc,'Paint')
    def wh(y):
        t=(y-y0)/(y1-y0); return w0+(w1-w0)*t,d0+(d1-d0)*t
    for row in range(rows):
        a=y0+.035+row*(y1-y0)/rows; b=y0+(row+1)*(y1-y0)/rows-.035; wa,da=wh(a); wb,db=wh(b)
        cols=max(3,round((wa+wb)/2/1.15))
        for face in [-1,1]:
            for col in range(cols):
                q0=-.5+col/cols; q1=-.5+(col+1)/cols; pad=.016
                pts=[(wa*q0+pad,a,zc+face*(da/2+.027)),(wa*q1-pad,a,zc+face*(da/2+.027)),(wb*q1-pad,b,zc+face*(db/2+.027)),(wb*q0+pad,b,zc+face*(db/2+.027))]
                normal=(0,(da-db)/(2*(b-a)),face)
                plate(name+' seamed panel %d %d %d'%(face,row,col),pts,normal,.031,'Enamel' if (col+row*3)%9==2 else 'Paint',.006)
        # Metal returns are actual side elevation panels with matching seams.
        for side in [-1,1]:
            for col in range(3):
                q0=-.5+col/3; q1=-.5+(col+1)/3
                pts=[(side*(wa/2+.027),a,zc+da*q0+.015),(side*(wa/2+.027),a,zc+da*q1-.015),(side*(wb/2+.027),b,zc+db*q1-.015),(side*(wb/2+.027),b,zc+db*q0+.015)]
                plate(name+' side return %d %d %d'%(side,row,col),pts,(side,(wa-wb)/(2*(b-a)),0),.031,'Paint',.006)
        for face in [-1,1]: box(name+' horizontal rib %d %d'%(row,face),(0,b+.018,zc+face*(db/2+.062)),(wb+.06,.060,.075),'Steel',.009)

group='Lower industrial tier'
tier('Lower tier',4.04,6.32,10.56,10.43,3.52,3.28,-2.18,2)
for side in [-1,1]:
    for y in [4.36,5.10,5.84]:
        box('Middle front buttress %.0f %.2f'%(side,y),(side*4.49,y,-.36),(.64,.735,.29),'WardPlaster',.018)
        box('Middle rear buttress %.0f %.2f'%(side,y),(side*4.49,y,-3.91),(.64,.735,.29),'WardPlaster',.018)
cap('Middle coping',6.55,11.06,3.66,-2.15,'WardStone')
group='Tapered upper tier'
tier('Upper tier',6.71,10.40,10.00,7.62,3.13,2.48,-2.29,3)
cap('Crown coping',10.64,8.13,2.68,-2.29,'WardStone')
group='Roof crown and antenna'
frustum('Mineral crown',10.765,12.11,3.47,2.49,1.76,1.40,-2.68,'WardPlaster')
box('Crown bearing plate',(0,12.20,-2.68),(2.68,.18,1.59),'Paint',.025)
box('Roof maintenance cover',(.94,10.93,-2.08),(.44,.29,.45),'WardWornSteel',.014)
for x in [-.28,.28]:
    for z in [-2.88,-2.48]: bolt('Antenna foundation %.2f %.2f'%(x,z),(x,12.31,z),.023)
cylinder('Antenna base sleeve',(0,12.64,-2.68),.125,.66,'Steel',verts=32,bevel=.009)
cylinder('Antenna main mast',(0,13.48,-2.68),.066,1.62,'Paint',r2=.034,verts=32,bevel=.006)
cylinder('Antenna tip',(0,14.355,-2.68),.028,.08,'Bronze',verts=24,bevel=.004)
cylinder('Antenna crossbar',(0,13.27,-2.68),.055,3.72,'Paint',(1,0,0),verts=24,bevel=.006)
for x,y in [(-.02,13.38),(1.17,13.70)]: cylinder('Antenna secondary tine '+str(x),(x,y,-2.68),.026,.55,'Steel',verts=24,bevel=.003)
for x in [-1.25,1.25]: tube('Antenna bracing '+str(x),[(0,12.92,-2.68),(x,13.27,-2.68)],.024,'Steel')

group='Attached red hall banner'
def banner_z(x,y): return -.378+.025*math.sin(x*3+y*1.7)+.014*math.sin(y*7)*math.cos(x*2)
vs=[]; faces=[]; nx,ny=30,32
for j in range(ny+1):
    y=4.06+j*2.10/ny
    for i in range(nx+1):
        x=-1.15+i*2.30/nx; vs.append((x,y,banner_z(x,y)))
for j in range(ny):
    for i in range(nx):
        k=j*(nx+1)+i; faces.append((k,k+1,k+nx+2,k+nx+1))
solid('Repaired woven hall banner',vs,faces,'Cloth',0)
for x in [-1.10,1.10]:
    tube('Banner stitched side '+str(x),[(x,y,banner_z(x,y)+.003) for y in [4.08+i*2.07/40 for i in range(41)]],.003,'Cloth')
for y in [4.09,6.13]: tube('Banner hem '+str(y),[(x,y,banner_z(x,y)+.004) for x in [-1.11+i*2.22/40 for i in range(41)]],.004,'Cloth')
for x in [-.94,.94]:
    box('Banner masonry mounting '+str(x),(x,6.24,-.455),(.17,.18,.17),'Steel',.006)
    ring('Banner eyelet '+str(x),(x,6.10,banner_z(x,6.10)+.008),.032,.006,'Bronze',(0,0,1),seg=24)
    tube('Banner tied mounting '+str(x),[(x,6.20,-.345),(x,6.10,banner_z(x,6.10)+.02)],.009,'Rubber')
for x,height in [(-.15,1.13),(.15,.67)]:
    pts=[(x-.10,4.45),(x+.10,4.45),(x+.10,4.45+height-.06),(x,4.45+height),(x-.10,4.45+height-.055)]
    solid('Original twin stripe '+str(x),[(xx,yy,banner_z(xx,yy)+.0018) for xx,yy in pts],[(0,1,2,3,4)],'BannerMark',0)

group='Rear service construction'
for x in [.78,2.26]: box('Rear service jamb '+str(x),(x,1.20,-4.105),(.20,2.40,.21),'WardStone',.015)
box('Rear service lintel',(1.52,2.46,-4.105),(1.68,.22,.21),'WardStone',.016)
box('Rear service threshold',(1.52,.07,-4.09),(1.28,.14,.29),'WardStone',.014)
box('Rear service weather seal',(1.52,1.25,-4.012),(1.30,2.35,.026),'Rubber',.006)
box('Rear closed service leaf',(1.52,1.25,-4.035),(1.24,2.30,.08),'Paint',.014)
for y in [.57,1.87]:
    box('Rear louvre backing '+str(y),(1.52,y,-4.089),(.72,.59,.024),'Rubber',.005)
    for k in range(7): box('Rear louvre %.2f %d'%(y,k),(1.52,y-.25+k*.083,-4.110),(.66,.038,.05),'Steel',.004)
for y in [.44,1.18,2.02]: cylinder('Rear hinge '+str(y),(.916,y,-4.129),.033,.17,'Steel',verts=24,bevel=.004)
tube('Rear door pull',[(1.98,1.04,-4.170),(1.98,1.35,-4.170)],.019,'Bronze')
for y in [1.04,1.35]: cylinder('Rear pull mount '+str(y),(1.98,y,-4.126),.024,.091,'Steel',(0,0,1),verts=24,bevel=.004)
# A readable repair plate replaces the old ill-defined trapezoid/shard feature.
box('Rear bolted masonry repair',(-2.47,1.36,-4.138),(1.60,1.73,.044),'WardWornSteel',.016)
for x in [-3.16,-1.78]:
    for y in [.65,1.11,1.57,2.03]: bolt('Repair masonry anchor %.2f %.2f'%(x,y),(x,y,-4.174),.019,(0,0,-1))
box('Rear electrical enclosure',(3.10,1.61,-4.137),(.51,.67,.16),'Enamel',.015)
box('Rear enclosure recessed panel',(3.10,1.62,-4.224),(.40,.54,.017),'Paint',.006)
for y in [1.40,1.80]: cylinder('Enclosure captive screw '+str(y),(3.28,y,-4.236),.012,.004,'Steel',(0,0,-1),verts=12,bevel=.001)
tube('Rear roof drainage',[(4.47,6.34,-4.07),(4.47,3.55,-4.07),(4.47,3.42,-4.13),(4.47,.32,-4.13),(4.19,.20,-4.13)],.065,'Bronze')
for y in [.57,1.95,3.18,4.58,5.99]:
    ring('Drain service collar '+str(y),(4.47,y,-4.13 if y<3.42 else -4.07),.069,.012,'Steel',seg=32)
    box('Drain masonry stand-off '+str(y),(4.47,y,-4.031),(.20,.11,.12),'Steel',.005)
    for dx in [-.13,.13]: bolt('Drain anchor %.2f %.2f'%(y,dx),(4.47+dx,y,-4.100),.012,(0,0,-1))
tube('Enclosure conduit',[(3.10,1.28,-4.13),(3.10,.91,-4.13),(3.82,.91,-4.13),(3.82,3.37,-4.13)],.025,'Paint')
for y in [1.34,2.21,3.07]:
    box('Conduit saddle '+str(y),(3.82,y,-4.156),(.12,.043,.027),'Steel',.004)
    for dx in [-.044,.044]: bolt('Conduit saddle fixing %.2f %.3f'%(y,dx),(3.82+dx,y,-4.178),.007,(0,0,-1))

group='Supported upper service repairs'
for x,y,z,w,h in [(-3.56,8.24,-.800,.63,.74),(3.45,5.02,-.412,.82,.94)]:
    box('Upper replacement plate %.2f %.2f'%(x,y),(x,y,z),(w,h,.065),'WardWornSteel',.009)
    for dx in [-w*.38,w*.38]:
        for dy in [-h*.38,h*.38]: bolt('Upper plate fixing %.2f %.2f %.2f %.2f'%(x,y,dx,dy),(x+dx,y+dy,z+.048),.015,(0,0,1))

group='Localized construction wear'
# Small true corner losses on only three exposed members; the structure remains sound.
for name,p,radius in [('Hall Pier footing 1',(5.39,.075,-.01),.061),('Hall Lower cornice front 0',(-5.96,3.90,-.065),.070),('Hall Portal structural segment 2',(3.03,3.00,-.035),.047)]:
 target=bpy.data.objects.get(name)
 if target:
  bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=radius,location=B(p));cutter=bpy.context.object;cutter.name='Hall temporary chip cutter'
  for v in cutter.data.vertices:v.co*=1+rng.uniform(-.12,.12)
  bpy.context.view_layer.objects.active=target;mod=target.modifiers.new('Local corner impact','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
  bm=bmesh.new();bm.from_mesh(target.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(target.data);bm.free()
  mod=target.modifiers.new('Impact corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
def film(name,points):
 ob=solid(name,points,[(0,1,2,3)],'Dust',0)
 for li,t in enumerate([(0,0),(1,0),(1,1),(0,1)]):ob.data.uv_layers.active.data[li].uv=t
 return ob
for x in [-4.69,4.69]:
 film('Pier protected footing dust '+str(x),[(x-.56,.265,-.47),(x-.56,.265,-.02),(x+.56,.265,-.02),(x+.56,.265,-.47)])
for x in [-3.7,2.8]:
 film('Coping sheltered dust '+str(x),[(x-.74,6.680,-.72),(x-.74,6.680,-.37),(x+.74,6.680,-.37),(x+.74,6.680,-.72)])

# Export all authored surfaces with material-space UV0 and weighted corner normals.
data=[]
for ob in objects:
    me=ob.data; me.calc_loop_triangles(); p=[]; n=[]; uv=[]; indices=[]; unique={}
    for tri in me.loop_triangles:
        for li in tri.loops:
            pp=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co); nn=U(ob.matrix_world.to_3x3()@me.corner_normals[li].vector); tt=[round(float(q),6) for q in me.uv_layers.active.data[li].uv]; key=tuple(pp+nn+tt)
            if key not in unique: unique[key]=len(p); p.append(pp); n.append(nn); uv.append(tt)
            indices.append(unique[key])
    data.append(dict(name=ob.name,group=ob['group'],material=ob['region'],positions=p,normals=n,uv=uv,indices=indices))
(O/'hall-meshes.json').write_text(json.dumps(data,separators=(',',':')))
points=[v for part in data for v in part['positions']]
report=dict(parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),vertices=sum(len(p['positions']) for p in data),bounds=dict(min=[min(p[i] for p in points) for i in range(3)],max=[max(p[i] for p in points) for i in range(3)]),source='Original Ward reconstruction preserving Hall silhouette, retained Meshy source hidden in document',materialTiles=tiles,nativeAcceptance='Pending independent source and native gates')
(O/'geometry-report.json').write_text(json.dumps(report,indent=2))

# Source studio only. The imported guard is an existing model for scale and is never exported with the building.
before=set(scene.objects); bpy.ops.import_scene.gltf(filepath=str(R/'meshy/ward-guard/model/character-rigged.glb'))
marker=[ob for ob in scene.objects if ob not in before]
coords=[ob.matrix_world@v.co for ob in marker if ob.type=='MESH' for v in ob.data.vertices]
lo=Vector(tuple(min(p[i] for p in coords) for i in range(3))); hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
scale=1.8/(hi.z-lo.z)
for ob in marker:
    if ob.type!='MESH': ob.hide_render=True; continue
    # Bake evaluated static mesh for the source marker, keeping supplied actor data intact.
    dg=bpy.context.evaluated_depsgraph_get(); evaluated=ob.evaluated_get(dg); mesh=bpy.data.meshes.new_from_object(evaluated,depsgraph=dg); ob.modifiers.clear(); ob.data=mesh; world=ob.matrix_world.copy(); ob.parent=None
    for v in mesh.vertices: v.co=(world@v.co-Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z)))*scale+B((-3.80,0,1.25))
    ob.matrix_world.identity(); ob.name='Hall existing guard 1.8m scale reference'
bpy.ops.mesh.primitive_plane_add(size=180,location=(0,0,-.006)); floor=bpy.context.object; floor.name='Hall source review floor'; floor.data.materials.append(M['WardConcrete'])
world=bpy.data.worlds.get('Hall review world') or bpy.data.worlds.new('Hall review world'); scene.world=world; world.use_nodes=True; world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.19,.23,1); world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,p,power,size in [('Hall key',(9,17,12),3600,10),('Hall fill',(-10,12,-5),2800,9),('Hall rear fill',(3,8,-13),1700,7)]:
    light=bpy.data.lights.new(name,'AREA'); light.energy=power; light.shape='DISK'; light.size=size; ob=bpy.data.objects.new(name,light); scene.collection.objects.link(ob); ob.location=B(p); ob.rotation_euler=(B((0,6,-2))-ob.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Hall review camera'); cam=bpy.data.objects.new('Hall review camera',camd); scene.collection.objects.link(cam); scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=32; scene.cycles.use_denoising=True; scene.render.resolution_x=1600; scene.render.resolution_y=1200; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.view_settings.view_transform='AgX'
views=[('front',(15,10,25),(0,6,-1),48),('door',(3.7,1.65,5.1),(0,1.7,-.1),43),('door-left',(-6.4,1.75,2.1),(-2.15,1.72,-.15),48),('door-right',(6.4,1.75,2.1),(2.15,1.72,-.15),48),('left',(-16,6,-2.1),(0,5.4,-2.1),43),('right',(16,6,-2.1),(0,5.4,-2.1),43),('rear',(-12,7,-22),(0,5.9,-2.6),46),('rear-service',(-2.5,1.7,-9),(1.4,1.5,-3.95),43),('roof',(11,18,8),(0,9.9,-2.3),52)]
for index,(name,p,target,lens) in enumerate(views):
    cam.location=B(p); cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler(); camd.lens=lens; scene.render.filepath=str(O/('studio-'+name+'.png'))
    if index==0: bpy.data.libraries.write(str(O/'hall-repaired.blend'),{scene},fake_user=True,compress=True)
    bpy.ops.render.render(write_still=True)
print(json.dumps(report))
