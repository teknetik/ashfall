"""Fix round: collar and cuffs close-ups of a colonist GLB (suit only, idle). Usage: hemview.py -- TAG colonist.glb"""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
a = sys.argv[sys.argv.index('--') + 1:]; out = f'{HERE}/renders/{a[0]}/'; os.makedirs(out, exist_ok=True)
reset(); arm, body, P = load((), colonist=a[1]); cam = setup(res=(800, 800), light='sun'); h = head_pos(arm)
render(out + 'collar.png', cam, h + Vector((0.15, 0.55, 0.05)), h + Vector((0, 0, -0.12)), 40)
render(out + 'cuff_R.png', cam, h + Vector((-0.55, 0.45, -0.35)), h + Vector((-0.22, 0, -0.5)), 40)
render(out + 'cuff_L.png', cam, h + Vector((0.55, 0.45, -0.35)), h + Vector((0.22, 0, -0.5)), 40)
