import bpy,math,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/phase1_20260908';T=R/'unity/AthenHill/Assets/AthenHill/Art/Courtyard/Textures'
s=bpy.context.scene;assert s.name=='Finery frontage'
for name in ['Stone0','Stone1','Stone2','Stone3','Drum']:
 m=bpy.data.materials[name];m.use_nodes=True;n=m.node_tree.nodes;bs=n.get('Principled BSDF');a='sandstone_cracks' if name.startswith('Stone') else 'rusty_painted_metal'
 for suffix,socket in [('diff','Base Color'),('rough','Roughness')]:
  im=bpy.data.images.load(str(T/(a+'_'+suffix+'_2k.jpg')),check_existing=True);node=n.new('ShaderNodeTexImage');node.image=im
  if suffix=='rough':im.colorspace_settings.name='Non-Color'
  m.node_tree.links.new(node.outputs['Color'],bs.inputs[socket])
 im=bpy.data.images.load(str(T/(a+'_nor_gl_2k.jpg')),check_existing=True);im.colorspace_settings.name='Non-Color';tex=n.new('ShaderNodeTexImage');tex.image=im;normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.5;m.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
def B(p):return Vector((p[0],-p[2],p[1]))
bpy.ops.object.light_add(type='SUN');sun=bpy.context.view_layer.objects.active;sun.rotation_euler=(math.radians(28),math.radians(-22),math.radians(-48));sun.data.energy=3;sun.data.angle=.06
s.world=bpy.data.worlds.new('Review daylight');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.35,.43,.55,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.45
s.render.engine='CYCLES';s.cycles.samples=16;s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
s.view_settings.view_transform='AgX'
for name,p,target in [('finery-source-whole',(7.5,4.4,-29.5),(20,3.7,-18)),('finery-source-door',(12.5,1.8,-18),(17,1.8,-18)),('finery-source-back',(31,4,-9),(23,3.8,-18))]:
 bpy.ops.object.camera_add(location=B(p));c=bpy.context.view_layer.objects.active;c.name=name;c.rotation_euler=(B(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=34;s.camera=c;s.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'finery-frontage.blend'))
print('Three source views saved')
