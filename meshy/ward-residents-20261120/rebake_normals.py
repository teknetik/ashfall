"""Re-bake a Meshy character's normal map against smooth vertex normals (headless Blender, Cycles CPU).
Usage: blender.sh rebake_normals.py -- <npc folder> [size=2048] [source glb name, default rigged.glb]
Meshy ships near-flat vertex normals and a normal map that compensates them per triangle. In Unity that compensation
did not reproduce (the faces rendered faceted with every tangent sign/green-channel combination tried), while Blender
renders it correctly. So: A = rigged.glb (flat normals + Meshy normal map, rendered correctly by Blender),
B = rigged_smooth.glb (smooth_normals.py, same vertices/UVs). Bake A's shading normal onto B in B's tangent space
(selected-to-active, tiny cage). The result only carries surface detail relative to smooth normals, so small tangent
convention differences no longer show as facets. Writes normal_smooth.png and B's MikkTSpace tangents (glTF order).
"""
import bpy, sys, numpy as np
from pathlib import Path
args = sys.argv[sys.argv.index('--') + 1:]
D = Path(args[0]); SIZE = int(args[1]) if len(args) > 1 else 2048
SRC = args[2] if len(args) > 2 else 'rigged.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
s = bpy.context.scene; s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 1


def load(p):
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=str(p), merge_vertices=False)
    new = [o for o in bpy.data.objects if o not in before]
    m = max((o for o in new if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
    for o in new:   # drop the armature: bake the rest pose geometry
        if o.type == 'ARMATURE':
            for c in new:
                if c.type == 'MESH':
                    for md in list(c.modifiers):
                        if md.type == 'ARMATURE': c.modifiers.remove(md)
    return m, new

A, na = load(D / SRC)
B, nb = load(D / 'rigged_smooth.glb')
assert len(A.data.vertices) == len(B.data.vertices)
# B gets its own material with a target image node; A keeps Meshy's material (normal map wired)
img = bpy.data.images.new('normal_smooth', SIZE, SIZE, alpha=False, float_buffer=False)
img.colorspace_settings.name = 'Non-Color'
mat = bpy.data.materials.new('bake_target'); mat.use_nodes = True
node = mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image = img; mat.node_tree.nodes.active = node
B.data.materials.clear(); B.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT'); A.select_set(True); B.select_set(True); bpy.context.view_layer.objects.active = B
s.render.bake.use_selected_to_active = True; s.render.bake.cage_extrusion = 0.004; s.render.bake.max_ray_distance = 0.02
s.render.bake.normal_space = 'TANGENT'; s.render.bake.margin = 8; s.render.bake.margin_type = 'EXTEND'
s.render.bake.target = 'IMAGE_TEXTURES'
bpy.ops.object.bake(type='NORMAL')
img.filepath_raw = str(D / 'normal_smooth.png'); img.file_format = 'PNG'; img.save()
# MikkTSpace tangents of B (glTF axes and order; glTF w = -Blender sign because the importer flips V)
me = B.data; me.calc_tangents(uvmap=me.uv_layers[0].name)
n = len(me.loops); vi = np.empty(n, np.int64); me.loops.foreach_get('vertex_index', vi)
t = np.empty(n * 3); me.loops.foreach_get('tangent', t); t = t.reshape(-1, 3)
sg = np.empty(n); me.loops.foreach_get('bitangent_sign', sg)
V = len(me.vertices); tan = np.zeros((V, 3)); sgn = np.zeros(V)
np.add.at(tan, vi, t); np.add.at(sgn, vi, sg); tan /= np.linalg.norm(tan, axis=1, keepdims=True) + 1e-20
out = np.zeros((V, 4), np.float32); out[:, 0] = tan[:, 0]; out[:, 1] = tan[:, 2]; out[:, 2] = -tan[:, 1]; out[:, 3] = -np.where(sgn >= 0, 1, -1)
co = np.empty(V * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
np.save(D / 'tangents_smooth.npy', out); np.save(D / 'tangents_smooth_pos.npy', np.stack([co[:, 0], co[:, 2], -co[:, 1]], 1).astype(np.float32))
print('REBAKE OK', D.name, SIZE)
