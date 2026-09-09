import bpy,json
from mathutils import Vector
from pathlib import Path
scene=bpy.data.scenes['Ward platform terminal source'];bpy.context.window.scene=scene;deps=bpy.context.evaluated_depsgraph_get();rows=[]
for y in [1.08,1.12,1.16,1.20,1.24,1.28,1.32,1.36,1.40,1.44,1.48,1.52]:
 for x in [-.20,-.16,-.12,0,.12,.16,.20]:
  hit,p,n,i,o,m=scene.ray_cast(deps,Vector((x,-3,y)),Vector((0,1,0)))
  rows.append({'x':x,'y':y,'hit':hit,'point':[p.x,p.z,-p.y]if hit else None,'normal':[n.x,n.z,-n.y]if hit else None,'object':o.name if o else None})
Path('/home/teknetik/code/ao2/art/quality_20260908/platform-terminals/screen-rays.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
