"""Author six measured Ward shop variants through the live Blender MCP.

Reuses construction and physical material helpers, never scales a whole building
to another parcel. Sources stay separate from Unity prefabs and rejected meshes.
"""
import bpy, bmesh, ast, math, json, random
from pathlib import Path
from mathutils import Vector

R = Path('/home/teknetik/code/ao2')
O = R/'art/quality_20260909/relay-family/store-variants-01'
assert not O.exists(), 'Keep existing source revisions; do not regenerate over edits.'
O.mkdir()
helpers = ast.parse((O.parent/'author_relay.py').read_text())
allowed = {'B','U','finish','box','cyl','tube','pipe','ring','plate','proxy','masonry_pier','louver','door','canopy','bolt'}
for node in helpers.body:
    if isinstance(node, ast.FunctionDef) and node.name in allowed:
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'retained Ward construction helper', 'exec'))
names = ['WardPlaster','WardStone','WardConcrete','WardWornSteel','WardPaint','WardSteel','WardBrass','WardRubber','WardCloth','WardGlass','WardLetter','WardGasket','WardLampGlass','WardScale']
with bpy.data.libraries.load(str(O.parent/'revision-02/relay-architecture.blend'), link=False) as (src, dst):
    dst.materials = ['Relay_'+n for n in names]
M = dict(zip(names, dst.materials))
assert all(M.values())
tile = {n: .75 for n in names}
tile.update(WardPlaster=3, WardStone=2, WardConcrete=1.23, WardWornSteel=2, WardCloth=.4, WardGlass=1, WardLetter=1, WardGasket=1, WardLampGlass=1, WardScale=1)
palettes = {'air_water':(.075,.16,.14),'field_supply':(.30,.21,.095),'repairs':(.15,.19,.20),'salvage':(.25,.09,.045),'thread_hide':(.22,.075,.11),'tool_exchange':(.12,.16,.11)}
for key, col in palettes.items():
    name='WardCloth_'+key; m=M['WardCloth'].copy();m.name=name
    m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*col,1)
    M[name]=m;tile[name]=.4

