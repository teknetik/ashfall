"""Read-only numerical source validation through live Blender MCP."""
import bpy, numpy as np, pathlib, json
out = pathlib.Path('/home/teknetik/code/ao2/art/quality_20260908/tree')
rows = []
for name in ['WardTree_LOD0_trunk','WardTree_LOD0_branches','WardTree_LOD0_leaves','WardTree_LOD1_trunk']:
    mesh = bpy.data.objects[name].data
    mesh.calc_loop_triangles()
    positions = np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',positions)
    positions = positions.reshape(-1,3)
    unique, inverse = np.unique(np.round(positions,6),axis=0,return_inverse=True)
    triangles = np.empty(len(mesh.loop_triangles)*3,dtype=np.int32)
    mesh.loop_triangles.foreach_get('vertices',triangles)
    canonical = np.sort(inverse[triangles.reshape(-1,3)],axis=1)
    _, counts = np.unique(canonical,axis=0,return_counts=True)
    rows.append({'mesh':name,'vertices':len(positions),'uniquePositions':len(unique),'triangles':len(canonical),'duplicateTrianglesIgnoringWinding':int(np.sum(counts-1)),'maximumOverlap':int(counts.max())})
(out/'overlap-check.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
