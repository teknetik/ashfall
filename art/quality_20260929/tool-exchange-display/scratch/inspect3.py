import bpy
from mathutils import Vector
def A(v): return (v[0],v[2],-v[1])
for o in bpy.data.objects:
    if o.type!='MESH': continue
    n=o.name
    if 'slat' in n and (n.endswith(' 0') or n.endswith(' 1') or n.endswith(' 19')) or 'Shutter' in n or 'Shop sign face' in n or 'Awning' in n and 'upper arm' in n or 'Closed floor' in n or 'Rolled' in n and 'slat 10' in n:
        bb=[A(o.matrix_world@Vector(c)) for c in o.bound_box]
        mn=[min(v[i] for v in bb) for i in range(3)]; mx=[max(v[i] for v in bb) for i in range(3)]
        print(n,[round(x,3) for x in mn],[round(x,3) for x in mx],len(o.data.polygons),[m.name for m in o.data.materials][:2], [len(o.data.uv_layers)])
print([ (m.name, [round(c,2) for c in m.diffuse_color]) for m in bpy.data.materials])
o=bpy.data.objects['tool_exchange Shutter lift handle 0.47499999999999987']
print('handle loc',o.location, o.rotation_euler, o.scale)
