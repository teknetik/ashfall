import bpy,json
from pathlib import Path
O=Path('/home/teknetik/code/ao2/art/reference_street_20260910');out={}
for revision in ['hero-masonry-v2','hero-masonry-v3']:
 S=bpy.data.scenes[revision];records=[]
 for ob in S.objects:
  if ob.type!='MESH' or ob.name.startswith('ORIGINAL'):continue
  M=ob.data;M.calc_loop_triangles();uv=M.uv_layers.active.data;bad=0
  for t in M.loop_triangles:
   if t.area<1e-10:continue
   a,b,c=[uv[i].uv for i in t.loops];area2=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
   if area2/t.area<1e-4:bad+=1
  if bad:records.append(dict(part=ob.name,triangles=len(M.loop_triangles),degenerateUvTriangles=bad))
 out[revision]=dict(affectedParts=len(records),degenerateUvTriangles=sum(r['degenerateUvTriangles'] for r in records),details=records)
(O/'hero-masonry-v3-uv-diagnosis.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:{p:q for p,q in v.items() if p!='details'} for k,v in out.items()}))
