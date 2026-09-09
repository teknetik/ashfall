import bpy, math
from pathlib import Path
from mathutils import Vector

ROOT=Path('/home/teknetik/code/ao2')
OUT=ROOT/'art/phase1_20260908'
o=bpy.data.objects['Ward connected root flare']
m=bpy.data.materials.new('Root bark review');m.use_nodes=True
nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
for filename,socket in [('bark_willow_02_diff_4k.png','Base Color'),('bark_willow_02_rough_4k.png','Roughness')]:
    t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'refs/phase1_20260908/materials'/filename),check_existing=True)
    if socket=='Roughness':t.image.colorspace_settings.name='Non-Color'
    links.new(t.outputs['Color'],bs.inputs[socket])
t=nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(ROOT/'refs/phase1_20260908/materials/bark_willow_02_nor_gl_4k.png'),check_existing=True);t.image.colorspace_settings.name='Non-Color'
n=nodes.new('ShaderNodeNormalMap');links.new(t.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs['Normal'])
o.data.materials.clear();o.data.materials.append(m)
for obj in bpy.data.objects:
    if obj.type=='MESH' and obj!=o:obj.hide_render=True
def camera(name,pos,target,lens=31):
    c=bpy.data.objects.new(name,bpy.data.cameras.new(name));bpy.context.scene.collection.objects.link(c)
    c.location=Vector(pos);c.rotation_euler=(Vector(target)-c.location).to_track_quat('-Z','Y').to_euler();c.data.lens=lens;return c
sun=bpy.data.objects.new('Source review sunlight',bpy.data.lights.new('Source review sunlight','SUN'));bpy.context.scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(30),math.radians(-20),math.radians(-35));sun.data.energy=2.2
scene=bpy.context.scene;scene.world=bpy.data.worlds.new('Source review sky');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.22,.29,.38,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100
for name,pos,target in [('root-close',(4.8,-3,3.7),(0,0,2.2)),('root-whole',(9,-11,7),(0,0,4.8))]:
    scene.camera=camera(name,pos,target);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree-root-repaired.blend'))
print('Source root close-up and whole-shape renders saved. Final acceptance requires native Unity.')
