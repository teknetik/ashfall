import bpy
from mathutils import Vector
A = lambda v: (round(v.x, 3), round(v.z, 3), round(-v.y, 3))
for name in ('air_water Roof to filter downfeed', 'air_water Filter manifold', 'air_water Filter manifold inlet 0.9', 'air_water Feed flange (1.7, 0.65)', 'air_water Feed retaining clamp 2.4', 'air_water Feed stand-off 2.4', 'air_water Filter wall mount 0.9', 'air_water Filter retainer (0.9, 0.52)'):
    o = bpy.data.objects[name]
    me = o.data
    print('##', name, len(me.vertices), 'verts', len(me.polygons), 'polys')
    vs = [A(o.matrix_world @ v.co) for v in me.vertices]
    if len(vs) < 80:
        print(vs)
    else:
        print(vs[:10], '...')
c = bpy.data.objects['air_water Filter canister 0.9']
print('canister verts', len(c.data.vertices))
ys = sorted({round(-(c.matrix_world @ v.co).y + 0, 3) for v in c.data.vertices})
print('canister A z levels', ys[:6], ys[-6:])
print('canister A y levels', sorted({round((c.matrix_world @ v.co).z, 3) for v in c.data.vertices}))
print('lights', [(o.name, o.type) for o in bpy.data.objects if o.type in ('LIGHT', 'CAMERA')])
# other items nearby the filter bank
for o in bpy.data.objects:
    if o.type == 'MESH':
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        mn = A(Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb))))
        mx = A(Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb))))
        ax0, ax1 = min(mn[0], mx[0]), max(mn[0], mx[0])
        # A-space bounds: x, y from z_b, z from -y_b
        x0, x1 = min(v.x for v in bb), max(v.x for v in bb)
        y0, y1 = min(v.z for v in bb), max(v.z for v in bb)
        z0, z1 = min(-v.y for v in bb), max(-v.y for v in bb)
        if x1 > 0.3 and x0 < 3.4 and y0 < 2.6 and z1 > 2.3 and 'Filter' not in o.name and 'Feed' not in o.name and 'Front masonry' not in o.name:
            print('NEAR', o.name, [round(v, 3) for v in (x0, y0, z0)], [round(v, 3) for v in (x1, y1, z1)])
