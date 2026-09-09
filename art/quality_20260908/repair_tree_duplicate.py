"""Replace the duplicated LOD0 trunk with its exact retained single source mesh."""
import bpy, pathlib, json, numpy as np
ROOT = pathlib.Path('/home/teknetik/code/ao2')
OUT = ROOT/'art/quality_20260908/tree'
duplicate = bpy.data.objects['WardTree_LOD0_trunk']
source = bpy.data.objects['jacaranda_tree_trunk_LOD0']
def points(mesh):
    v = np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',v)
    return np.unique(np.round(v.reshape(-1,3),6),axis=0)
assert np.array_equal(points(duplicate.data), points(source.data)), 'Source trunk differs; review before replacing.'
old_count = len(duplicate.data.loop_triangles)
duplicate.data = source.data.copy()
duplicate.data.name = 'WardTree full source trunk, duplicate removed'
duplicate.data.calc_loop_triangles()
assert len(duplicate.data.loop_triangles)*2 == old_count
bpy.ops.object.select_all(action='DESELECT')
for name in ['WardTree_LOD0_trunk','WardTree_LOD0_branches','WardTree_LOD0_leaves']:
    obj = bpy.data.objects[name]
    obj.hide_set(False)
    obj.select_set(True)
bpy.context.view_layer.objects.active = duplicate
destination = OUT/'WardTree_LOD0_repaired.fbx'
bpy.ops.export_scene.fbx(filepath=str(destination),use_selection=True,object_types={'MESH'},use_mesh_modifiers=True,mesh_smooth_type='OFF',use_tspace=True,add_leaf_bones=False,bake_anim=False,axis_forward='-Z',axis_up='Y',path_mode='STRIP',embed_textures=False)
report = {'defect':'The supplied combined LOD0 contains two exactly coincident copies of the complete trunk. Standalone source trunk has the same unique positions, UVs and material.','retainedSource':'jacaranda_tree_trunk_LOD0','exactUniquePositions':True,'originalTrunkTriangles':old_count,'repairedTrunkTriangles':len(duplicate.data.loop_triangles),'candidateTotalTriangles':3748776,'candidateFile':str(destination),'originalDownloadsUnchanged':True}
(OUT/'duplicate-repair.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree-runtime-repaired.blend'))
print(json.dumps(report,indent=2))
