"""Author the empty artisan stall in a live Blender session via Blender MCP.

Source dimensions use metres, X width / Y depth / Z up; customers stand at -Y.
Creates only a new KA_ scene and its own named datablocks. No Unity operations.
"""
import bpy
import math
import json
import sys
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/karaveen_artisan_20260910')
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(OUT))
from artisan_materials import create_materials

SCENE_NAME = 'KA_Artisan_Stall_v01'
if bpy.data.scenes.get(SCENE_NAME):
    raise RuntimeError('Artisan scene already exists: inspect it before modifying or rerunning authoring.')
scene = bpy.data.scenes.new(SCENE_NAME)
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene['scope'] = 'Empty artisan stall, Blender only; merchandise intentionally absent.'
scene['authoring_transport'] = 'Blender MCP execute_blender_code'
scene['reference'] = 'refs/karaveen_market_20260910/modeling-v01/04-travelling-artisan-turnaround-v01.png'
M = create_materials()
collections = {}
for key, label in [('frame','01 Frame and fixings'), ('canvas','02 Canopy and sewn fittings'),
                   ('cabinet','03 Empty counter and cupboards'), ('shelf','04 Empty display fixtures'),
                   ('rig','05 Rig controls'), ('studio','90 Review studio')]:
    col = bpy.data.collections.new('KA_' + label)
    scene.collection.children.link(col)
    collections[key] = col

asset_objects = []
door_parts = {'L': [], 'R': []}

def register(obj, category, material=None, door=None):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collections[category].objects.link(obj)
    if material:
        obj.data.materials.append(M[material])
    obj['KA_component'] = category
    if category not in ('studio','rig'):
        asset_objects.append(obj)
        if door:
            door_parts[door].append(obj)
    return obj

