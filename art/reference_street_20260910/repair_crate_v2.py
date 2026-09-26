"""Local repair of small unintended crate punctures, through live Blender.

Retains the generated FBX and every map. Only closed boundary loops below 12 cm
in normalized source units are filled. Large openings remain for visual review.
"""
import bpy,bmesh,json,shutil,math
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');SRC=R/'meshy/ground-detail-20260910/crate';OUT=R/'meshy/ground-detail-20260910/crate-v2'
assert not (OUT/'model.fbx').exists(),'Preserve prior repair'
OUT.mkdir(exist_ok=True)
S=bpy.data.scenes.new('Crate localized puncture repair v2');bpy.context.window.scene=S
before=set(S.objects);bpy.ops.import_scene.fbx(filepath=str(SRC/'model.fbx'))
obs=[o for o in S.objects if o not in before and o.type=='MESH'];report=[]
for ob in obs:
 bm=bmesh.new();bm.from_mesh(ob.data);uv=bm.loops.layers.uv.active
 olduv={v:next((l[uv].uv.copy() for f in v.link_faces for l in f.loops if l.vert==v),Vector((0,0))) for v in bm.verts}
 unseen={e for e in bm.edges if e.is_boundary};groups=[]
 while unseen:
  seed=unseen.pop();grp={seed};queue=[seed]
  while queue:
   e=queue.pop()
   for v in e.verts:
    for n in list(v.link_edges):
     if n in unseen:unseen.remove(n);grp.add(n);queue.append(n)
  groups.append(grp)
 for edges in groups:
  verts=set(v for e in edges for v in e.verts)
  closed=all(sum(e in edges for e in v.link_edges)==2 for v in verts)
  lo=Vector([min(v.co[k] for v in verts) for k in range(3)]);hi=Vector([max(v.co[k] for v in verts) for k in range(3)])
  span=max(hi-lo);fill=closed and span<.12
  count=0
  if fill:
   result=bmesh.ops.holes_fill(bm,edges=list(edges),sides=0);faces=result.get('faces',[]);count=len(faces)
   for f in faces:
    f.smooth=True
    for loop in f.loops:loop[uv].uv=olduv[loop.vert]
   bmesh.ops.triangulate(bm,faces=faces)
  report.append(dict(edges=len(edges),vertices=len(verts),closed=closed,span=float(span),center=list((lo+hi)/2),filled=fill,newPolygons=count))
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free();ob.data.update()
 ob.data.calc_loop_triangles()
for q in bpy.context.selected_objects:q.select_set(False)
for q in obs:q.select_set(True)
bpy.context.view_layer.objects.active=obs[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'model.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,bake_space_transform=False,add_leaf_bones=False,path_mode='AUTO')
shutil.copytree(SRC/'model_textures',OUT/'model_textures',dirs_exist_ok=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'repair-source.blend'))
(OUT/'repair-manifest.json').write_text(json.dumps(dict(source='meshy/ground-detail-20260910/crate/model.fbx',sourceRetained=True,operation='Fill only small closed unintended boundary loops; nearest boundary UV retained; no scale or remesh',triangles=sum(len(o.data.loop_triangles) for o in obs),boundaryGroups=report,filledGroups=sum(r['filled'] for r in report),nativeReviewRequired=True),indent=2))
print(json.dumps(dict(groups=len(report),filled=sum(r['filled'] for r in report),triangles=sum(len(o.data.loop_triangles) for o in obs))))
