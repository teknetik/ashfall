"""Live Blender source repair: remove generated glass, install a seated solid display."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/platform-terminals'
if Path(bpy.data.filepath)!=(O/'terminal-runtime-review.blend'):
 bpy.ops.wm.open_mainfile(filepath=str(O/'terminal-runtime-review.blend'),load_ui=False,use_scripts=False)
scene=bpy.data.scenes['Ward platform terminal source'];bpy.context.window.scene=scene
rows=[]
for level in range(3):
 ob=scene.objects['Terminal LOD'+str(level)];ob.hide_set(False);ob.hide_render=level!=0
 # Runtime derivatives were already normalized uniformly; edit only the generated flat glass surface.
 original_normals=[tuple(n.vector)for n in ob.data.corner_normals]
 bm=bmesh.new();bm.from_mesh(ob.data);remove=[];source_corner=bm.loops.layers.int.new('ward_source_corner')
 for f in bm.faces:
  start=ob.data.polygons[f.index].loop_start
  for j,loop in enumerate(f.loops):loop[source_corner]=start+j
 for f in bm.faces:
  p=f.calc_center_median();x,y,z=p.x,p.z,-p.y;plane=.36162-.205625*y
  if -.1515<x<.1515 and 1.138<y<1.428 and plane-.010<z<plane+.006:remove.append(f)
 before=len(bm.faces);bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(ob.data);bm.free();ob.data.update()
 indices=ob.data.attributes['ward_source_corner'];ob.data.normals_split_custom_set([original_normals[v.value]for v in indices.data]);ob.data.attributes.remove(indices);ob.data.calc_loop_triangles()
 rows.append({'lod':level,'removed_glass_faces':len(remove),'faces_before':before,'triangles_after':len(ob.data.loop_triangles),'note':'Original detailed Meshy source unchanged; edited only derived generated-glass region behind existing gasket.'})
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.gltf(filepath=str(O/('terminal-lod'+str(level)+'.glb')),export_format='GLB',use_selection=True,export_materials='NONE',export_texcoords=True,export_normals=True,export_tangents=False)
 ob.hide_set(level!=0)
old=scene.objects.get('Authored screen insert')
if old:bpy.data.objects.remove(old,do_unlink=True)
mat=bpy.data.materials.get('Terminal authored SAVE display');bs=mat.node_tree.nodes.get('Principled BSDF')
for n in mat.node_tree.nodes:
 if n.type=='TEX_IMAGE':n.image.reload()
def B(x,y,z):return (x,-z,y)
front=[B(x,y,.36162-.205625*y+.012)for x,y in [(-.156,1.128),(.156,1.128),(.156,1.438),(-.156,1.438)]]
back=[(p[0],p[1]+.004,p[2])for p in front];mesh=bpy.data.meshes.new('Solid seated display glass');mesh.from_pydata(front+back,[],[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]);mesh.materials.append(mat);uv=mesh.uv_layers.new(name='UV0')
for f in mesh.polygons:
 for li in f.loop_indices:
  vi=mesh.loops[li].vertex_index;uv.data[li].uv=[(0,0),(1,0),(1,1),(0,1)][vi]if f.index==0 else(0,0)
display=bpy.data.objects.new('Solid seated authored display',mesh);scene.collection.objects.link(display)
# A clean manufactured rubber gasket replaces the ragged generated inner lip.
def rect(hw,hh,r):
 points=[]
 for cx,cy,a in [(hw-r,hh-r,0),(-hw+r,hh-r,90),(-hw+r,-hh+r,180),(hw-r,-hh+r,270)]:
  for j in range(9):
   angle=math.radians(a+j*90/8);points.append((cx+r*math.cos(angle),1.283+cy+r*math.sin(angle)))
 return points
outer=rect(.164,.166,.011);inner=rect(.148,.143,.009);count=len(outer);vertices=[]
for loop,depth in [(outer,.023),(inner,.013),(inner,.006),(outer,.010)]:
 vertices.extend(B(x,y,.36162-.205625*y+depth)for x,y in loop)
faces=[]
for side in range(4):
 for i in range(count):faces.append((side*count+i,side*count+(i+1)%count,((side+1)%4)*count+(i+1)%count,((side+1)%4)*count+i))
gm=bpy.data.meshes.new('Authored rounded receiver gasket');gm.from_pydata(vertices,[],faces);gm.update();gmat=bpy.data.materials.new('Terminal receiver gasket rubber');gmat.use_nodes=True;gbs=gmat.node_tree.nodes.get('Principled BSDF');gbs.inputs['Base Color'].default_value=(.013,.018,.019,1);gbs.inputs['Roughness'].default_value=.78;gm.materials.append(gmat)
gasket=bpy.data.objects.new('Authored receiver gasket',gm);scene.collection.objects.link(gasket)
for f in gm.polygons:f.use_smooth=True
bpy.ops.object.select_all(action='DESELECT');gasket.select_set(True);bpy.context.view_layer.objects.active=gasket
bpy.ops.export_scene.gltf(filepath=str(O/'terminal-gasket.glb'),export_format='GLB',use_selection=True,export_materials='NONE',export_normals=True)
# The nameplate is authored exact text, mounted on the existing blank hardware plaque.
pm=bpy.data.materials.new('Terminal authored model plate');pm.use_nodes=True;pbs=pm.node_tree.nodes.get('Principled BSDF');tex=pm.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O/'displays/nameplate.png'),check_existing=True);pm.node_tree.links.new(tex.outputs['Color'],pbs.inputs['Base Color']);pm.node_tree.links.new(tex.outputs['Alpha'],pbs.inputs['Alpha']);pbs.inputs['Roughness'].default_value=.7
verts=[B(x,y,.33275-.1668*y+.0018)for x,y in [(-.133,1.479),(.133,1.479),(.133,1.545),(-.133,1.545)]];me=bpy.data.meshes.new('Authored model plate ink');me.from_pydata(verts,[],[(0,1,2,3)]);me.materials.append(pm);uv=me.uv_layers.new(name='UV0')
for li,p in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=p
plate=bpy.data.objects.new('WARD SR-08 model plate',me);scene.collection.objects.link(plate)
(O/'display-repair.json').write_text(json.dumps({'repair':'Generated glass faces removed from all 3 runtime derivatives with corner normals preserved. Solid 4 mm opaque glass sits behind a clean authored rounded receiver gasket. Inset exact-text interface and hardware nameplate are separately authored. Original 3,015,022 triangle source unchanged.','glass_front_bounds':{'xmin':-.156,'xmax':.156,'ymin':1.128,'ymax':1.438,'z_formula':'.36162-.205625*y+.012'},'gasket_triangles':len(faces)*2,'surface_normal_unity':[0,.2014,.9795],'lods':rows},indent=2))
cam=scene.camera;scene.render.resolution_x=1400;scene.render.resolution_y=1200
views=[('screen',(0,1.35,1.3),(0,1.285,.1)),('grazing-right',(.8,1.32,.75),(0,1.29,.1)),('grazing-left',(-.8,1.32,.75),(0,1.29,.1)),('grazing-top',(0,1.95,.8),(0,1.285,.1)),('grazing-bottom',(0,.8,1),(0,1.285,.1)),('back',(-1.7,1.3,-2.4),(0,.84,0)),('front',(1.9,1.3,2.7),(0,.84,0))]
bpy.data.libraries.write(str(O/'terminal-runtime-seated-v3.blend'),{scene},fake_user=True,compress=True)
for name,p,target in views:
 cam.data.lens=48 if name in ['front','back'] else 65
 cam.location=B(*p);cam.rotation_euler=(Vector(B(*target))-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/('seated-v3-'+name+'.png'));bpy.ops.render.render(write_still=True)
print(json.dumps(rows))
