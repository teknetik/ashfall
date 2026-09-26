import bpy,bmesh,json
from pathlib import Path
R=Path('/home/teknetik/code/ao2');out=[]
S=bpy.data.scenes.new('Ground topology inspection');bpy.context.window.scene=S
for family in ['trash','scrap','crate']:
 before=set(S.objects);bpy.ops.import_scene.fbx(filepath=str(R/'meshy/ground-detail-20260910'/family/'model.fbx'))
 for ob in [o for o in S.objects if o not in before and o.type=='MESH']:
  bm=bmesh.new();bm.from_mesh(ob.data);seen=set();dups=0;deg=0
  for f in bm.faces:
   key=tuple(sorted(v.index for v in f.verts));dups+=key in seen;seen.add(key);deg+=f.calc_area()<1e-10
  out.append(dict(asset=family,vertices=len(bm.verts),polygons=len(bm.faces),edges=len(bm.edges),boundaryEdges=sum(e.is_boundary for e in bm.edges),nonManifoldEdges=sum(not e.is_manifold for e in bm.edges),overSharedEdges=sum(len(e.link_faces)>2 for e in bm.edges),duplicateFaces=dups,degenerateFaces=deg,smoothFaces=sum(f.smooth for f in bm.faces),uvLayers=len(ob.data.uv_layers)))
  bm.free()
  bpy.data.objects.remove(ob,do_unlink=True)
(R/'meshy/ground-detail-20260910/topology-audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