def mesh_object(name, verts, faces, category, material, location=(0,0,0), bevel=0, door=None):
    mesh = bpy.data.meshes.new('KA_' + name + '_mesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('KA_' + name, mesh)
    obj.location = location
    register(obj, category, material, door)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        n = poly.normal
        axes = (0,1) if abs(n.z) > .7 else ((0,2) if abs(n.y) > .7 else (1,2))
        for li in poly.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv = (co[axes[0]], co[axes[1]])
    if bevel:
        b = obj.modifiers.new('Edge radii', 'BEVEL')
        b.width = bevel
        b.segments = 3
        b.limit_method = 'ANGLE'
        n = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
        n.keep_sharp = True
        n.weight = 35
    return obj

def box(name, loc, dims, category='frame', material='frame', bevel=.004, door=None):
    x,y,z = (v*.5 for v in dims)
    vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    fs=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return mesh_object(name,vs,fs,category,material,loc,bevel,door)

def tube(name, a, b, radius=.025, category='frame', material='frame', segments=24, door=None):
    a,b=Vector(a),Vector(b)
    depth=(b-a).length
    verts=[]
    for z in (-depth*.5,depth*.5):
        verts += [(radius*math.cos(i*2*math.pi/segments),radius*math.sin(i*2*math.pi/segments),z) for i in range(segments)]
    faces=[tuple(reversed(range(segments))),tuple(range(segments,segments*2))]
    faces += [(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    obj=mesh_object(name,verts,faces,category,material,(a+b)*.5,.0015,door)
    obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices)==4
    return obj

def paths(name, lines, radius, category, material, door=None):
    data=bpy.data.curves.new('KA_'+name+'_curves','CURVE')
    data.dimensions='3D'
    data.resolution_u=1
    data.bevel_depth=radius
    data.bevel_resolution=2
    for points in lines:
        s=data.splines.new('POLY')
        s.points.add(len(points)-1)
        for p,co in zip(s.points,points):p.co=(*co,1)
    obj=bpy.data.objects.new('KA_'+name,data)
    return register(obj,category,material,door)

def torus(name, center, major=.009, minor=.002, normal=(0,0,1), category='frame', material='brass', door=None):
    vs=[];fs=[];n=20;m=8
    q=Vector(normal).to_track_quat('Z','Y')
    for i in range(n):
        a=i*2*math.pi/n
        for j in range(m):
            b=j*2*math.pi/m
            co=q@Vector(((major+minor*math.cos(b))*math.cos(a),(major+minor*math.cos(b))*math.sin(a),minor*math.sin(b)))
            vs.append(tuple(co))
    for i in range(n):
        for j in range(m):fs.append((i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m))
    o=mesh_object(name,vs,fs,category,material,center,0,door)
    for f in o.data.polygons:f.use_smooth=True
    return o

def bolt(name, pos, normal=(0,0,1), size=.006, category='frame', door=None):
    p=Vector(pos);n=Vector(normal)
    torus(name+'_washer',p,major=size*1.15,minor=size*.2,normal=n,category=category,material='bare_steel',door=door)
    return tube(name+'_hex',p,p+n*size*.75,size,category,'brass',6,door)

def roof_z(x,y):
    u=(x+1.65)/3.3;v=(y+1.35)/2.7
    return 2.30+.35*v-.056*math.sin(math.pi*u)*math.sin(math.pi*v)+.004*math.sin(10*math.pi*u)*math.sin(math.pi*v)**2

# Four portable weighted feet, telescoping uprights and visible service fasteners.
for ix,x in enumerate((-1.50,1.50)):
    for iy,y in enumerate((-1.20,1.20)):
        tag=f'{ix}{iy}'
        top=roof_z(x,y)-.035
        box('Rubber_sole_'+tag,(x,y,.012),(.215,.215,.024),material='rubber',bevel=.01)
        box('Weighted_foot_'+tag,(x,y,.11),(.20,.20,.19),material='cabinet',bevel=.018)
        tube('Foot_socket_'+tag,(x,y,.15),(x,y,.31),.052)
        tube('Lower_upright_'+tag,(x,y,.22),(x,y,1.26),.034)
        tube('Upper_upright_'+tag,(x,y,1.19),(x,y,top+.025),.028)
        for z in (1.23,top-.10):
            tube('Split_clamp_'+tag+str(z),(x,y,z-.035),(x,y,z+.035),.043)
            box('Clamp_lugs_'+tag+str(z),(x,y-.042,z),(.10,.025,.05),material='bare_steel',bevel=.004)
            for dx in (-.034,.034):bolt('Clamp_bolt_'+tag+str(z)+str(dx),(x+dx,y-.058,z),(0,-1,0))
        for dx in (-.067,.067):
            for dy in (-.067,.067):bolt('Foot_bolt_'+tag+str(dx)+str(dy),(x+dx,y+dy,.21),size=.008)
        for sign in (-1,1):
            if sign*x<0:
                tube('Width_knee_'+tag,(x,y,top-.28),(x+sign*.28,y,roof_z(x+sign*.28,y)-.042),.015)
        sy=-1 if y>0 else 1
        tube('Depth_knee_'+tag,(x,y,top-.28),(x,y+sy*.28,roof_z(x,y+sy*.28)-.042),.015)

for y in (-1.20,1.20):
    tube('Width_top_rail_'+str(y),(-1.50,y,roof_z(-1.5,y)-.034),(1.50,y,roof_z(1.5,y)-.034),.029)
for x in (-1.50,-.75,0,.75,1.50):
    tube('Sloping_roof_rail_'+str(x),(x,-1.20,roof_z(x,-1.2)-.038),(x,1.20,roof_z(x,1.2)-.038),.024 if abs(x)==1.5 else .019)

# Sewn canvas surface and separate edge valances, with editable cloth topology.
def grid(name, nx, ny, point, category='canvas', material='canvas'):
    vs=[point(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    fs=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh_object(name,vs,fs,category,material)
    for p in o.data.polygons:p.use_smooth=True
    s=o.modifiers.new('Canvas thickness 2.5 mm','SOLIDIFY');s.thickness=.0025;s.offset=0
    return o

roof=grid('Tensioned_sand_canvas',72,56,lambda u,v:(-1.65+3.3*u,-1.35+2.7*v,roof_z(-1.65+3.3*u,-1.35+2.7*v)))
roof.shape_key_add(name='Basis')
billow=roof.shape_key_add(name='Soft billow')
for p in billow.data:
    x,y,z=p.co;u=(x+1.65)/3.3;v=(y+1.35)/2.7
    p.co.z+=.035*math.sin(math.pi*u)**2*math.sin(math.pi*v)**2*math.sin(3*math.pi*u+v)
roof['rig_notes']='Soft billow preserves all canopy perimeter attachment positions.'
front_valance=grid('Front_sewn_valance',80,10,lambda u,v:(-1.65+3.3*u,-1.35-.012*math.sin(14*math.pi*u)*v,roof_z(-1.65+3.3*u,-1.35)-v*(.21+.018*math.sin(math.pi*u))))
back_valance=grid('Rear_sewn_valance',80,6,lambda u,v:(-1.65+3.3*u,1.35+.009*math.sin(12*math.pi*u)*v,roof_z(-1.65+3.3*u,1.35)-v*.12))
for x in (-1.65,1.65):
    grid('Side_sewn_valance_'+str(x),60,6,lambda u,v,x=x:(x,-1.35+2.7*u,roof_z(x,-1.35+2.7*u)-v*.11))

seams=[];stitches=[]
for x in (-.55,.55):
    seams.append([(x,-1.34+2.68*j/64,roof_z(x,-1.34+2.68*j/64)+.003) for j in range(65)])
    for k in range(112):
        y=-1.31+k*.0234
        for dx in (-.006,.006):
            stitches.append([(x+dx,y,roof_z(x+dx,y)+.004),(x+dx,y+.009,roof_z(x+dx,y+.009)+.004)])
for y in (-1.34,1.34):seams.append([(-1.64+3.28*j/72,y,roof_z(-1.64+3.28*j/72,y)+.004) for j in range(73)])
for x in (-1.64,1.64):seams.append([(x,-1.34+2.68*j/64,roof_z(x,-1.34+2.68*j/64)+.004) for j in range(65)])
paths('Reinforced_canopy_seams',seams,.0028,'canvas','seam')
paths('Double_rows_of_stitching',stitches,.00065,'canvas','seam')
for k,(cx,cy,w,d) in enumerate([(-.95,.58,.29,.24),(.72,-.60,.24,.20),(.17,.96,.34,.18)]):
    grid('Stitched_roof_repair_'+str(k),10,8,lambda u,v,cx=cx,cy=cy,w=w,d=d:(cx+(u-.5)*w,cy+(v-.5)*d,roof_z(cx+(u-.5)*w,cy+(v-.5)*d)+.004),material='canvas_patch')
    border=[]
    for u,v in [(0,0),(1,0),(1,1),(0,1),(0,0)]:
        x=cx+(u-.5)*(w-.013);y=cy+(v-.5)*(d-.013);border.append((x,y,roof_z(x,y)+.008))
    paths('Patch_seam_'+str(k),[border],.0011,'canvas','seam')
for y in (-1.28,1.28):
    for k in range(9):
        x=-1.46+k*.365;z=roof_z(x,y)
        torus('Canopy_eyelet_'+str(y)+'_'+str(k),(x,y,z+.004),.010,.0025,(0,-.13,1),'canvas')
        bar_y=-1.2 if y<0 else 1.2
        paths('Canopy_tie_'+str(y)+'_'+str(k),[[(x,y,z+.01),(x+.009,bar_y,roof_z(x,bar_y)-.067),(x-.009,y,z+.012)]],.003,'canvas','rope')

# Empty two-cupboard service counter. Doors are genuinely separate articulated parts.
for side,cx in [('L',-.66),('R',.66)]:
    for x in (cx-.56,cx+.56):
        for y in (-1.075,-.595):box('Counter_foot_'+side+str(x)+str(y),(x,y,.095),(.08,.08,.19),'cabinet','frame',.005)
    box('Cupboard_floor_'+side,(cx,-.835,.20),(1.23,.59,.065),'cabinet','shelf')
    box('Cupboard_top_'+side,(cx,-.835,.867),(1.23,.59,.045),'cabinet','cabinet')
    box('Cupboard_back_'+side,(cx,-.550,.535),(1.23,.028,.64),'cabinet','cabinet')
    for x in (cx-.600,cx+.600):box('Cupboard_side_'+side+str(x),(x,-.835,.535),(.030,.60,.64),'cabinet','cabinet')
    box('Cupboard_internal_shelf_'+side,(cx,-.835,.51),(1.17,.56,.020),'cabinet','shelf')
    door=box('Cupboard_door_'+side,(cx,-1.155,.535),(1.16,.045,.625),'cabinet','cabinet',.009,side)
    door['opening']='Outward, 0 to 105 degrees; use rig custom property.'
    for z in (.265,.80):box('Door_horizontal_reinforcement_'+side+str(z),(cx,-1.184,z),(1.075,.018,.040),'cabinet','bare_steel',.003,side)
    for x in (cx-.505,cx+.505):box('Door_vertical_reinforcement_'+side+str(x),(x,-1.184,.535),(.035,.018,.52),'cabinet','bare_steel',.003,side)
    for dx in (-.505,.505):
        for z in (.27,.80):bolt('Door_rivet_'+side+str(dx)+str(z),(cx+dx,-1.199,z),(0,-1,0),.005,'cabinet',side)
    hx=cx+(.39 if side=='L' else -.39)
    for z in (.56,.68):box('Handle_mount_'+side+str(z),(hx,-1.208,z),(.05,.035,.04),'cabinet','brass',.003,side)
    paths('Cupboard_pull_'+side,[[(hx,-1.224,.56),(hx,-1.252,.58),(hx,-1.252,.66),(hx,-1.224,.68)]],.008,'cabinet','bare_steel',side)
    hinge_x=cx+(-.591 if side=='L' else .591)
    for z in (.34,.73):
        tube('Door_hinge_barrel_'+side+str(z),(hinge_x,-1.172,z-.04),(hinge_x,-1.172,z+.04),.013,'cabinet','bare_steel',16,side)
        box('Fixed_hinge_leaf_'+side+str(z),(hinge_x+(-.027 if side=='L' else .027),-1.172,z),(.045,.021,.066),'cabinet','bare_steel',.003)
        box('Moving_hinge_leaf_'+side+str(z),(hinge_x+(.026 if side=='L' else -.026),-1.191,z),(.043,.021,.066),'cabinet','bare_steel',.003,side)

box('Service_counter_top',(0,-.835,.926),(2.60,.65,.048),'cabinet','shelf',.009)
box('Counter_front_edge',(0,-1.166,.930),(2.60,.025,.052),'cabinet','bare_steel',.005)
box('Counter_rear_lip',(0,-.514,.949),(2.60,.016,.04),'cabinet','shelf',.002)
for x in (-1.29,1.29):box('Counter_end_trim_'+str(x),(x,-.835,.930),(.02,.65,.05),'cabinet','bare_steel',.003)

# Empty shelving and an empty textile-hanging rail; no pots, rugs, plants or loose stock.
sx,sy=.94,.945
for dx in (-.34,.34):
    for dy in (-.19,.19):tube('Shelf_upright_'+str(dx)+str(dy),(sx+dx,sy+dy,.04),(sx+dx,sy+dy,1.98),.018,'shelf')
for k,z in enumerate((.24,.72,1.20,1.68)):
    box('Empty_display_shelf_'+str(k),(sx,sy,z),(.73,.43,.028),'shelf','shelf',.004)
    box('Shelf_rear_lip_'+str(k),(sx,sy+.211,z+.035),(.73,.017,.075),'shelf','frame',.002)
    for dx in (-.34,.34):
        tube('Shelf_bracket_'+str(k)+str(dx),(sx+dx,sy+.16,z-.15),(sx+dx,sy-.15,z-.025),.01,'shelf')
        bolt('Shelf_bolt_'+str(k)+str(dx),(sx+dx,sy-.19,z+.026),size=.005,category='shelf')
tube('Empty_textile_display_rail',(-1.31,.99,1.96),(-.35,.99,1.96),.019,'shelf')
for x in (-1.31,-.35):tube('Display_rail_hanger_'+str(x),(x,.99,1.96),(x,.99,roof_z(x,.99)-.06),.011,'shelf')
for x in (-1.11,-.64):
    paths('Empty_display_hook_'+str(x),[[(x,.99,1.98),(x,.965,1.94),(x,.965,1.86),(x,.98,1.84),(x,1.00,1.855)]],.0035,'shelf','brass')

# Mechanical rig: parented rigid parts, two swing doors and a pinned canopy shape key.
arm=bpy.data.armatures.new('KA_Artisan_mechanical_rig_data')
rig=bpy.data.objects.new('KA_Artisan_Rig',arm)
register(rig,'rig')
bpy.context.view_layer.objects.active=rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root=arm.edit_bones.new('ROOT');root.head=(0,0,0);root.tail=(0,0,.45)
for side,cx in [('L',-.66),('R',.66)]:
    x=cx+(-.591 if side=='L' else .591)
    b=arm.edit_bones.new('Cupboard_'+side);b.head=(x,-1.172,.20);b.tail=(x,-1.172,.86);b.parent=root
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front=True
rig.display_type='WIRE'
arm.display_type='STICK'
for prop,description,maximum in [('left_door_open','Left cupboard opening in degrees',105),('right_door_open','Right cupboard opening in degrees',105),('canopy_billow','Small pinned-edge canvas billow, 0 to 1',1)]:
    rig[prop]=0.0
    rig.id_properties_ui(prop).update(min=0,max=maximum,soft_min=0,soft_max=maximum,description=description)
for side,prop,sign in [('L','left_door_open',-1),('R','right_door_open',1)]:
    p=rig.pose.bones['Cupboard_'+side];p.rotation_mode='XYZ'
    p.lock_location=(True,True,True);p.lock_scale=(True,True,True);p.lock_rotation=(True,False,True)
    d=p.driver_add('rotation_euler',1).driver;d.type='SCRIPTED'
    var=d.variables.new();var.name='angle';var.type='SINGLE_PROP';var.targets[0].id=rig;var.targets[0].data_path='["'+prop+'"]'
    d.expression=f'{sign} * angle * 0.017453292519943295'
bpy.context.view_layer.update()
for obj in asset_objects:
    bone='Cupboard_L' if obj in door_parts['L'] else 'Cupboard_R' if obj in door_parts['R'] else 'ROOT'
    matrix=obj.matrix_world.copy();obj.parent=rig;obj.parent_type='BONE';obj.parent_bone=bone;obj.matrix_world=matrix
d=billow.driver_add('value').driver;d.type='SCRIPTED'
v=d.variables.new();v.name='billow';v.type='SINGLE_PROP';v.targets[0].id=rig;v.targets[0].data_path='["canopy_billow"]';d.expression='billow'
rig['README']='Move/rotate ROOT in Pose Mode. Object custom properties: left_door_open/right_door_open 0–105 degrees; canopy_billow 0–1. No keyframes are baked.'

# Original reference packed into the file; fixtures remain independently editable.
reference=Path('/home/teknetik/code/ao2/refs/karaveen_market_20260910/modeling-v01/04-travelling-artisan-turnaround-v01.png')
im=bpy.data.images.load(str(reference),check_existing=True);im.pack();im.use_fake_user=True
notes=bpy.data.texts.new('KA_README')
notes.write('KARAVEEN ARTISAN STALL — EMPTY STRUCTURE\n\nBlender MCP authored source; metres, front -Y, Z up. Frame 3.00 x 2.40 m; canopy 3.30 x 2.70 m; top front 2.30 m / rear 2.65 m; front hanging valance bottom approx. 2.07 m; counter 0.95 m.\n\nSelect KA_Artisan_Rig: custom properties operate two cupboard doors and subtle pinned canopy billow. ROOT bone positions the entire stall. Doors are rigid parts, not deforming meshes.\n\nMerchandise intentionally omitted: no rugs, pots, plants, textiles, packs or stock. Empty shelf and empty hanging rail are fixtures.\n\nAll materials are editable procedural PBR. Source topology, solidify, bevels and UVMap preserved. Packed concept reference is available in Image Editor. Studio collection and cameras are review-only. No Unity import or runtime claim.\n')

# Neutral review studio, separate from the asset collection.
ground=box('Studio_ground',(0,0,-.07),(200,200,.12),'studio',None,0)
gm=bpy.data.materials.new('KA_Studio_Ground');gm.diffuse_color=(.30,.32,.32,1);gm.use_nodes=True;gm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.30,.32,.32,1);gm.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.9;ground.data.materials.append(gm)
world=bpy.data.worlds.new('KA_Studio_World');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.51,.60,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4;scene.world=world
for name,loc,power,size,color in [('Key',(-3.8,-4.5,6.0),1200,4.0,(1,.88,.74)),('Fill',(4,-1,4.0),950,4.0,(.78,.87,1)),('Rear',(0,4,5),1400,3.0,(1,.94,.83))]:
    light=bpy.data.lights.new('KA_'+name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=color
    o=bpy.data.objects.new('KA_'+name,light);register(o,'studio');o.location=loc;o.rotation_euler=(Vector((0,0,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
camera_specs={'Hero':((5.1,-6.7,3.65),(0,0,1.25),5.5),'Front':((0,-8,1.36),(0,0,1.36),4.0),'Right':((8,0,1.36),(0,0,1.36),3.6),'Back':((0,8,1.36),(0,0,1.36),4.0),'Detail':((2.8,-3.5,2.8),(.9,-.8,2.1),1.75)}
for name,(pos,target,scale) in camera_specs.items():
    data=bpy.data.cameras.new('KA_Camera_'+name);data.type='ORTHO';data.ortho_scale=scale
    cam=bpy.data.objects.new('KA_Camera_'+name,data);register(cam,'studio');cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
scene.camera=bpy.data.objects['KA_Camera_Hero']
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
gpu=[]
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:
        device.use=device.type!='CPU'
        if device.use:gpu.append(device.name)
    scene.cycles.device='GPU' if gpu else 'CPU'
except Exception:scene.cycles.device='CPU'
scene.render.resolution_x=1440;scene.render.resolution_y=1080;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=.35
scene.render.filepath=str(OUT/'artisan-stall-hero-v01.png')
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=6.2
        area.spaces.active.region_3d.view_location=(0,0,1.25)
        area.spaces.active.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
        area.spaces.active.shading.type='MATERIAL'
for o in bpy.context.selected_objects:o.select_set(False)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.context.view_layer.update()
manifest={'created':'2026-09-10','blender':bpy.app.version_string,'scene':scene.name,'file':str(OUT/'karaveen-artisan-stall-v01.blend'),'objects':len(asset_objects),'merchandise':False,'unity_imported':False,'gpu':gpu,'rig_controls':['ROOT','left_door_open','right_door_open','canopy_billow'],'dimensions_m':{'frame':[3,2.4],'canopy':[3.3,2.7],'roof_front':2.3,'roof_rear':2.65,'counter_height':.95},'meshes':sum(o.type=='MESH' for o in asset_objects),'source_vertices':sum(len(o.data.vertices) for o in asset_objects if o.type=='MESH'),'source_polygons':sum(len(o.data.polygons) for o in asset_objects if o.type=='MESH')}
(OUT/'authoring-manifest-v01.json').write_text(json.dumps(manifest,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'karaveen-artisan-stall-v01.blend'))
print(json.dumps(manifest))
