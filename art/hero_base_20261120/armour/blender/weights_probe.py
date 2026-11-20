"""Print the body's skin weights on the torso surface at a grid of heights and directions (front, front-side, side,
back-side, back) to see how far the collarbones reach down the chest and back on the new rig."""
import sys; sys.path.insert(0, '/home/teknetik/code/ao2/art/hero_base_20261120/armour/blender')
import bpy, bmesh, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import hlib as H
arm, body = H.load_hero()
bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table(); bvh = BVHTree.FromBMesh(bm)
gn = {g.index: g.name for g in body.vertex_groups}
def wat(p):
    hit = bvh.find_nearest(p, 0.3); f = bm.faces[hit[2]]; tot = {}
    for v in f.verts:
        for g in body.data.vertices[v.index].groups: tot[gn[g.group]] = tot.get(gn[g.group], 0) + g.weight / len(f.verts)
    return ' '.join('%s %.2f' % (k.replace('Shoulder', 'Clav').replace('Spine', 'Sp'), w) for k, w in sorted(tot.items(), key=lambda kv: -kv[1]) if w > 0.03)
for z in (1.56, 1.52, 1.48, 1.44, 1.40, 1.36, 1.32, 1.28, 1.24, 1.20, 1.16, 1.12):
    for tag, d in (('front', (0, -1)), ('front+10', (0.10, -1)), ('front+16', (0.16, -1)), ('side', (1, 0.0)), ('back+16', (0.16, 1)), ('back+10', (0.10, 1)), ('back', (0, 1))):
        if tag == 'side': o = Vector((0.6, 0.01, z)); dr = Vector((-1, 0, 0))
        else: o = Vector((d[0], d[1], z)); dr = Vector((0, -d[1], 0))
        hit = bvh.ray_cast(o, dr, 2.0)
        if hit[0] is None: continue
        print('W z=%.2f %-9s x=%.2f y=%.2f | %s' % (z, tag, hit[0].x, hit[0].y, wat(hit[0])))
for n in ('LeftShoulder', 'RightShoulder', 'LeftArm', 'RightArm', 'Spine', 'Spine01'):
    for act in ('idle', 'walk', 'run'):
        mx = 0.0
        a = next(a for a in bpy.data.actions if a.name.startswith(act)); ad = arm.animation_data or arm.animation_data_create(); ad.action = a
        try:
            if a.slots: ad.action_slot = a.slots[0]
        except Exception: pass
        f0, f1 = a.frame_range; angs = []
        for f in range(int(f0), int(f1) + 1, max(1, int((f1 - f0) / 12))):
            bpy.context.scene.frame_set(f); pb = arm.pose.bones[n]
            q = pb.matrix_basis.to_quaternion(); angs.append(math.degrees(q.angle))
        print('ROT %-14s %-5s local rotation from rest: min %.1f max %.1f deg' % (n, act, min(angs), max(angs)))
