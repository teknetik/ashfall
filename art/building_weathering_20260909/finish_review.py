import bpy,math
from mathutils import Vector
from pathlib import Path
O=Path('/home/teknetik/code/ao2/art/building_weathering_20260909')
scene=bpy.data.scenes['Ward Field Supply and Finery weathering v1'];bpy.context.window.scene=scene
def B(v):return Vector((v[0],-v[2],v[1]))
scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('Ward review sky');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.32,.40,.5,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
ld=bpy.data.lights.new('Review sunlight','SUN');ld.energy=2.5;ld.angle=.04;light=bpy.data.objects.new('Review sunlight',ld);scene.collection.objects.link(light);light.rotation_euler=(.5,-.6,-.7)
cd=bpy.data.cameras.new('Weathering source review');cam=bpy.data.objects.new('Weathering source review',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.lens=46
cam.location=B((4.0,7.0,-4.0));cam.rotation_euler=(B((18.5,3.6,-13.0))-cam.location).to_track_quat('-Z','Y').to_euler()
for name in ['Wear Graffiti']:
 m=bpy.data.materials[name];bs=m.node_tree.nodes.get('Principled BSDF');tex=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE');m.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha'])
bpy.ops.wm.save_as_mainfile(filepath=str(O/'weathering-v1.blend'))
scene.render.filepath=str(O/'source-review-v1.png');bpy.ops.render.render(write_still=True)
cam.location=B((14,2.5,-7));cam.rotation_euler=(B((17.9,2.0,-10.2))-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=28
scene.render.filepath=str(O/'source-field-close-v1.png');bpy.ops.render.render(write_still=True)
print('Saved editable source and two Blender review images')
