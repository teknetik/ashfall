import bpy
from mathutils import Vector
from collections import Counter
objs=[o for o in bpy.data.objects if o.type=='MESH']
print('mesh objs',len(objs), Counter(o.name.split(' ')[0] for o in objs))
print('parented', sum(1 for o in objs if o.parent), 'modifiers', sum(len(o.modifiers) for o in objs))
print('non-airwater/relay:', [o.name for o in objs if not o.name.startswith(('air_water','relay_works'))][:40])
aw=[o for o in objs if o.name.startswith('air_water')]
print('aw objs', len(aw), 'polys', sum(len(o.data.polygons) for o in aw))
mats=Counter(m.name for o in aw for m in o.data.materials); print(mats)
for m in bpy.data.materials:
    if m.name in mats:
        imgs=[(n.image.name, n.image.filepath, tuple(n.image.size), n.image.packed_file is not None) for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []
        print(m.name, imgs)
# Ground / porch below front
print([ (o.name) for o in aw if any(k in o.name.lower() for k in ('porch','step','floor','ground','slab','foundation','plinth'))])
# hide-check: geometry hit by downward ray in front of bank
dg=bpy.context.evaluated_depsgraph_get(); sc=bpy.context.scene
for xA in (0.9,1.7,2.5,-1.3,3.5):
  for zA in (3.3,3.6,4.0,5.0):
    hit,loc,nrm,idx,ob,mat=sc.ray_cast(dg, Vector((zA-20.6, 9-xA, 5.0)), Vector((0,0,-1)), distance=9)
    print('down',xA,zA, round(loc.z-.5,3) if hit else None, ob.name if hit else '')
