import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path('/home/teknetik/code/ao2/art/quality_20260909/basic-general')
scene=bpy.data.scenes['Basic General architectural repair'];bpy.context.window.scene=scene
B=lambda p:Vector((p[0],-p[2],p[1]))
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
world=bpy.data.worlds.new('General neutral source world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.30,.36,.43,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.42;scene.world=world
for name,position,energy,size,color in [('Warm source key',(-3,7,5),1850,5,(1,.88,.74)),('Cool source fill',(5,5,1),1300,5,(.73,.84,1)),('Rear source rim',(-2,5,-6),1700,4,(1,.9,.79))]:
 data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=B(position);o.rotation_euler=(B((0,1.2,0))-o.location).to_track_quat('-Z','Y').to_euler()
mat=bpy.data.materials.new('General source backdrop');mat.diffuse_color=(.13,.145,.16,1);mat.use_nodes=True;mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.13,.145,.16,1);mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.9
bpy.ops.mesh.primitive_plane_add(size=200,location=B((0,-.585,0)));bpy.context.object.name='General source backdrop';bpy.context.object.data.materials.append(mat)
cd=bpy.data.cameras.new('General source camera');camera=bpy.data.objects.new('General source camera',cd);scene.collection.objects.link(camera);scene.camera=camera
views=[('front',(5.8,3,7.4),(0,1.35,0),48),('back',(-5,2.8,-7),(0,1.4,-.6),48),('left',(-7.6,2.0,-.1),(0,1.4,-.1),46),('right',(7.6,2.0,-.1),(0,1.4,-.1),46),('roof',(-5,7.5,6),(0,1.6,0),46),('door',(0,1.65,4.6),(0,1.45,-.2),35),('sign-close',(-1.1,2.45,3.18),(-1.1,2.32,1.74),48),('rear-close',(-1.1,1.4,-3.1),(-1.1,1.3,-1.63),42)]
(O/'source-view-plan-v1.json').write_text(json.dumps(views,indent=2))
bpy.data.libraries.write(str(O/'basic-general-source-v1.blend'),{scene},fake_user=True,compress=True)
for name,pos,target,lens in views:
 camera.location=B(pos);camera.rotation_euler=(B(target)-camera.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;scene.render.filepath=str(O/('source-v1-'+name+'.png'));bpy.ops.render.render(write_still=True)
print('BASIC_GENERAL_SOURCE_VIEWS_COMPLETE')
