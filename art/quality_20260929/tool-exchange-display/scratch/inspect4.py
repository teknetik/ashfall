import bpy
from mathutils import Vector
def A(v): return (v[0],v[2],-v[1])
for m in bpy.data.materials:
    if m.use_nodes:
        p=m.node_tree.nodes.get('Principled BSDF')
        if p: print(m.name,[round(x,3) for x in p.inputs['Base Color'].default_value],'rough',round(p.inputs['Roughness'].default_value,2),'metal',p.inputs['Metallic'].default_value,'alpha',p.inputs['Alpha'].default_value, [n.type for n in m.node_tree.nodes if n.type=='TEX_IMAGE'])
    else: print(m.name,'no nodes',list(m.diffuse_color))
groups={}
for o in bpy.data.objects:
    groups.setdefault(o.get('group'),0)
    groups[o.get('group')]+=1
print(groups)
for o in bpy.data.objects:
    n=o.name.lower()
    if any(k in n for k in ('porch','step','pavement','ground','kerb','curb','stair')): print('OBJ',o.name)
print([ (c.name,len(c.objects)) for c in bpy.data.collections], bpy.context.scene.camera, [o.name for o in bpy.data.objects if o.type in ('LIGHT','CAMERA')], bpy.context.scene.world)
o=bpy.data.objects['tool_exchange Shutter lift handle 0.47499999999999987']
bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]; print([tuple(round(x,3) for x in b) for b in bb][:8])
me=bpy.data.objects['tool_exchange Shutter guide rail -1'].data
print(len(me.vertices)); 
