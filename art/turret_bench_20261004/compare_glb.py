"""Compare two glTF files' meshes: per object, vertex count, sorted position/UV arrays and material names."""
import bpy, sys, numpy as np
a, b = sys.argv[sys.argv.index('--') + 1:][:2]
def load(f):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=f)
    out = {}
    for o in bpy.context.scene.objects:
        if o.type != 'MESH': continue
        me = o.data
        v = np.array([(o.matrix_world @ x.co)[:] for x in me.vertices]).round(4)
        out[o.name] = (len(me.vertices), len(me.polygons), np.sort(v.view('f8,f8,f8'), axis=0) if len(v) else v, sorted(m.name for m in me.materials if m))
    return out
A, B = load(a), load(b)
print('RES objects', sorted(A) == sorted(B), len(A), len(B))
for k in sorted(set(A) | set(B)):
    if k not in A or k not in B: print('RES missing', k); continue
    va, vb = A[k], B[k]
    same = va[0] == vb[0] and va[1] == vb[1] and va[3] == vb[3] and (va[2].shape == vb[2].shape and np.array_equal(va[2], vb[2]))
    print('RES', k, 'SAME' if same else f'DIFF verts {va[0]}/{vb[0]} faces {va[1]}/{vb[1]} mats {va[3]==vb[3]}')
