"""Render every Meshy source piece in its raw import frame (front = looking along +Y, i.e. camera at -Y), to read its
orientation and construction before fitting. Writes renders/src_<piece>.jpg (front, back, left(+X side), right, top, under)."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy
from mathutils import Vector
import hlib as H
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SRC = {'helmet': H.MESHY / 'helmet/model.glb', 'vest': H.MESHY / 'chest/model.glb', 'carrier': H.CARRIER_SRC,
       'bracer': H.MESHY / 'bracer/model.glb', 'kneeshin': H.MESHY / 'kneeshin/model.glb',
       'bootplates': H.MESHY / 'bootplates/model.glb', 'glove_retex': H.MESHY / 'glove_retex/model.glb'}
for key in (args or SRC):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p = H.import_piece(SRC[key], key)
    lo, hi = H.bounds(p); size = max(hi - lo)
    cam = H.setup_render((480, 480))
    paths = [H.shot(cam, H.REND / f'src_{key}_{v}.png', (0, 0, 0), size * 1.1, v) for v in ('front', 'back', 'left', 'right', 'top', 'under')]
    H.sheet(paths, H.REND / f'src_{key}.jpg', cols=6)
    import os
    for q in paths: os.remove(q)
    print('SRC', key, 'size', [round(x, 3) for x in hi - lo])
