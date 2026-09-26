import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path('/home/teknetik/code/ao2');out=root/'art/reference_street_20260910/canopy-v3'
sc=bpy.data.scenes.get('Finery tensioned canopy 20260910 v3 source scene')
assert sc is not None
bpy.context.window.scene=sc
base=root/'unity/AthenHill/Assets/AthenHill/Art/Phase1/BasicGeneral/Revision03/Textures'
for mat in bpy.data.materials:
 if not mat.name.startswith('Finery v3 ') or mat.name.split()[-1] not in ['CanopyRed','CanopyRepair','CanopySeam']:continue
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF')
 uv=nodes.new('ShaderNodeTexCoord');scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=1/7;links.new(uv.outputs['UV'],scale.inputs[0])
 tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(base/'Canvas_BaseColor.png'),check_existing=True);links.new(scale.outputs[0],tex.inputs[0]);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 normal=nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(base/'fabric_pattern_07_nor_gl_4k.jpg'),check_existing=True);normal.image.colorspace_settings.name='Non-Color';links.new(uv.outputs['UV'],normal.inputs[0])
 n=nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.23;links.new(normal.outputs[0],n.inputs['Color']);links.new(n.outputs[0],bs.inputs['Normal'])
# Studio presentation only; saved city support geometry is installed separately.
world=bpy.data.worlds.new('Canopy inspection sky');sc.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.40,.52,.69,1);world.node_tree.nodes['Background'].inputs[1].default_value=.6
light=bpy.data.lights.new('Canopy inspection sunlight','SUN');light.energy=2.2;light.angle=.012
ob=bpy.data.objects.new('Canopy inspection sunlight',light);sc.collection.objects.link(ob);ob.rotation_euler=(.5,-.7,-.55)
camdata=bpy.data.cameras.new('Canopy inspection camera');cam=bpy.data.objects.new('Canopy inspection camera',camdata);sc.collection.objects.link(cam);sc.camera=cam
sc.render.engine='CYCLES';sc.cycles.samples=24;sc.cycles.use_denoising=True;sc.render.resolution_x=1200;sc.render.resolution_y=800;sc.render.resolution_percentage=100
sc.view_settings.view_transform='AgX'
def B(p):return Vector((p[0],-p[2],p[1]))
for name,pos,target,fov in [('top',(10.6,6.3,-12.7),(14.55,3.5,-18.4),58),('under',(11.1,2.2,-14.5),(14.1,3.55,-18.3),56),('hem',(10.9,3.5,-17.4),(12.2,3.35,-18.1),48)]:
 cam.location=B(pos);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();camdata.angle=math.radians(fov)
 sc.render.filepath=str(out/('source-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.data.libraries.write(str(out/'canopy-v3-source-review.blend'),{sc},fake_user=True)
print('Saved three source inspection views; isolated shape review is not native acceptance.')
