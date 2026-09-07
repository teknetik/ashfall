"""Original Athen Hill asset authoring; execute through the live Blender MCP.

All helper inputs use Three.js metres: X east, Y up, Z south.
Blender conversion is (x, -z, y). Never use downloaded mesh assets.
"""
import bpy, math, random, json
from pathlib import Path
from mathutils import Vector

ROOT = Path('/Users/carl.draper/Documents/code/ao2')
random.seed(1707)
ACTIVE_LANDMARK = 'blockout'
AUTHORED = list(bpy.context.scene.get('authoredLandmarks', []))
PALETTE = {'stone':'C4A574','metal':'3A4149','dark':'272D30',
           'bark':'71634F','leaf':'4A5A32','grass':'626346',
           'red':'8B2E2E','cyan':'3EC7C2','rust':'815335'}

def xyz(p): return Vector((p[0],-p[2],p[1]))
def linear(v): return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4
def rgba(h): return tuple(linear(int(h[i:i+2],16)/255) for i in (0,2,4))+(1,)

def material(key):
    name='MAT_'+key
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=rgba(PALETTE[key])
    bs.inputs['Roughness'].default_value=.94 if key!='metal' else .83
    bs.inputs['Metallic'].default_value=.16 if key=='metal' else 0
    if key=='cyan':
        bs.inputs['Emission Color'].default_value=rgba(PALETTE[key])
        bs.inputs['Emission Strength'].default_value=.8
    m.diffuse_color=rgba(PALETTE[key])
    return m

MATS={key:material(key) for key in PALETTE}

def tag(obj,key,landmark=None):
    obj['landmark']=landmark or ACTIVE_LANDMARK
    obj.data.materials.clear(); obj.data.materials.append(MATS[key])
    return obj

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj

def planar_uv(obj,scale=4):
    uv=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UV0')
    for p in obj.data.polygons:
        n=p.normal; dominant=max(range(3),key=lambda j:abs(n[j]))
        axes=[j for j in range(3) if j!=dominant]
        for li in p.loop_indices:
            v=obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv=(v[axes[0]]/scale,v[axes[1]]/scale)

