import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
out = HERE + '/renders/diag/'
for fr, act in ((0, 'none'), (12, 'idle')):
    reset()
    arm, body, P = load(('vest',), piece_paths={'vest': HERE + '/out/TS_FieldVest.glb'}, frame=fr, action=act)
    cam = setup(res=(900, 900), light='sun')
    h = head_pos(arm)
    render(out + f'flank_{act}.png', cam, h + Vector((-0.75, 0.55, -0.3)), h + Vector((-0.12, 0.0, -0.45)), 40)
    vm = P['vest'].data.materials[0]; vb = vm.node_tree.nodes['Principled BSDF']
    for inp in ('Base Color', 'Metallic', 'Roughness'):
        for l in list(vb.inputs[inp].links): vm.node_tree.links.remove(l)
    vb.inputs['Base Color'].default_value = (0.6, 0.55, 0.45, 1); vb.inputs['Metallic'].default_value = 0
    render(out + f'flank_{act}_flat.png', cam, h + Vector((-0.75, 0.55, -0.3)), h + Vector((-0.12, 0.0, -0.45)), 40)
