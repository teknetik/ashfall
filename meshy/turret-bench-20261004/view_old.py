import bpy, math, mathutils
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='unity/AthenHill/Assets/AthenHill/Art/StreetDressing/Props/bench_painted/bench_painted_LOD0.glb')
sc=bpy.context.scene; sc.render.resolution_x=sc.render.resolution_y=500
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[1].default_value=1.5
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
# camera on Blender -Y (= Unity +Z front)
cam.location=(0.6,-2.2,1.2); cam.rotation_euler=(mathutils.Vector((0,0,0.4))-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath='/home/teknetik/code/ao2/meshy/turret-bench-20261004/review/old_bench_from_unity_plusZ.png'; bpy.ops.render.render(write_still=True)