def solid(name, points, faces, mat='WardPaint', bevel=.008, thickness=0):
    me=bpy.data.meshes.new(name);me.from_pydata([B(p) for p in points],[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob=finish(ob,name,mat,bevel)
    if thickness:
        mod=ob.modifiers.new('Physical surface thickness','SOLIDIFY');mod.thickness=thickness
        bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob

def lettering(name, words, pos, width, height=.26):
    c=bpy.data.curves.new(name,'FONT');c.body=words;c.align_x='CENTER';c.align_y='CENTER';c.size=1;c.extrude=.002;c.bevel_depth=.0006;c.resolution_u=6
    c.font=bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf',check_existing=True)
    ob=bpy.data.objects.new(name,c);scene.collection.objects.link(ob);ob.location=B(pos);ob.rotation_euler=(math.pi/2,0,0)
    ob=finish(ob,name,'WardLetter');bpy.context.view_layer.update()
    points=[ob.matrix_world@Vector(v)for v in ob.bound_box]
    scale=min(width/(max(p.x for p in points)-min(p.x for p in points)),height/(max(p.z for p in points)-min(p.z for p in points)))
    ob.scale*=scale
    return ob

def wall(name, axis, at, lo, hi, height, openings=(), mat='WardPlaster'):
    # Partition around actual recesses; the rectangle slots do not cover a solid wall.
    xs=sorted(set([lo,hi]+[v for o in openings for v in o[:2]]))
    ys=sorted(set([0,height]+[v for o in openings for v in o[2:]]))
    for i,(a,b) in enumerate(zip(xs,xs[1:])):
        for j,(c,d) in enumerate(zip(ys,ys[1:])):
            x=(a+b)/2;y=(c+d)/2
            if any(q[0]<x<q[1] and q[2]<y<q[3]for q in openings):continue
            pos=(x,y,at)if axis=='z'else(at,y,x)
            size=(b-a,d-c,.28)if axis=='z'else(.28,d-c,b-a)
            box(name+f' segment {i} {j}',pos,size,mat,.012)

def shell(height, openings, wallmat='WardPlaster'):
    global group
    group='Masonry shell'
    wall('Front masonry','z',2.59,-3.62,3.62,height,openings,wallmat)
    wall('Rear masonry','z',-4.23,-3.62,3.62,height,(),wallmat)
    for x in [-3.66,3.66]:
        box('Full wall return '+str(x),(x,height/2,-.82),(.28,height,7.10),wallmat,.015)
        for z in [2.60,-4.20]:masonry_pier('Corner quoin '+str((x,z)),x,z,.43,.43,height)
    box('Closed floor',(0,.035,-.8),(7.15,.07,6.7),'WardConcrete',.01)
    for x in [-3.55,3.55]:proxy('Side wall '+str(x),(x,height/2,-.8),(.45,height,7.1))
    proxy('Rear wall',(0,height/2,-4.22),(7.6,height,.35))
    proxy('Front closed shop wall',(0,height/2,2.55),(7.6,height,.30))
    # Current shops have closed doors; the existing porch/step colliders remain external.

def flat_roof(height, width=7.65, depth=7.35, center=-.8, coping=True):
    global group
    group='Roof construction'
    box('Roof bearing slab',(0,height+.055,center),(width,.11,depth),'WardConcrete',.025)
    for i in range(6):box('Seamed roof pan '+str(i),(-width/2+(i+.5)*width/6,height+.121,center),(width/6-.024,.024,depth-.18),'WardPaint',.006)
    if coping:
        for z in [center-depth/2+.05,center+depth/2-.05]:
            box('Parapet curb '+str(z),(0,height+.27,z),(width,.31,.18),'WardPlaster',.016)
            for i in range(8):box('Separate coping '+str((z,i)),(-width/2+(i+.5)*width/8,height+.452,z),(width/8-.012,.08,.30),'WardStone',.012)
        for x in [-width/2+.06,width/2-.06]:box('Side coping '+str(x),(x,height+.37,center),(.25,.27,depth),'WardStone',.016)

def window(name,x,y,width,height,z=2.64):
    global group
    group='Window and reveals'
    box(name+' dark recess',(x,y,z-.17),(width,height,.07),'WardGasket',.005)
    for sx in [-1,1]:box(name+' mineral reveal '+str(sx),(x+sx*(width/2+.065),y,z),(.13,height+.26,.35),'WardStone',.014)
    for sy in [-1,1]:box(name+' dressed sill '+str(sy),(x,y+sy*(height/2+.07),z+.03),(width+.30,.14,.41),'WardStone',.014)
    for i in range(max(1,round(width/.65))):
        n=max(1,round(width/.65));cx=x-width/2+(i+.5)*width/n
        box(name+' glass '+str(i),(cx,y,z-.08),(width/n-.065,height-.10,.035),'WardGlass',.003)
        box(name+' mullion '+str(i),(cx-width/n/2+.015,y,z-.04),(.035,height,.07),'WardPaint',.004)

def shutter(x,width,height,z=2.66):
    global group
    group='Workshop shutter'
    box('Shutter recessed backing',(x,height/2,z-.15),(width,height,.08),'WardGasket',.008)
    for sx in [-1,1]:
        box('Shutter masonry reveal '+str(sx),(x+sx*(width/2+.09),height/2,z-.035),(.18,height,.35),'WardStone',.017)
        box('Shutter guide rail '+str(sx),(x+sx*(width/2-.02),height/2,z+.02),(.085,height,.15),'WardSteel',.005)
    for i in range(round(height/.14)):
        hh=height/round(height/.14);box('Rolled shutter slat '+str(i),(x,(i+.5)*hh,z-.035),(width-.14,hh-.012,.06),'WardPaint',.008)
    box('Shutter drum casing',(x,height+.16,z),(width+.30,.32,.40),'WardSteel',.02)
    box('Shutter ground rail',(x,.045,z+.005),(width,.09,.10),'WardSteel',.008)
    for xx in [x-.55,x+.55]:tube('Shutter lift handle '+str(xx),[(xx-.13,.82,z+.005),(xx-.13,.82,z+.09),(xx+.13,.82,z+.09),(xx+.13,.82,z+.005)],.018,'WardBrass')

def sign(title, y, width=5.7, x=0):
    global group
    group='Separate shop signage'
    plate('Shop sign frame',(x,y,2.88),(width,.49,.095),'WardPaint')
    box('Shop sign face',(x,y,2.936),(width-.16,.35,.021),'WardGasket',.005)
    lettering('Exact shop name',title,(x,y,2.955),width-.40,.265)

def shade(width=5.8,offset=0,height=2.85):
    start=len(objects);canopy(width=width,front=4.18,rear=2.78,height=height)
    for o in objects[start:]:
        o.location+=B((offset,0,0))
        if o['region']=='WardCloth':o['region']='WardCloth_'+family;o.data.materials[0]=M[o['region']]

def services(height):
    global group
    group='Attached services'
    x=3.83;z=-3.70
    pipe('Rainwater pipe',(x,.30,z),(x,height+.17,z),.055,'WardBrass')
    for y in [.48,1.90,height-.6]:
        box('Rainwater stand-off '+str(y),(3.71,y,z),(.24,.10,.14),'WardSteel',.004)
        ring('Pipe clamp '+str(y),(x,y,z),.060,.009,'WardSteel',axis=(0,1,0))
    tube('Rainwater discharge shoe',[(x,.30,z),(x,.16,z-.13),(x,.16,z-.33)],.055,'WardBrass')
    # Rear louvre and service hatch make the full back useful at player height.
    start=len(objects);louver('Rear service vent',(0,1.60,4.40),1.38,.72,.18)
    for o in objects[start:]:o.matrix_world=__import__('mathutils').Matrix.Rotation(math.pi,4,'Z')@o.matrix_world
    box('Side power cabinet',(-3.86,1.42,.20),(.22,.65,.54),'WardPaint',.014)
    for y in [1.05,1.85,2.65]:box('Power conduit anchor '+str(y),(-3.76,y,.20),(.18,.085,.15),'WardSteel',.004)
    pipe('Side power conduit',(-3.87,.20,.20),(-3.87,height-.35,.20),.025,'WardSteel')

def pitched_roof(height, rise=.8):
    global group
    group='Pitched metal roof'
    for side in [-1,1]:
        points=[(0,height+rise,-4.48),(side*3.94,height,-4.48),(side*3.94,height,2.95),(0,height+rise,2.95)]
        solid('Roof sloped structural face '+str(side),points,[(0,1,2,3)],'WardPaint',0,.10)
        for i in range(13):
            z=-4.45+i*7.38/12
            tube('Roof standing seam '+str((side,i)),[(0,height+rise+.015,z),(side*3.94,height+.015,z)],.018,'WardSteel')
        for z in [-4.47,2.94]:pipe('Roof edge fascia '+str((side,z)),(0,height+rise,z),(side*3.94,height,z),.08,'WardSteel')
    pipe('Roof ridge cap',(0,height+rise+.025,-4.53),(0,height+rise+.025,3),.072,'WardBrass')
    solid('Front gable',[(-3.74,height-.03,2.65),(3.74,height-.03,2.65),(0,height+rise-.04,2.65)],[(0,1,2)],'WardPlaster',0,.20)
    solid('Rear gable',[(-3.74,height-.03,-4.25),(0,height+rise-.04,-4.25),(3.74,height-.03,-4.25)],[(0,1,2)],'WardPlaster',0,.20)

def tank(x,base,r=.78,h=1.85):
    global group
    group='Water storage and filtration'
    for dx in [-.47,.47]:
        box('Tank saddle '+str((x,dx)),(x+dx,base+.14,-1.75),(.17,.28,1.9),'WardSteel',.008)
    cyl('Riveted water vessel '+str(x),(x,base+.36+h/2,-1.75),r,h,'WardPaint',verts=64,bevel=.025)
    for y in [base+.36,base+.36+h*.5,base+.36+h]:
        ring('Vessel seam band '+str((x,y)),(x,y,-1.75),r+.012,.033,'WardSteel',axis=(0,1,0))
    cyl('Tank lid '+str(x),(x,base+.39+h,-1.75),r-.015,.08,'WardSteel',verts=64,r2=.53,bevel=.014)
    cyl('Inspection cap '+str(x),(x,base+.51+h,-1.75),.21,.16,'WardBrass',verts=40,bevel=.014)
    pipe('Vessel feed '+str(x),(x,base+.44,-.98),(x,base+.44,.80),.085,'WardBrass')
    for z in [-.7,.65]:ring('Feed flange '+str((x,z)),(x,base+.44,z),.12,.025,'WardSteel',axis=(0,0,1))

def build(kind):
    global group
    if kind=='air_water':
        h=6.5;shell(h,[(-2.15,-.45,0,2.3),(-2.55,2.55,4.5,5.55)])
        door('Service entry',-1.3,2.64,1.70);window('Upper filter gallery',0,5.025,5.1,1.05);flat_roof(h)
        for x in [-1.7,1.7]:tank(x,h+.14)
        group='Front filter bank'
        for x in [.9,1.7,2.5]:
            cyl('Filter canister '+str(x),(x,1.24,2.93),.25,1.48,'WardSteel',verts=40)
            for y in [.52,1.94]:ring('Filter retainer '+str((x,y)),(x,y,2.93),.265,.026,'WardBrass',axis=(0,1,0))
            box('Filter wall mount '+str(x),(x,1.3,2.70),(.13,1.8,.26),'WardPaint',.008)
        pipe('Filter manifold',(.55,2.1,2.98),(2.85,2.1,2.98),.055,'WardBrass')
        shade(3.45,-1.35);sign('AIR + WATER',3.7);services(h)
    elif kind=='field_supply':
        h=4.35;shell(h,[(-1.75,1.75,0,2.8),(-3.1,-2.15,0,2.25)])
        shutter(0,3.5,2.8);door('Staff door',-2.63,2.64,.92,2.25);pitched_roof(h,.85);sign('FIELD SUPPLY',3.65)
        group='Loading canopy structure'
        for x in [-3.3,3.3]:
            box('Front canopy post '+str(x),(x,1.48,4.12),(.12,2.96,.12),'WardSteel',.012)
            box('Post base shoe '+str(x),(x,.08,4.12),(.28,.16,.28),'WardPaint',.012)
            pipe('Canopy side beam '+str(x),(x,3.02,2.75),(x,3.02,4.24),.065,'WardSteel')
        box('Loading roof',(0,3.075,3.50),(6.88,.08,1.63),'WardPaint',.014)
        for i in range(12):box('Loading roof seam '+str(i),(-3.2+i*.58,3.13,3.50),(.025,.028,1.62),'WardSteel',.002)
        services(h)
    elif kind=='repairs':
        h=4.90;shell(h,[(-2.85,.85,0,2.75),(1.65,2.70,0,2.3)])
        shutter(-1,3.7,2.75);door('Workshop entry',2.18,2.64,1.04);flat_roof(h, coping=False);sign('REPAIRS',3.55,4.2,-.7)
        group='Raised workshop ventilation'
        box('Roof monitor base',(.2,5.30,-1.7),(5.25,.74,2.25),'WardPlaster',.022)
        louver('Monitor front louvres',(.2,5.38,-.5),4.78,.42,.14)
        box('Monitor sloped cap',(.2,5.77,-1.7),(5.70,.15,2.7),'WardPaint',.022)
        cyl('Exhaust duct',(2.72,5.9,-3.35),.23,1.6,'WardSteel',verts=40)
        cyl('Exhaust rain cap',(2.72,6.79,-3.35),.40,.13,'WardPaint',verts=40,r2=.28)
        for y in [5.35,6.3]:ring('Exhaust seam '+str(y),(2.72,y,-3.35),.25,.026,'WardBrass',axis=(0,1,0))
        shade(4,-.7);services(h)
    elif kind=='salvage':
        h=6.45;shell(h,[(-1,1,0,2.3),(-2.30,-.90,4.5,5.6),(.55,2.35,4.35,5.6)])
        door('Heavy salvage entry',0,2.64,2.0);window('Loft narrow light',-1.60,5.05,1.4,1.1);window('Loft loading light',1.45,4.975,1.8,1.25)
        pitched_roof(h,1.48);sign('SALVAGE',3.75);shade(4.45,-.7)
        group='Reclaimed facade cladding'
        for i in range(5):
            x=-2.8+i*1.4
            plate('Reclaimed skirt '+str(i),(x,1.25,2.805),(.56 if abs(x)<1.2 else 1.05,1.9,.07),'WardWornSteel'if i in[0,4]else'WardPaint') if abs(x)>1.2 else None
        group='Loft lifting bracket'
        box('Hoist wall anchor',(2.65,5.62,2.91),(.25,1.16,.15),'WardSteel',.012)
        pipe('Hoist beam',(2.65,6.05,2.9),(2.65,6.05,4.15),.09,'WardSteel')
        pipe('Hoist diagonal',(2.65,5.18,2.95),(2.65,6.05,4.0),.056,'WardSteel')
        ring('Hoist rope pulley',(2.65,5.96,4.06),.16,.035,'WardBrass',axis=(1,0,0))
        tube('Hoist hanging cable',[(2.65,5.89,4.13),(2.65,4.83,4.13)],.013,'WardRubber');services(h)
    elif kind=='thread_hide':
        h=6.35; openings=[(-.85,.85,0,2.3)]+[(x-.36,x+.36,4.45,5.65)for x in[-2.1,0,2.1]]
        shell(h,openings);door('Textile shop entry',0,2.64,1.7)
        for x in [-2.1,0,2.1]:window('Narrow atelier light '+str(x),x,5.05,.72,1.2)
        flat_roof(h);shade(6);sign('THREAD + HIDE',3.65)
        group='Rooftop drying frame'
        for x in [-2.65,2.65]:
            for z in [-3.45,.95]:
                box('Drying frame foot '+str((x,z)),(x,6.54,z),(.32,.12,.32),'WardConcrete',.012)
                pipe('Drying frame upright '+str((x,z)),(x,6.60,z),(x,7.82,z),.038,'WardSteel')
            pipe('Drying side rail '+str(x),(x,7.82,-3.45),(x,7.82,.95),.042,'WardBrass')
        for z in [-3.45,-1.95,-.45,.95]:
            pipe('Textile drying rail '+str(z),(-2.65,7.82,z),(2.65,7.82,z),.029,'WardSteel')
        for i,x in enumerate([-1.55,-.25,1.1]):
            solid('Hanging cloth length '+str(i),[(x-.48,7.78,-1.93),(x+.48,7.78,-1.93),(x+.47,6.82,-1.82),(x-.45,6.91,-1.82)],[(0,1,2,3)],'WardCloth_'+family,0,.005)
        services(h)
    else:
        h=5.40;shell(h,[(-.7,2.75,0,2.75),(-2.90,-1.4,.78,2.2),(-2.80,2.80,4.1,4.75)])
        shutter(1.025,3.45,2.75);window('Recessed tool display',-2.15,1.49,1.50,1.42);window('Workshop clerestory',0,4.425,5.60,.65)
        flat_roof(h, coping=False);sign('TOOL EXCHANGE',3.42);shade(3.9,1.0,height=2.96)
        group='Roof utility monitor'
        box('Monitor masonry base',(-1.6,5.90,-2.15),(2.40,.85,2.15),'WardPlaster',.014)
        louver('Monitor slatted return',(-1.6,6.0,-.99),2.1,.45,.13)
        box('Monitor protected lid',(-1.6,6.38,-2.15),(2.7,.15,2.45),'WardPaint',.016);services(h)

def export():
    data=[]
    for ob in objects:
        me=ob.data;me.calc_loop_triangles();vs=[];ns=[];uv=[];ii=[];unique={};nm=ob.matrix_world.to_3x3().inverted().transposed()
        for tri in me.loop_triangles:
            for li in tri.loops:
                p=U(ob.matrix_world@me.vertices[me.loops[li].vertex_index].co);n=U((nm@me.corner_normals[li].vector).normalized());t=[round(float(v),6)for v in me.uv_layers.active.data[li].uv];key=tuple(p+n+t)
                if key not in unique:unique[key]=len(vs);vs.append(p);ns.append(n);uv.append(t)
                ii.append(unique[key])
        data.append(dict(name=ob.name,family=family,group=ob['group'],material=ob['region'],positions=vs,normals=ns,uv=uv,indices=ii))
    return data

allparts=[];allproxies=[];reports=[]
for family in palettes:
    scene=bpy.data.scenes.new('Ward '+family+' authored source');bpy.context.window.scene=scene
    objects=[];proxies=[];group='Structure';rng=random.Random('Ward '+family)
    build(family);bpy.context.view_layer.update();data=export();allparts+=data;allproxies+=proxies
    folder=O/family;folder.mkdir();(folder/'meshes.json').write_text(json.dumps(data,separators=(',',':')))
    (folder/'collider-proxies.json').write_text(json.dumps(proxies,indent=2))
    reports.append(dict(id=family,parts=len(data),triangles=sum(len(p['indices'])//3 for p in data),status='Authored source, requires individual visual and native review'))
    # Clearly separate the studio floor and metric marker from exported architecture.
    group='Review only';family_for_parts=family;family='review'
    box('1.8m height marker',(-4.60,.9,3.4),(.07,1.8,.07),'WardScale',.003)
    for y in [0,.5,1,1.5,1.8]:box('Scale tick '+str(y),(-4.60,y,3.4),(.28,.015,.04),'WardLetter',.001)
    family=family_for_parts
    bpy.ops.mesh.primitive_plane_add(size=150,location=(0,0,-.035));floor=bpy.context.object;floor.data.materials.append(M['WardConcrete'])
    for li in range(len(floor.data.loops)):
        p=floor.data.vertices[floor.data.loops[li].vertex_index].co;floor.data.uv_layers.active.data[li].uv=(p.x/1.23,p.y/1.23)
    world=bpy.data.worlds.new(family+' studio sky');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.20,.26,.36,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
    light=bpy.data.lights.new(family+' sun','SUN');light.energy=2.5;light.angle=.02;ob=bpy.data.objects.new('Source sun',light);scene.collection.objects.link(ob);ob.rotation_euler=(.6,-.45,-.50)
    light=bpy.data.lights.new(family+' fill','AREA');light.energy=2100;light.size=12;ob=bpy.data.objects.new('Source sky fill',light);scene.collection.objects.link(ob);ob.location=B((-7,8,10));ob.rotation_euler=(B((0,3,0))-ob.location).to_track_quat('-Z','Y').to_euler()
    camd=bpy.data.cameras.new(family+' source camera');cam=bpy.data.objects.new('Source camera',camd);scene.collection.objects.link(cam);scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    bpy.data.libraries.write(str(folder/'source.blend'),{scene},fake_user=True,compress=True)
    print(json.dumps(reports[-1]),flush=True)
(O/'store-meshes.json').write_text(json.dumps(allparts,separators=(',',':')))
(O/'collider-proxies.json').write_text(json.dumps(allproxies,indent=2))
(O/'manifest.json').write_text(json.dumps({'source':'Original metric Blender construction through live MCP','families':reports,'clothTints':palettes,'coordinateConvention':'Interchange X/Z/-Y; Unity must reflect X and reverse triangle indices','sourceOnly':True},indent=2))
print('Six separate architectural source variants authored; no Unity installation.')
