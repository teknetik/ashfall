"""Live Blender derivative: preserve detailed original, measure collapse LOD errors."""
import bpy,json,random,math
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from pathlib import Path
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/platform-terminals';scene=bpy.data.scenes['Ward platform terminal source'];bpy.context.window.scene=scene
source=scene.objects['Mesh_0'];assert len(source.data.polygons)>1000000
deps=bpy.context.evaluated_depsgraph_get();tree=BVHTree.FromObject(source,deps)
runtime=[];report=[]
for name,target in [('LOD0',300000),('LOD1',75000),('LOD2',20000)]:
 (O/'runtime-progress.json').write_text(json.dumps({'stage':'derive','lod':name,'target':target}))
 basis=source if not runtime else runtime[-1];basis.data.calc_loop_triangles()
 ob=bpy.data.objects.new('Terminal '+name,basis.data.copy());scene.collection.objects.link(ob);ob.matrix_world=basis.matrix_world.copy()
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Measured runtime collapse','DECIMATE');mod.decimate_type='COLLAPSE';mod.ratio=target/len(basis.data.loop_triangles);mod.use_collapse_triangulate=True
 bpy.ops.object.modifier_apply(modifier=mod.name);ob.data.calc_loop_triangles()
 # Surface distance sampled in both directions: vertices and barycentric face centres.
 # Distances transformed to normalized metres (source transform is uniform).
 rng=random.Random(90826);distance=[];inv=source.matrix_world.inverted();scale=source.matrix_world.to_scale().x
 for tri in rng.sample(list(ob.data.loop_triangles),min(16000,len(ob.data.loop_triangles))):
  p=sum((ob.data.vertices[i].co for i in tri.vertices),Vector())/3
  q=inv@(ob.matrix_world@p);near=tree.find_nearest(q)
  if near[0] is not None:distance.append(near[3]*scale)
 reverse=BVHTree.FromObject(ob,deps);rev_inv=ob.matrix_world.inverted()
 for v in rng.sample(list(source.data.vertices),16000):
  p=rev_inv@(source.matrix_world@v.co);near=reverse.find_nearest(p)
  if near[0]is not None:distance.append(near[3]*scale)
 distance.sort();row={'name':name,'triangles':len(ob.data.loop_triangles),'vertices':len(ob.data.vertices),'samples':len(distance),'distance_p50_m':distance[len(distance)//2],'distance_p95_m':distance[int(len(distance)*.95)],'distance_p99_m':distance[int(len(distance)*.99)],'distance_max_m':max(distance)}
 report.append(row);print(json.dumps(row),flush=True)
 (O/'runtime-lod-partial.json').write_text(json.dumps(report,indent=2))
 # Apply the shared uniform normalization to the exported derivative only.
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bpy.ops.export_scene.gltf(filepath=str(O/('terminal-'+name.lower()+'.glb')),export_format='GLB',use_selection=True,export_materials='NONE',export_texcoords=True,export_normals=True,export_tangents=False)
 ob.hide_render=True;ob.hide_set(True);runtime.append(ob)
(O/'runtime-lod-measurements.json').write_text(json.dumps({'source_triangles':3015022,'normalization':'Uniform, 1.65m height, .74668m width, .72002m depth','method':'Bidirectional sampled nearest surface distance at deterministic vertices/triangle centres; not a proof of all-point Hausdorff distance. Native silhouette/shading review remains required.','lods':report},indent=2))
# The screen opening is a measured plane. Source defects are covered by an authored opaque glass insert.
source.hide_render=True;runtime[0].hide_render=False;runtime[0].hide_set(False)
mat=bpy.data.materials.new('Terminal authored SAVE display');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'displays/save.png'));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=.3;bs.inputs['Roughness'].default_value=.38
def B(x,y,z):return (x,-z,y)
verts=[B(x,y,.36162-.205625*y+.0035)for x,y in [(-.151,1.141),(.151,1.141),(.151,1.423),(-.151,1.423)]]
mesh=bpy.data.meshes.new('Measured opaque display insert');mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.materials.append(mat);uv=mesh.uv_layers.new(name='UV0')
for li,p in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=p
display=bpy.data.objects.new('Authored screen insert',mesh);scene.collection.objects.link(display)
cam=scene.camera
for name,p,target in [('runtime-front',(0,1.1,3.4),(0,.84,0)),('runtime-right',(2.5,1.1,2.5),(0,.84,0)),('runtime-screen',(0,1.3,1.6),(0,1.24,.2))]:
 cam.location=B(*p);cam.rotation_euler=(Vector(B(*target))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.data.libraries.write(str(O/'terminal-runtime-review.blend'),{scene},fake_user=True,compress=True)
print('Runtime derivatives and measured display insert saved.')
