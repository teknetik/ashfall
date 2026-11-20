"""Raw Meshy sources (chest rig, helmet) rendered back and front, textured and flat, before any fitting/decimation."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
out = HERE + '/renders/diag/'; os.makedirs(out, exist_ok=True)
M = AO2 + '/meshy/tutorial-set-20261002/'
for name in ('chest', 'helmet'):
    reset()
    objs = import_glb(M + name + '/model.glb')
    ms = [o for o in objs if o.type == 'MESH']
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms)
    lo = Vector([min((o.matrix_world @ v.co)[i] for o in ms for v in o.data.vertices) for i in range(3)])
    hi = Vector([max((o.matrix_world @ v.co)[i] for o in ms for v in o.data.vertices) for i in range(3)])
    c = (lo + hi) / 2; s = (hi - lo).length
    print('SRC', name, 'tris', tris, 'size', hi - lo)
    cam = setup(res=(900, 900), light='backsun')
    g = bpy.data.objects['ground']; g.location.z = lo.z - 0.01
    for tag, d in (('back', Vector((0, 1, 0.15))), ('front', Vector((0, -1, 0.15)))):
        render(out + f'src_{name}_{tag}.png', cam, c + d.normalized() * s * 1.5, c, 40)
    for o in ms:
        for m in o.data.materials:
            b = m.node_tree.nodes['Principled BSDF']
            for inp in ('Base Color', 'Metallic', 'Roughness', 'Normal'):
                for l in list(b.inputs[inp].links): m.node_tree.links.remove(l)
            b.inputs['Base Color'].default_value = (0.6, 0.6, 0.6, 1); b.inputs['Metallic'].default_value = 0
    render(out + f'src_{name}_back_flat.png', cam, c + Vector((0, 1, 0.15)).normalized() * s * 1.5, c, 40)
