# tools/build.py: the Field Toolkit and Brann's bench tools (PARTS.md). model-bench, 20 Nov 2026; model-tools from
# 21 Nov 2026 (the eleven new tools in src/tl_new.py, three texture sets).
# Run (through the Blender slot):
#   SH/blender.sh art/steady_hands_bench_20261120/tools/build.py -- --nobake              geometry, parts.json, source .blend
#   SH/blender.sh art/steady_hands_bench_20261120/tools/build.py -- --size 2048 --spp 24  the bake
# Texture sets: a = every carried hand tool, r = the roll, b = what stands on the bench (oil bottle, iron stand, solder
# reel, third hand). --size-a N, --size-r N, --size-b N set one set's atlas; --reuse-sets r,b keeps those sets' last bake
# (same geometry and UVs) so a long bake can be split over two slot holds.
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, 'src')]
import mbk
from mbk import BenchFamily, CT, Vector, BK
import tl_mats, tl_parts as TL, tl_roll as RL, tl_new as TN, tl_hero as TH

F = BenchFamily('tools', __file__, budget=80000)   # raised from 60k by the orchestrator, 21 Nov 09:55
M = tl_mats.library(F.mats)
argv = F.argv
for tag in ('a', 'r', 'b'):
    k = '--size-' + tag
    if k in argv:
        F.size_of[tag] = int(argv[argv.index(k) + 1])
REUSE = argv[argv.index('--reuse-sets') + 1].split(',') if '--reuse-sets' in argv else []
if REUSE:
    _bake = BK.bake

    def _bake_or_reuse(objs, family, outdir, size=2048, spp=24, **kw):
        tag = family.rsplit('_', 1)[-1]
        if tag in REUSE:
            F.log('reusing the last bake of set', tag)
            return F.load_bake(tag, size)
        return _bake(objs, family, outdir, size, spp, **kw)
    BK.bake = _bake_or_reuse

# the emission map (only the applicator's paste glows) is baked at the set's size and then cut to 512 (orchestrator, 21 Nov)
_bake0 = BK.bake


def _bake_small_emit(objs, family, outdir, size=2048, spp=24, **kw):
    t = _bake0(objs, family, outdir, size, spp, **kw)
    im = t.get('emit')
    if im is not None and im.size[0] > 512:
        im.scale(512, 512)
        im.save()
        F.log('emission map of', family, 'cut to 512')
    return t
BK.bake = _bake_small_emit

# the toolkit's tools, each in its own frame
sd = TH.build_screwdriver(F, M)
bb = TH.build_bitblock(F, M)
pl = TH.build_pliers(F, M)
cu = TH.build_cutters(F, M)
pu = TH.build_punch(F, M)
st = TN.build_strippers(F, M)
wb = TN.build_wirebrush(F, M)
pk = TN.build_pick(F, M)
sc = TN.build_scribe(F, M)
roll = RL.build_roll(F, M)
Mroll = roll['root'].matrix_world.copy()


def pocket(key, d, finish):
    """Seat a tool in its pocket on the unrolled roll, with its drawn-out pose and the seat mark that rides the roll."""
    Ms = RL.seat_matrix(key, d['y_tip'])
    o = finish(Mroll @ Ms)
    CT.clear(o, offset=Mroll.to_3x3() @ Vector((0, 0.095, 0.015)))
    RL.add_seat(F, roll, key, Ms)
    F.log('seated', key, mbk.G.tris(o))
    return o


pocket('screwdriver', sd, lambda Mw: TL.finish_screwdriver(F, M, sd, Mw))
pocket('bitblock', bb, lambda Mw: TL.finish_bitblock(F, M, bb, Mw))
pocket('pliers', pl, lambda Mw: TL.finish_scissor(F, M, pl['root'], pl['b'], 'pliers', 'Combination pliers', Mw, 34.0, (0, 0.047, 0.0057), (0, -0.07, 0.0057),
                                                 ['turn', 'seat', 'window'], ['tool:pliers'], ['s1.lead', 's1.pin', 's2.stripped', 's2.circlip', 's4.open', 's5.rotor'],
                                                 '0 = closed (as found), 1 = open 34 degrees'))
pocket('cutters', cu, lambda Mw: TL.finish_scissor(F, M, cu['root'], cu['b'], 'cutters', 'Wire cutters', Mw, 30.0, (0, 0.024, 0.0059), (0, -0.065, 0.0059),
                                                  ['point'], ['tool:cutters'], ['s1.bind', 's2.board', 's2.leads', 's3.trim'],
                                                  '0 = closed (as found), 1 = open 30 degrees'))
pocket('punch', pu, lambda Mw: TL.finish_punch(F, M, pu, Mw))
pocket('strippers', st, lambda Mw: TN.finish_strippers(F, M, st, Mw))
pocket('wirebrush', wb, lambda Mw: TN.finish_wirebrush(F, M, wb, Mw))
pocket('pick', pk, lambda Mw: TN.finish_pick(F, M, pk, Mw))
pocket('scribe', sc, lambda Mw: TN.finish_scribe(F, M, sc, Mw))
# Brann's
ma = TH.build_mallet(F, M)
TL.finish_mallet(F, M, ma)
TL.build_oil(F, M)
TN.finish_file(F, M, TN.build_file_flat(F, M), 'file_flat', 'Flat file', ['tool:file'], ['s3.file', 's4.flash'])
TN.finish_file(F, M, TN.build_file_round(F, M), 'file_round', 'Round file', ['tool:file_round'], ['s4.flash'])
TN.finish_snips(F, M, TN.build_snips(F, M))
TN.finish_drill(F, M, TN.build_drill(F, M))
TN.finish_iron(F, M, TN.build_iron(F, M), TN.build_iron_stand(F, M), TN.build_solder_reel(F, M))
TN.finish_applicator(F, M, TN.build_applicator(F, M))
TN.finish_thirdhand(F, M, TN.build_thirdhand(F, M))
# texture sets (model-tools, 21 Nov): the roll on its own set, every carried tool on the hand-tool set
F.set_of['tools_roll'] = 'r'
F.set_of['tools_mallet'] = 'a'
F.size_of.setdefault('b', min(F.size, 2048))
F.finish()
