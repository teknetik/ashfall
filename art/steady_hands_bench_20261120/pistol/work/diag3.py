import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..', 'kit'))
import bpy, bmesh
from mathutils import Vector
import geo as G, check as CK, pgeom as PG
from pgeom import us, ycyl, GP, MM
bpy.ops.wm.read_factory_settings(use_empty=True)
gs = PG.solid('gs')
def sv(o):
    bm = bmesh.new(); bm.from_mesh(o.data); v = G.signed_volume(bm); bm.free(); return v
def probe(o, tag, side):
    g = CK.Geo(o); t = g.bvh(o.matrix_world)
    print(tag, 'solid', G.solid_check(o), 'tris', G.tris(o), 'vol %.3e' % sv(o), 'rebate pt', CK.inside(t, GP(-20, 20, 6 * side)), 'body pt', CK.inside(t, GP(0, 0, 10 * side)), flush=True)
side = 1
for variant in ('plain', 'nobevel', 'cutter_reversed', 'fast'):
    o = G.duplicate(gs, 'scale')
    G.boolean(o, [us('_o', PG.outline(), 3.6, 30)], 'INTERSECT')
    if variant != 'nobevel':
        G.bevel(o, 0.5 * MM, 1, 30)
    probe(o, variant + ' before', side)
    c = us('_reb', [(-32, -8), (-12.9, -8), (-12.9, 42.3), (-32, 42.3)], 3.5, 9.2)
    print('   cutter vol %.3e' % sv(c), G.solid_check(c), flush=True)
    if variant == 'cutter_reversed':
        bm = bmesh.new(); bm.from_mesh(c.data); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(c.data); bm.free()
    if variant == 'fast':
        m = o.modifiers.new('b', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; m.solver = 'FLOAT' if 'FLOAT' in [e.identifier for e in m.bl_rna.properties['solver'].enum_items] else 'FAST'
        G.apply_mods(o); bpy.data.objects.remove(c, do_unlink=True)
    else:
        G.boolean(o, [c])
    probe(o, variant + ' after', side)
