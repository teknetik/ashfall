"""Original eroded desert basin. Execute through the live Blender MCP addon.
The city exclusion rectangle and all original gameplay geometry remain intact.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, noise
ROOT = Path('/home/teknetik/code/ao2')
scene=bpy.data.scenes.new('AthenHill_DesertTerrain_20260908')
bpy.context.window.scene=scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1

def n(x,z,scale,seed=0):
    return noise.noise_vector(Vector((x*scale+seed,z*scale-seed,4.37)),noise_basis='PERLIN_ORIGINAL').x

def height(x,z):
    a=math.atan2(z,x);r=math.hypot(x,z)
    edge=min(62/max(abs(math.cos(a)),.0001),48/max(abs(math.sin(a)),.0001))
    t=max(0,r-edge)
    # Folded strata with angularly varying cliff fronts and low passes.
    front=39+12*math.sin(a*3+1.2)+8*math.sin(a*7-.8)
    summit=38+17*math.sin(a*3+.9)+12*math.sin(a*5-1.1)
    summit=max(17,summit)
    shoulder=math.exp(-((t-front-19)/39)**2)
    rise=max(0,min(1,(t-front+9)/19));rise=rise*rise*(3-2*rise)
    near=summit*shoulder*rise
    # Tall, staggered rear peaks, softened by distance in the Unity material.
    crest=145+23*math.sin(a*4+.7)
    far=math.exp(-((t-crest)/57)**2)*(61+29*math.sin(a*3-2)+17*math.sin(a*8+.6))
    distant=math.exp(-((t-278)/67)**2)*(68+27*math.sin(a*5+.2))
    base=max(near,far,distant)
    broad=n(x,z,.031,13)
    erosion=abs(n(x+14*n(x,z,.015),z,.085,31))
    fine=n(x,z,.17,17)
    # Coherent flutes cut into the front; stepped sediment shelves avoid smooth dunes.
    geological=(base*(.87+.20*broad)-erosion*min(9,base*.22)+fine*min(1.2,base*.035))
    stepped=geological-1.4*math.sin(geological*1.2)*min(1,base/25)
    apron=(2+3*n(x,z,.045,4))*min(1,t/15)
    blend=min(1,max(0,t/23));blend=blend*blend*(3-2*blend)
    return -1.8+max(apron,stepped)*blend*.66

mat=bpy.data.materials.new('Desert geological preview');mat.diffuse_color=(.43,.29,.16,1)
mat.use_nodes=True
p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.43,.29,.16,1);p.inputs['Roughness'].default_value=.93
rings=[0,28,46,53,61,72,135,169,210,263,405]
steps=256;sectors=8;objects=[]
# Preserve continuous normals at sector borders by differentiating the shared height function.
for sector in range(sectors):
    vertices=[];faces=[]
    columns=steps//sectors+1
    for ring,t in enumerate(rings):
        for j in range(columns):
            a=math.tau*(sector*(columns-1)+j)/steps
            edge=min(62/max(abs(math.cos(a)),.0001),48/max(abs(math.sin(a)),.0001))
            r=edge+t;x=math.cos(a)*r;z=math.sin(a)*r
            vertices.append((x,-z,height(x,z)))
    for row in range(len(rings)-1):
        for j in range(columns-1):
            v=row*columns+j
            faces.extend([(v,v+1,v+columns),(v+1,v+columns+1,v+columns)])
    mesh=bpy.data.meshes.new('DesertBasin_%02d'%sector);mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(obj);objects.append(obj)
    obj.data.materials.append(mat)
    for face in mesh.polygons:face.use_smooth=True
    uv=mesh.uv_layers.new(name='UV0')
    for loop in mesh.loops:
        x,z,y=vertices[loop.vertex_index];uv.data[loop.index].uv=(x/16,z/16)
    obj['original_asset']='Athen Hill procedural eroded sandstone basin'
    obj['city_exclusion']='x=62m, z=48m; render only, no collision'
# Area-weighted shared vertex normals respect the actual exported geometry.
shared={}
for obj in objects:
    for face in obj.data.polygons:
        v=[obj.data.vertices[k].co for k in face.vertices]
        weighted=(v[1]-v[0]).cross(v[2]-v[0])
        for k in face.vertices:
            key=tuple(round(c,4) for c in obj.data.vertices[k].co)
            shared[key]=shared.get(key,Vector((0,0,0)))+weighted
for obj in objects:
    obj.data.normals_split_custom_set_from_vertices([shared[tuple(round(c,4) for c in v.co)].normalized() for v in obj.data.vertices])
# Bake geological sun occlusion and sky access into vertex colours. The Unity sun
# is fixed at (35,-35,0); source X is reflected by glTFast on import.
for obj in objects:
    attr=obj.data.color_attributes.new(name='TerrainLight',type='FLOAT_COLOR',domain='POINT')
    for index,v in enumerate(obj.data.vertices):
        x,minusz,y=v.co;z=-minusz
        obstruction=0
        for step in (3,6,10,16,24,36,52,75,105):
            obstruction=max(obstruction,height(x-.46985*step,z-.67101*step)-y-.57358*step-1.2)
        sun_visibility=1-min(1,max(0,obstruction)/2)
        occlusion=0
        for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
            horizon=max((height(x+dx*d,z+dz*d)-y)/d for d in (8,20,45))
            occlusion+=max(0,min(1,horizon))*.055
        attr.data[index].color=(sun_visibility,1-occlusion,1,1)
# Simple native Blender evidence; Unity is the final appearance authority.
world=bpy.data.worlds.new('Desert overcast');world.use_nodes=True
world.node_tree.nodes.get('Background').inputs[0].default_value=(.5,.61,.72,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.4;scene.world=world
light=bpy.data.lights.new('Late sun','SUN');light.energy=2.5;light.angle=.04
lo=bpy.data.objects.new('Late sun',light);scene.collection.objects.link(lo);lo.rotation_euler=(.6,-.3,-.7)
cam=bpy.data.cameras.new('Terrain review');co=bpy.data.objects.new('Terrain review',cam);scene.collection.objects.link(co)
co.location=(4,-20,12);target=Vector((0,165,37));co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler();cam.lens=24;scene.camera=co
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
output=ROOT/'unity/AthenHill/Assets/AthenHill/Art/Terrain/DesertBasin.glb'
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,use_active_scene=True,export_cameras=False,export_lights=False,export_normals=True,export_vertex_color='NAME',export_vertex_color_name='TerrainLight',export_all_vertex_colors=False,export_materials='EXPORT')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/scenes/18_desert_terrain.blend'))
triangles=sum(len(o.data.polygons) for o in objects)
report={'sectors':sectors,'triangles':triangles,'method':'live Blender MCP; original eroded heightfield','innerExclusion':[62,48],'outerRadius':480,'bounds':[list(min(v[k] for o in objects for v in [vert.co for vert in o.data.vertices]) for k in range(3)),list(max(v[k] for o in objects for v in [vert.co for vert in o.data.vertices]) for k in range(3))]}
(ROOT/'unity/evidence/terrain/20260908/blender-authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
scene.render.filepath=str(ROOT/'blender/previews/terrain-20260908.png');bpy.ops.render.render(write_still=True)
