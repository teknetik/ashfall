import bpy,math,pathlib
from mathutils import Vector
R=pathlib.Path('/home/teknetik/code/ao2');T=R/'unity/AthenHill/Assets/AthenHill/Art/Courtyard/Textures'
def B(p):return Vector((p[0],-p[2],p[1]))
for o in list(bpy.data.objects):
    if o.name.startswith('CWReview'):bpy.data.objects.remove(o,do_unlink=True)
for m in bpy.data.materials:
    if not m.name.startswith('CW '):continue
    k=m.name[3:];nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
    asset='sandstone_cracks' if k.startswith('Stone') else 'sand_03' if k=='Sand' else None
    if not asset:continue
    col=nodes.new('ShaderNodeTexImage');col.image=bpy.data.images.load(str(T/(asset+'_diff_2k.jpg')),check_existing=True);links.new(col.outputs['Color'],bs.inputs['Base Color'])
    nor=nodes.new('ShaderNodeTexImage');nor.image=bpy.data.images.load(str(T/(asset+'_nor_gl_2k.jpg')),check_existing=True);nor.image.colorspace_settings.name='Non-Color'
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45;links.new(nor.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
poster=bpy.data.materials['CW Karaveen'];n=poster.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(T/'KaraveenPoster.png'),check_existing=True);poster.node_tree.links.new(n.outputs['Color'],poster.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
for o in bpy.context.scene.objects:
    if not o.name.startswith('CWReview') and o not in bpy.data.collections['Ward courtyard authored'].objects[:]:o.hide_render=True
light=bpy.data.lights.new('CWReview sun','SUN');light.energy=3;light.angle=.055
sun=bpy.data.objects.new('CWReview sun',light);bpy.context.scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(38),math.radians(-25),math.radians(-50))
bpy.context.scene.world.color=(.18,.20,.25)
camera=bpy.data.cameras.new('CWReview camera');cam=bpy.data.objects.new('CWReview camera',camera);bpy.context.scene.collection.objects.link(cam)
cam.location=B((1,5,-5));cam.rotation_euler=(B((9,.3,-14))-cam.location).to_track_quat('-Z','Y').to_euler();camera.lens=35
s=bpy.context.scene;s.camera=cam;s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.filepath=str(R/'unity/evidence/courtyard/20260908/blender-geometry-review-v2.png');bpy.ops.render.render(write_still=True)
print('Authored geometry preview rendered. Unity remains final shading and gameplay authority.')
