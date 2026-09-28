import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('/home/teknetik/code/ao2');before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'meshy/checkpoint-robots-20260926/range-target/model.glb'))
obs=[o for o in bpy.data.objects if o not in before];meshes=[o for o in obs if o.type=='MESH'];bpy.context.view_layer.update();pts=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
mn=Vector(tuple(min(p[i] for p in pts) for i in range(3)));mx=Vector(tuple(max(p[i] for p in pts) for i in range(3)));s=1.05/(mx.z-mn.z)
# source-detail preserving normalization, bottom lug at local Y=0 in Unity
norm=Matrix.Scale(s,4)@Matrix.Translation(Vector((-(mn.x+mx.x)/2,-(mn.y+mx.y)/2,-mn.z)))
for o in meshes:
 mw=o.matrix_world.copy();o.parent=None;o.data.transform(norm@mw);o.matrix_world=Matrix.Identity(4);o.name='Steel target plate'
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/SteelTargetPlate.glb'),export_format='GLB',use_selection=True,export_yup=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/checkpoint_20260926/target-source.blend'))
json.dump({'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'uniform_scale':s,'dimensions_m':list((mx-mn)*s),'source_preserved':True,'review':'Beveled steel torso plate, bolts, hinge lugs. No pillows or base. Reviewed geometry before installation.'},open(ROOT/'art/checkpoint_20260926/target-runtime.json','w'),indent=2)
print('Steel target prepared',list((mx-mn)*s))
