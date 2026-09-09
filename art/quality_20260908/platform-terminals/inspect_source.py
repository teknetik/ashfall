"""Run through the live Blender MCP after ownership is released; no Unity writes."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2'); O=R/'art/quality_20260908/platform-terminals'
source=R/'meshy/platform-terminals-20260908/source/terminal.glb'
assert source.is_file(), 'Download and preserve the Meshy source first.'
assert bpy.context.window, 'Use the live Blender session.'
scene=bpy.data.scenes.get('Ward platform terminal source') or bpy.data.scenes.new('Ward platform terminal source')
bpy.context.window.scene=scene
for ob in list(scene.objects): bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(source),merge_vertices=False)
objects=[ob for ob in scene.objects if ob.type=='MESH']
assert objects
points=[ob.matrix_world@Vector(c) for ob in objects for c in ob.bound_box]
lo=Vector(tuple(min(p[a] for p in points) for a in range(3))); hi=Vector(tuple(max(p[a] for p in points) for a in range(3)))
height=hi.z-lo.z; factor=1.65/height
# Apply one shared uniform transform to the authored source, preserving relative proportions.
anchor=bpy.data.objects.new('Terminal normalized source',None);scene.collection.objects.link(anchor)
for ob in [ob for ob in scene.objects if ob.parent is None and ob!=anchor]: ob.parent=anchor
anchor.scale=(factor,)*3;anchor.location=(-(lo.x+hi.x)*.5*factor,-(lo.y+hi.y)*.5*factor,-lo.z*factor)
bpy.context.view_layer.update()
report={'source':str(source.relative_to(R)), 'source_bounds_blender':{'min':list(lo),'max':list(hi)},'uniform_scale':factor,'target_height_m':1.65,'normalized_size_unity':[(hi.x-lo.x)*factor,1.65,(hi.y-lo.y)*factor],'meshes':[],'materials':[]}
for ob in objects:
 me=ob.data;me.calc_loop_triangles()
 report['meshes'].append({'name':ob.name,'vertices':len(me.vertices),'triangles':len(me.loop_triangles),'uv_layers':[u.name for u in me.uv_layers],'materials':[m.name if m else None for m in me.materials]})
for mat in set(m for ob in objects for m in ob.data.materials if m):
 report['materials'].append({'name':mat.name,'images':[{'node':n.name,'path':n.image.filepath,'size':list(n.image.size),'colorspace':n.image.colorspace_settings.name} for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
(O/'source-inspection.json').write_text(json.dumps(report,indent=2))
world=bpy.data.worlds.get('Terminal neutral studio') or bpy.data.worlds.new('Terminal neutral studio');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.25,1);world.node_tree.nodes['Background'].inputs[1].default_value=.4
floor_mat=bpy.data.materials.new('Terminal studio floor');floor_mat.diffuse_color=(.25,.27,.30,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006));floor=bpy.context.object;floor.name='Terminal source studio floor';floor.data.materials.append(floor_mat)
def B(p):return Vector((p[0],-p[2],p[1]))
for name,p,power,size in [('Terminal key',(2,3,3),650,3),('Terminal fill',(-3,2,-1),420,3),('Terminal rim',(1,3,-3),350,2)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.shape='DISK';ld.size=size;ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=B(p);ob.rotation_euler=(B((0,.8,0))-ob.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Terminal source camera');cam=bpy.data.objects.new('Terminal source camera',camd);scene.collection.objects.link(cam);scene.camera=cam;camd.lens=65
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
for name,p,target in [('front',(0,1.1,3.4),(0,.84,0)),('right',(2.5,1.1,2.5),(0,.84,0)),('back',(0,1.1,-3.4),(0,.84,0)),('screen',(0,1.3,1.6),(0,1.24,.2))]:
 cam.location=B(p);cam.rotation_euler=(B(target)-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/('source-'+name+'.png'))
 if name=='front': bpy.data.libraries.write(str(O/'terminal-source-inspection.blend'),{scene},fake_user=True,compress=True)
 bpy.ops.render.render(write_still=True)
print(json.dumps(report))
