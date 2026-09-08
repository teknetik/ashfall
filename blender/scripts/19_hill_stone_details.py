"""Small original chipped stones, exclusively in the planted hill quadrants."""
import bpy,math,random,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('/home/teknetik/code/ao2')
scene=bpy.data.scenes.new('AthenHill_HillStones');bpy.context.window.scene=scene
scene.unit_settings.system='METRIC'
random.seed(882)
material=bpy.data.materials.new('Hill stone preview');material.diffuse_color=(.42,.35,.25,1)
parts=[]
for i in range(32):
    x=random.choice([-1,1])*random.uniform(2.2,6.4)
    z=random.choice([-1,1])*random.uniform(2.2,6.4)
    # Terminal feet and Linn's standing patch, in source coordinates.
    if any(math.hypot(x-a,z-b)<1.1 for a,b in [(-5,-4),(5,-4),(5,1),(-2.5,4.7)]):continue
    radius=random.uniform(.14,.35)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(x,-z,1.49))
    obj=bpy.context.object;obj.name='Hill stone %02d'%i
    obj.scale=(radius, radius*random.uniform(.63,1.4),radius*random.uniform(.43,.75))
    obj.rotation_euler=(random.uniform(-.12,.12),random.uniform(-.12,.12),random.uniform(0,math.tau))
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for v in obj.data.vertices:v.co*=random.uniform(.88,1.11)
    obj.data.materials.append(material);parts.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for p in parts:p.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();obj=bpy.context.object;obj.name='Hill weathered stones'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Terrain/HillStones.glb'),export_format='GLB',use_selection=True,use_active_scene=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/scenes/19_hill_stones.blend'))
print(json.dumps({'originalStones':len(parts),'triangles':len(obj.data.polygons)}))
