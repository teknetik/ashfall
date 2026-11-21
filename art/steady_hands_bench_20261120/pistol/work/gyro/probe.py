# Rays into a pistol .blend: which part each ray hits first and where (P mm). Usage: blender -b X.blend -P probe.py
import bpy, json
from mathutils import Vector
dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene
def ray(o, d):
    ok, loc, n, i, ob, m = sc.ray_cast(dg, Vector(o) * 0.001, Vector(d))
    return (ob.name, [round(x * 1000, 2) for x in loc], [round(x, 2) for x in n]) if ok else None
print('FRAME rays from -y')
for x in (54, 56, 58, 60, 62, 64, 66):
    for z in (21, 22.5, 24, 25.5, 27, 28.5):
        print('PROBE', x, z, ray((x, -40, z), (0, 1, 0)))
print('BACK rays from +x')
for z in (-26, -28, -29, -30, -32, -40, -50, -54, -56, -58, -60, -62, -64, -66, -68):
    for y in (-6, 0, 6):
        print('PROBE', y, z, ray((160, y, z), (-1, 0, 0)))