def mesh(name,verts,faces,key,uvs=None):
    data=bpy.data.meshes.new(name); data.from_pydata([xyz(v) for v in verts],[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(obj); tag(obj,key)
    if uvs:
        layer=data.uv_layers.new(name='UV0')
        for p in data.polygons:
            for li in p.loop_indices: layer.data[li].uv=uvs[data.loops[li].vertex_index]
    else: planar_uv(obj,4 if key!='stone' else 8)
    return obj

def box(name,pos,size,key='stone',bevel=.04,collision=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(pos))
    obj=bpy.context.object; obj.name=name; obj.scale=(size[0],size[2],size[1])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    tag(obj,key)
    if bevel:
        mod=obj.modifiers.new('authored_edge_bevel','BEVEL');mod.width=bevel;mod.segments=1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    planar_uv(obj,8 if key=='stone' else 3)
    if collision: collider(name,pos,size)
    return obj

def collider(name,pos,size,kind='box'):
    obj=box('COL_'+name,pos,size,'dark',0,False)
    obj['colliderKind']=kind;obj.hide_render=True;obj.display_type='WIRE'
    if kind=='cylinder': obj['colliderRadius']=size[0]/2;obj['colliderHalfHeight']=size[1]/2
    return obj

def tube(name,points,radii,key='bark',segments=10):
    if key=='bark' and segments>=9:
        source=[Vector(p) for p in points];smooth=[];rs=[]
        for i in range(len(source)-1):
            p0=source[max(0,i-1)];p1=source[i];p2=source[i+1];p3=source[min(len(source)-1,i+2)]
            for k in range(4):
                t=k/4
                smooth.append(tuple(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)))
                rs.append(radii[i]*(1-t)+radii[i+1]*t)
        smooth.append(tuple(source[-1]));rs.append(radii[-1]);points=smooth;radii=rs
    verts=[];faces=[];uvs=[];distance=0
    for i,p in enumerate(points):
        v=Vector(p)
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        tangent.normalize(); axis=tangent.cross(Vector((0,0,1)))
        if axis.length<.01:axis=tangent.cross(Vector((1,0,0)))
        axis.normalize(); second=tangent.cross(axis).normalized()
        if i:distance+=(v-Vector(points[i-1])).length
        for j in range(segments+1):
            angle=math.tau*j/segments
            r=radii[i]*(1+.065*math.sin(j*3.1+i*.6))
            q=v+(axis*math.cos(angle)+second*math.sin(angle))*r
            verts.append(tuple(q));uvs.append((j/segments*1.3,distance/5))
    for i in range(len(points)-1):
        for j in range(segments):
            a=i*(segments+1)+j;b=a+segments+1
            faces.append((a,a+1,b+1,b))
    faces.extend([tuple(reversed(range(segments))),tuple((len(points)-1)*(segments+1)+j for j in range(segments))])
    obj=mesh(name,verts,faces,key,uvs)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def ring(name,center,outer,inner,depth,key='stone',axis='z',segments=40,arc=math.tau):
    verts=[];faces=[]
    for j in range(segments+1):
        a=arc*j/segments
        for d,r in [(-depth/2,outer),(-depth/2,inner),(depth/2,outer),(depth/2,inner)]:
            local=(r*math.cos(a),r*math.sin(a),d)
            if axis=='x':local=(d,local[1],local[0])
            verts.append(tuple(center[k]+local[k] for k in range(3)))
    for j in range(segments):
        a=j*4;b=a+4
        faces.extend([(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)])
    faces.extend([(0,1,3,2),(segments*4,segments*4+2,segments*4+3,segments*4+1)])
    return mesh(name,verts,faces,key)

def label(name,text,pos,size=.35,width=3,turn=0,key='cyan'):
    bpy.ops.object.text_add(location=xyz(pos))
    ob=bpy.context.object;ob.name=name;ob.data.body=text;ob.data.align_x='CENTER';ob.data.size=size
    ob.data.extrude=.001;ob.data.resolution_u=2
    # Text lies in Blender XY; rotate upright facing Three +Z, optionally yaw.
    ob.rotation_euler=(math.pi/2,0,turn)
    ob['landmark']=ACTIVE_LANDMARK;ob.data.materials.append(MATS[key])
    bpy.ops.object.convert(target='MESH');planar_uv(ob,2)
    return ob

def save(stage):
    bpy.context.scene['authoredLandmarks']=AUTHORED
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/scenes'/stage),check_existing=False)

def export_world():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH' and obj.get('landmark') in AUTHORED:
            obj.hide_set(False);obj.select_set(True)
    bpy.context.scene['authoredLandmarks']=AUTHORED
    bpy.ops.export_scene.gltf(filepath=str(ROOT/'public/assets/world.glb'),export_format='GLB',
        use_selection=True,use_active_scene=True,export_yup=True,export_apply=True,export_extras=True,
        export_animations=False,export_cameras=False,export_lights=False,export_materials='EXPORT')
    (ROOT/'public/assets/world-manifest.json').write_text(json.dumps({'source':'world.glb','landmarks':AUTHORED},indent=2)+'\n')
    report={'landmarks':AUTHORED,'meshes':0,'triangles':0,'colliders':0,'materials':set()}
    for obj in bpy.context.selected_objects:
        if obj.type!='MESH':continue
        if obj.name.startswith('COL_'):report['colliders']+=1;continue
        report['meshes']+=1;report['triangles']+=sum(len(p.vertices)-2 for p in obj.data.polygons)
        report['materials'].update(m.name for m in obj.data.materials)
    report['materials']=sorted(report['materials'])
    (ROOT/'blender/world-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

def cameras_and_light():
    views={'cam_gate':((-32,9,18),(-48,3.4,5)),'cam_avenue':((-12,7,34),(0,9,-5)),
      'cam_hill':((23,14,27),(0,9,0)),'cam_grid':((-10,6,-28),(0,2,-38)),
      'cam_whompah':((13,6.5,26),(0,3,36)),'cam_hero':((-5,3.4,9),(0,9,0))}
    for name,(pos,target) in views.items():
        data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob)
        ob.location=xyz(pos);ob.rotation_euler=(xyz(target)-ob.location).to_track_quat('-Z','Y').to_euler()
        data.type='PERSP';data.sensor_fit='VERTICAL';data.sensor_height=24;data.lens=24/(2*math.tan(math.radians(50)/2))
    light=bpy.data.lights.new('SUN_west_golden','SUN');light.energy=3;light.angle=math.radians(3)
    sun=bpy.data.objects.new('SUN_west_golden',light);bpy.context.scene.collection.objects.link(sun)
    sun.location=xyz((-62,40,42));sun.rotation_euler=(-sun.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('Dusty_daylight');world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.39,.48,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.7;bpy.context.scene.world=world
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12
    scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'

def render_camera(name,folder='phase3'):
    scene=bpy.context.scene;scene.camera=bpy.data.objects[name]
    path=ROOT/'blender/previews'/folder;path.mkdir(parents=True,exist_ok=True)
    scene.render.filepath=str(path/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('Rendered '+scene.render.filepath)
