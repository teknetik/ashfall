import bpy, math, mathutils, sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]; A=R/'unity/AthenHill/Assets/AthenHill/Art/TurretBench'; S=R/'meshy/turret-bench-20261004/source'
out=Path(__file__).resolve().parent/'review'; out.mkdir(exist_ok=True)
jobs=[('sentinel_turret',S/'Meshy_AI_Sentinel_Turret_1004174027_texture.glb'),('cyber_bench',S/'Meshy_AI_Cybernetic_Bench_1004174020_texture.glb')]
for pid,src in jobs:
    for tag,f in [('source',src),('LOD0',A/pid/f'{pid}_LOD0.glb'),('LOD1',A/pid/f'{pid}_LOD1.glb')]:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(f))
        obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
        if tag!='source':   # untextured exports: borrow the source material
            bpy.ops.import_scene.gltf(filepath=str(src)); s=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in obs][0]
            for o in obs: o.data.materials.clear(); o.data.materials.append(s.data.materials[0])
            s.hide_render=True
            ob=obs[0]
        else:
            ob=obs[0]
        mn=mathutils.Vector([min((ob.matrix_world@mathutils.Vector(c))[i] for c in ob.bound_box) for i in range(3)]); mx=mathutils.Vector([max((ob.matrix_world@mathutils.Vector(c))[i] for c in ob.bound_box) for i in range(3)])
        ctr=(mn+mx)/2; r=(mx-mn).length
        sc=bpy.context.scene; sc.render.resolution_x=sc.render.resolution_y=700
        w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.55,0.6,0.7,1)
        sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sun.data.energy=4; sun.rotation_euler=(math.radians(45),0,math.radians(-40)); sc.collection.objects.link(sun)
        cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
        d=r*1.25; t=math.radians(-60)
        cam.location=ctr+mathutils.Vector((math.cos(t)*d,math.sin(t)*d,d*0.35)); cam.rotation_euler=(ctr-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath=str(out/f'{pid}_{tag}.png'); bpy.ops.render.render(write_still=True)
