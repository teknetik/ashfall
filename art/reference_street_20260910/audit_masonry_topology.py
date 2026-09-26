import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
R=Path('/home/teknetik/code/ao2');O=R/'art/reference_street_20260910'
source={r['path']:r for r in json.loads((R/'art/building_weathering_20260909/unity-source.json').read_text())}
replacements=json.loads((O/'hero-masonry-v1-replacements.json').read_text());records=[]
def audit(row,tolerance):
 me=bpy.data.meshes.new('Temporary topology proof');P=row['positions'];I=row['indices']
 me.from_pydata([(p[0],-p[2],p[1]) for p in P],[],[I[k:k+3] for k in range(0,len(I),3)])
 bm=bmesh.new();bm.from_mesh(me);before=len(bm.verts)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=tolerance)
 # Match v1 authoring, reporting before and after orientation repair.
 def stats():return dict(vertices=len(bm.verts),faces=len(bm.faces),boundaryEdges=sum(e.is_boundary for e in bm.edges),nonManifoldEdges=sum(not e.is_manifold for e in bm.edges),nonContiguousEdges=sum(e.is_manifold and not e.is_contiguous for e in bm.edges),signedVolume=bm.calc_volume(signed=True),min=[min(v.co[i] for v in bm.verts) for i in range(3)],max=[max(v.co[i] for v in bm.verts) for i in range(3)])
 a=stats();bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));b=stats();bm.free();bpy.data.meshes.remove(me)
 return dict(weldTolerance=tolerance,originalVertices=before,beforeNormalRepair=a,afterNormalRepair=b)
for row in replacements:
 path=row['sourcePath'];records.append(dict(path=path,original=[audit(source[path],t) for t in [1e-7,1e-6,1e-5]],v1=[audit(row,t) for t in [1e-7,1e-5]]))
(O/'hero-masonry-v1-topology-diagnosis.json').write_text(json.dumps(records,indent=2));print(json.dumps(records))
