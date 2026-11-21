# kit/example/build.py: the smallest family that uses every part of the kit. A junction box: a base with a cover
# plate held by two screws, a hinged latch (0-1 rig), a fuse that slides out once the latch is open, a wipe zone.
# Run: SH/blender.sh kit/example/build.py -- --nobake          (geometry, parts.json, source .blend: seconds)
#      SH/blender.sh kit/example/check.py                      (the machine checks -> export/check.json)
#      SH/blender.sh kit/example/build.py -- --size 512 --spp 8   (a small bake, about a minute)
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from family import Family, G, MT, CT, RG
import am_parts as AP
from mathutils import Vector
MM = 0.001

F = Family('example', __file__, budget=6000)
M = F.mats
M['alloy_dusty'] = MT.make('alloy_dusty', (0.6, 0.59, 0.56), 1.0, 0.3, edge=((0.78, 0.77, 0.74), 1.0, 0.18, 0.8),
                           dirt=((0.16, 0.12, 0.09), 0.85, 0.75), wipe=('dust', (0.42, 0.35, 0.27), 0.95, 1.0))
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

# base: a block with a pocket for the fuse and two screw holes (0.1 mm clear all round: threads are not meshed)
base = G.prism('base', G.rounded_rect(60 * MM, 40 * MM, 4 * MM), 14 * MM, (0, 0, 0), X, Y, Z, M['steel'], w0=0)
G.boolean(base, [G.prism('_pocket', G.rounded_rect(34 * MM, 9 * MM, 1 * MM), 20 * MM, (-4 * MM, 0, 5 * MM), X, Y, Z, w0=0),
                 G.prism('_mouth', G.rounded_rect(34 * MM, 9 * MM, 1 * MM), 12 * MM, (-30 * MM, 0, 5 * MM), X, Y, Z, w0=0)] +
          [AP.hole_cutter(3.2 * MM, 9 * MM, (22 * MM, s * 14 * MM, 14 * MM), Z) for s in (1, -1)])
G.bevel(base, 0.5 * MM, 2)
CT.part(base, 'example', 'base', 'Junction base', kind='fixture', material='steel', mass='medium', loose=True)

# cover plate with two clearance holes, on top of the base
cover = G.plate('cover', G.rounded_rect(26 * MM, 40 * MM, 4 * MM), 1.5 * MM, (17 * MM, 0, 14.05 * MM), X, Y, Z,
                holes=[(5 * MM, 14 * MM, 1.7 * MM), (5 * MM, -14 * MM, 1.7 * MM)], mat=M['alloy_dusty'], w0=0, bevel_w=0.25 * MM)
CT.part(cover, 'example', 'cover', 'Cover plate', parent='base', material='alloy', held_by=['screw_a', 'screw_b'], steps=['x.cover'],
        origin=(17 * MM, 0, 14.05 * MM))
CT.clear(cover, offset=(0, 0, 25 * MM))
CT.zone(cover, 'dust', (17 * MM, 0, 15.6 * MM), (13 * MM, 20 * MM, 1 * MM))
CT.wipe(cover, 'dust', zone='dust', label='Caked dust')

for nm, s, drive in (('screw_a', 1, 'slot'), ('screw_b', -1, 'cross')):
    sc = AP.screw(nm, 3 * MM, 9 * MM, head='pan', drive=drive, mat=M['brass'], at=(22 * MM, s * 14 * MM, 15.6 * MM), axis=Z)
    CT.fastener(sc, 'example', nm, 'Cover screw', bit=drive, turns=6, holds=['cover'], into='base', shank_d=3 * MM,
                parent='base', material='steel', steps=['x.screws'])
    CT.clear_along(sc, 14 * MM)

# fuse: slides out of the pocket toward -X once the latch is open
fuse = G.cyl('fuse', (-21 * MM, 0, 9.5 * MM), (11 * MM, 0, 9.5 * MM), 3.6 * MM, 16, M['ceramic'], chamfer=0.6 * MM)
CT.part(fuse, 'example', 'fuse', 'Fuse', parent='base', material='ceramic', mass='tiny', symmetry=2, steps=['x.fuse'],
        origin=(-5 * MM, 0, 9.5 * MM), touches=['latch'])
CT.clear(fuse, offset=(-40 * MM, 0, 0))
CT.mark(fuse, 'probe', (-21 * MM, 0, 9.5 * MM), -X)

# latch: a bar across the pocket mouth on a hinge pin along Y
latch = G.box('latch', (-31.2 * MM, 0, 9.5 * MM), (2 * MM, 14 * MM, 11 * MM), None, M['paint_orange'])
G.bevel(latch, 0.4 * MM, 1)
CT.part(latch, 'example', 'latch', 'Fuse latch', parent='base', material='steel', mass='tiny', loose=True)

R = F.rig = RG.Rig('example', parent=base)
R.hinge('latch', (-31.2 * MM, 0, 3.6 * MM), -Y, 0, 95, [latch])
R.slide('fuse_seat', (-5 * MM, 0, 9.5 * MM), -X, 0, 30 * MM, [fuse], requires={'latch': 1.0})
R.finish()
CT.sequence([{'op': 'remove', 'part': 'fuse', 'step': 'x.fuse', 'params': {'latch': 1.0}},
             {'op': 'remove', 'part': 'screw_a', 'step': 'x.screws', 'group': 'screws'},
             {'op': 'remove', 'part': 'screw_b', 'step': 'x.screws', 'group': 'screws'},
             {'op': 'remove', 'part': 'cover', 'step': 'x.cover'}])
F.finish()
