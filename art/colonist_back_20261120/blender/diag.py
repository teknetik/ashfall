"""Diagnosis renders of the shipped assets (no file is written outside renders/diag/)."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
out = HERE + '/renders/diag/'; os.makedirs(out, exist_ok=True)
reset()
arm, body, P = load(('vest', 'boots', 'helmet'))
cam = setup(light='sun')
V = views(arm)
render(out + 'conv_sun.png', cam, *V['conv'])
setup(light='backsun'); render(out + 'back15_backsun.png', cam, *V['back15'], res=(1280, 1280))
render(out + 'vest_backsun.png', cam, *V['vest'])
render(out + 'helmet_backsun.png', cam, *V['helmet'])
# suit poke-through: suit material magenta and flat
for i, m in enumerate(body.data.materials):
    print('MAT', i, m.name)
suit = next(m for m in body.data.materials if 'Jumpsuit' in m.name)
bsdf = suit.node_tree.nodes['Principled BSDF']
for l in list(bsdf.inputs['Base Color'].links): suit.node_tree.links.remove(l)
bsdf.inputs['Base Color'].default_value = (1, 0, 1, 1)
render(out + 'vest_pokethrough.png', cam, *V['vest'])
render(out + 'back15_pokethrough.png', cam, *V['back15'], res=(1280, 1280))
# vest flat grey: geometric raggedness vs texture
vm = P['vest'].data.materials[0]; vb = vm.node_tree.nodes['Principled BSDF']
for inp in ('Base Color', 'Metallic', 'Roughness', 'Normal'):
    for l in list(vb.inputs[inp].links): vm.node_tree.links.remove(l)
vb.inputs['Base Color'].default_value = (0.6, 0.55, 0.45, 1); vb.inputs['Metallic'].default_value = 0; vb.inputs['Roughness'].default_value = 0.8
render(out + 'vest_flat.png', cam, *V['vest'])
print('HEAD', head_pos(arm))
