"""MikkTSpace tangents for a Meshy GLB (headless Blender). Usage: blender.sh tangents_blender.py -- in.glb out.npy
Meshy bakes its normal maps in MikkTSpace; glTFast computes Unity tangents when the file has none, which do not match
on Meshy's fragmented UV atlas and render as per-chart facets. This computes per-vertex MikkTSpace tangents on the
file's own normals and UVs and saves them in glTF vertex order and glTF axes (x, y, z, w) for add_tangents.py."""
import bpy, sys, numpy as np
args = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=args[0], merge_vertices=False)
mesh = max((o for o in bpy.context.scene.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
me = mesh.data
me.calc_tangents(uvmap=me.uv_layers[0].name)
n = len(me.loops)
vi = np.empty(n, np.int64); me.loops.foreach_get('vertex_index', vi)
t = np.empty(n * 3); me.loops.foreach_get('tangent', t); t = t.reshape(-1, 3)
s = np.empty(n); me.loops.foreach_get('bitangent_sign', s)
V = len(me.vertices)
tan = np.zeros((V, 3)); sgn = np.zeros(V); cnt = np.zeros(V)
np.add.at(tan, vi, t); np.add.at(sgn, vi, s); np.add.at(cnt, vi, 1)
tan /= np.linalg.norm(tan, axis=1, keepdims=True) + 1e-20
co = np.empty(V * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
# Blender (x, y, z) = glTF (x, -z, y)  =>  glTF = (x, z, -y); the importer flips V, which flips the bitangent
out = np.zeros((V, 4)); out[:, 0] = tan[:, 0]; out[:, 1] = tan[:, 2]; out[:, 2] = -tan[:, 1]
out[:, 3] = -np.where(sgn >= 0, 1.0, -1.0)
pos = np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1)
np.save(args[1], out.astype(np.float32)); np.save(args[1].replace('.npy', '_pos.npy'), pos.astype(np.float32))
mixed = int(((np.abs(sgn) < cnt - .5)).sum())
print('TANGENTS OK', V, 'vertices', n, 'loops', 'mixed-sign vertices', mixed)
