"""Preserve detailed Meshy source; normalize one runtime derivative to 1.5 m rotor span."""
import bpy,json
from mathutils import Vector,Matrix
from pathlib import Path
ROOT=Path('/home/teknetik/code/ao2');SRC=ROOT/'meshy/checkpoint-robots-20260926/scrap-drone/model.glb'
old=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(SRC));obs=[o for o in bpy.data.objects if o not in old];meshes=[o for o in obs if o.type=='MESH']
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
mn=Vector(tuple(min(p[i] for p in points) for i in range(3)));mx=Vector(tuple(max(p[i] for p in points) for i in range(3)))
s=1.5/max(mx.x-mn.x,mx.y-mn.y);centre=(mn+mx)/2
for o in meshes:
 mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw
 o.data.transform(Matrix.Scale(s,4)@Matrix.Translation(-centre)@o.matrix_world);o.matrix_world=Matrix.Identity(4)
 o.name='Inspection salvage drone'
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'unity/AthenHill/Assets/AthenHill/Art/Checkpoint/InspectionDrone.glb'),export_format='GLB',use_selection=True,export_yup=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/checkpoint_20260926/drone-review.blend'))
json.dump({'source':'Meshy source GLB retained unchanged','uniform_scale':s,'runtime_span_m':1.5,'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'qa':'Four rotors and broad rectangular chassis instead of spherical ceiling-fitting silhouette. Meshy produced exposed rotors rather than requested ducts; accepted mechanical form. No obvious floaters or holes in orbit review. Native shader and combat review required.'},open(ROOT/'art/checkpoint_20260926/drone-runtime.json','w'),indent=2)
print('Drone prepared')
