import bpy
from mathutils import Vector
def A(v): return (v[0], v[2], -v[1])
# everything whose A-bounds intersect the display opening volume (with margin), any z
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    bb = [A(o.matrix_world @ Vector(c)) for c in o.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
    if mx[0] > -2.95 and mn[0] < -1.35 and mx[1] > 0.7 and mn[1] < 2.3 and mx[2] > 1.2 and mn[2] < 2.9:
        print('HIT', o.name, o.get('group'), [round(x, 3) for x in mn], [round(x, 3) for x in mx], len(o.data.polygons), [m.name for m in o.data.materials][:2], 'hide_render', o.hide_render)
print('COLL', [(c.name, len(c.objects)) for c in bpy.data.collections])
print('CAM', [ (o.name, tuple(round(x,2) for x in o.location), o.data.lens) for o in bpy.data.objects if o.type=='CAMERA'])
print('LIGHTS', [ (o.name, o.data.type, o.data.energy, tuple(round(x,2) for x in o.location)) for o in bpy.data.objects if o.type=='LIGHT'])
print('SCENES', [s.name for s in bpy.data.scenes])
for n in ('Relay_WardGasket.007', 'Relay_WardGlass.005', 'Relay_WardStone.007', 'Relay_WardSteel.007', 'Relay_WardPaint.007'):
    m = bpy.data.materials.get(n)
    if m and m.use_nodes:
        p = m.node_tree.nodes.get('Principled BSDF')
        print(n, [round(x, 3) for x in p.inputs['Base Color'].default_value], 'r', round(p.inputs['Roughness'].default_value, 2), 'm', p.inputs['Metallic'].default_value, 'a', p.inputs['Alpha'].default_value, [ (n_.type, getattr(n_, 'image', None) and n_.image.name) for n_ in m.node_tree.nodes if n_.type == 'TEX_IMAGE'])
