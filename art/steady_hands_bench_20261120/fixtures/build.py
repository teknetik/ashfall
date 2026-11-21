# fixtures/build.py: everything fixed to or standing on Brann's bench (PARTS.md). model-bench, 20-21 Nov 2026.
# Run (from the repository root, through the Blender slot):
#   SH/blender.sh art/steady_hands_bench_20261120/fixtures/build.py -- --nobake            geometry, parts.json, source .blend
#   SH/blender.sh art/steady_hands_bench_20261120/fixtures/build.py -- --size 2048 --spp 24   the bake (sets: a mats, b hardware, c schematic)
#   ... -- --sets a=4096,b=2048,c=2048      a size per set (overrides --size for the sets named)
#   ... -- --nobake --only vise,dish        a subset while working on it (board,schematic go together)
# The mask images in src/gen/ come from src/gen_masks.py and src/gen_schematic.py (system Python and ImageMagick).
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'src'), os.path.join(HERE, '..', 'tools', 'src')]
import mbk
from mbk import BenchFamily, CT
import fx_mats, fx_mats3, fx_parts as FX, fx_m3 as F3

F = BenchFamily('fixtures', __file__, budget=70000)
_bake = mbk.BK.bake


def bake_fx(objs, name, out, size, spp, *a, **k):
    """The kit's bake, then: the emit map down to 512 (orchestrator, 21 Nov: it only marks the lamps), and the as-found
    set's files written into every wipe of the set's parts, as the kit's own Family does (BenchFamily does not)."""
    t = _bake(objs, name, out, size, spp, *a, **k)
    em = t.get('emit')
    if em is not None and em.size[0] > 512:
        em.scale(512, 512); em.save()
    if t.get('dirty'):
        rel = {k_: os.path.relpath(v.filepath_raw, out) for k_, v in t['dirty'].items()}
        for o in objs:
            d = mbk.json.loads(o['sh'])
            for w in d.get('wipes', []):
                w.update({k_: rel[k_] for k_ in ('color', 'normal', 'orm')})
            o['sh'] = mbk.json.dumps(d)
    return t


mbk.BK.bake = bake_fx
M = fx_mats.library(F.mats)
M = fx_mats3.library3(M, F3.press_paint())
if '--sets' in F.argv:
    for kv in F.argv[F.argv.index('--sets') + 1].split(','):
        k, v = kv.split('=')
        F.size_of[k] = int(v)
F.size_of.setdefault('c', min(F.size, 1024))      # the schematic sheet (its drawing must read from the bench camera)
BUILD = [('worksurface', FX.build_worksurface), ('workmat', FX.build_workmat), ('partsmat', FX.build_partsmat), ('vise', FX.build_vise),
         ('dish', FX.build_dish), ('cradle', FX.build_cradle), ('pad', FX.build_pad), ('board', FX.build_board),
         # Milestone 3
         ('tray', F3.build_tray), ('bin', F3.build_bin), ('jar', F3.build_jar), ('tester', F3.build_tester), ('press', F3.build_press),
         ('moulds', F3.build_moulds), ('lamp', F3.build_lamp), ('schematic', F3.build_schematic), ('holster', F3.build_holster)]
for key, fn in BUILD:
    if F.want(key):
        o = fn(F, M)
        F.log('built', key, sum(mbk.G.tris(c) for c in mbk.bpy.data.objects if c.type == 'MESH' and 'sh' in c and c.name.startswith('fixtures_' + key)))
F3.add_places(F)
if F3.NOTES.get('absent'):
    CT.absent(F3.NOTES['absent'])
if all(F.want(k) for k in ('worksurface', 'workmat', 'partsmat')):
    F.manual_uv['a'] = FX.uv_mats(F)
F.finish()
