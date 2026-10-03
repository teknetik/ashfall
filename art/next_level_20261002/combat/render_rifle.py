# Blender: orthographic side/top/front renders of the Meshy field rifle glb, with axis labels, to decide the muzzle end.
import bpy,math,os,sys
out=os.environ.get('RIFLE_OUT','/home/teknetik/code/ao2/unity/evidence/next-level/20261002/combat/rifle-mesh')
glb='/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/Weapons/FieldRifle/FieldRifle.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs=[o for o in bpy.data.objects if o.type=='MESH']
import mathutils
mn=mathutils.Vector((1e9,)*3);mx=mathutils.Vector((-1e9,)*3)
for o in objs:
    for v in o.bound_box:
        w=o.matrix_world@mathutils.Vector(v)
        mn=mathutils.Vector(map(min,mn,w));mx=mathutils.Vector(map(max,mx,w))
c=(mn+mx)/2;size=mx-mn
print('BLENDER bbox min',tuple(round(x,3) for x in mn),'max',tuple(round(x,3) for x in mx))
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=1600;scene.render.resolution_y=600;scene.render.film_transparent=False
world=bpy.data.worlds.new('w');scene.world=world;world.color=(0.6,0.6,0.6)
cam_data=bpy.data.cameras.new('cam');cam_data.type='ORTHO';cam=bpy.data.objects.new('cam',cam_data);scene.collection.objects.link(cam);scene.camera=cam
# Blender imports glTF with Y-up -> Z-up: glTF X stays X, glTF Y -> Blender Z, glTF Z -> Blender -Y
def shot(name,loc,rot,ortho,resx,resy):
    cam.location=loc;cam.rotation_euler=rot;cam_data.ortho_scale=ortho
    scene.render.resolution_x=resx;scene.render.resolution_y=resy
    scene.render.filepath=os.path.join(out,name+'.png');bpy.ops.render.render(write_still=True);print('BLENDER wrote',scene.render.filepath)
L=max(size)*1.15
# side view: camera on -Y looking +Y (sees Blender X right, Z up) => glTF X right, glTF Y up
shot('side_from_-Y',(c.x,c.y-5,c.z),(math.radians(90),0,0),L,1600,600)
# top view: camera above looking down, Blender X right, Blender -Y up on image => glTF X right, glTF Z up
shot('top',(c.x,c.y,c.z+5),(0,0,0),L,1600,400)
# end views along X: from +X and from -X
shot('end_from_+X',(c.x+5,c.y,c.z),(math.radians(90),0,math.radians(90)),max(size.y,size.z)*1.3,600,600)
shot('end_from_-X',(c.x-5,c.y,c.z),(math.radians(90),0,math.radians(-90)),max(size.y,size.z)*1.3,600,600)
