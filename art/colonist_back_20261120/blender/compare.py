"""Before/after review renders. Usage: blender.sh compare.py -- TAG <before|after> [light ...]
'before' = the shipped Unity assets; 'after' = out/ pieces + out/colonist.glb when present.
Writes renders/TAG/<state>_<view>_<light>.png for the views conv, follow, back15, quarter, helmet, vest.
Kit: suit + vest + boots + helmet (+ carrier for the 'carrier' views, + arm guards and gloves for 'full')."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/colonist_back_20261120/blender')
from cblib import *
a = sys.argv[sys.argv.index('--') + 1:]
TAG, STATE = a[0], a[1]; GLB = [x for x in a[2:] if x.endswith('.glb')]; LIGHTS = [x for x in a[2:] if not x.endswith('.glb')] or ['sun']
out = f'{HERE}/renders/{TAG}/'; os.makedirs(out, exist_ok=True)
OUTD = HERE + '/out/'
pp = {}; col = COLONIST
if STATE == 'after':
    for k, f in (('vest', 'TS_FieldVest.glb'), ('helmet', 'TS_Helmet.glb'), ('carrier', 'TS_WardenCarrier.glb'),
                 ('arms', 'TS_ArmGuards.glb'), ('gloves', 'TS_Gloves.glb'), ('boots', 'TS_Boots.glb')):
        if os.path.exists(OUTD + f): pp[k] = OUTD + f
    if os.path.exists(OUTD + 'colonist.glb'): col = OUTD + 'colonist.glb'
    if GLB: col = GLB[0]
ONLY = os.environ.get('CB_KITS')
KITS = {'kit': ('vest', 'boots', 'helmet'), 'carrier': ('carrier', 'boots', 'helmet', 'arms', 'gloves'), 'suit': ()}
SHOTS = {'kit': ('conv', 'follow', 'back15', 'quarter', 'helmet', 'vest'), 'carrier': ('conv', 'back15', 'vest'),
         'suit': ('conv', 'back15', 'quarter')}
for kit, pieces in KITS.items():
    reset()
    arm, body, P = load(pieces, colonist=col, piece_paths=pp)
    for light in LIGHTS:
        cam = setup(light=light); V = views(arm)
        for s in SHOTS[kit]:
            render(f'{out}{STATE}_{kit}_{s}_{light}.png', cam, *V[s], res=(1920, 1080) if s in ('conv', 'follow') else (1000, 1000))
