"""Inspect the retrofit's hydroponics meshes (art/ward_retrofit_20260926/ward-retrofit-v1.blend): per-material triangle
counts and loose-part bounds in Unity world coordinates (x, y up, z)."""
import bpy, bmesh, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath='/home/teknetik/code/ao2/art/ward_retrofit_20260926/ward-retrofit-v1.blend')
out = {}
for ob in bpy.data.objects:
    if not ob.name.startswith('Hydroponics bays') or ob.type != 'MESH': continue
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(ob.matrix_world)
    per = {}
    for f in bm.faces:
        m = me.materials[f.material_index].name if me.materials else '-'
        per[m] = per.get(m, 0) + len(f.verts) - 2
    # loose parts
    bm.verts.ensure_lookup_table()
    seen = set(); parts = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; seen.add(v.index); pts = []
        mats = set()
        while stack:
            a = stack.pop(); pts.append(a.co.copy())
            for f in a.link_faces: mats.add(me.materials[f.material_index].name if me.materials else '-')
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen: seen.add(b.index); stack.append(b)
        lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        # blender (-x, -z, y) -> unity
        ux = (-hi.x, -lo.x); uz = (-hi.y, -lo.y); uy = (lo.z, hi.z)
        parts.append(dict(n=len(pts), mats=sorted(mats), x=[round(a, 2) for a in ux], y=[round(a, 2) for a in uy], z=[round(a, 2) for a in uz]))
    out[ob.name] = dict(tris=per, parts=len(parts), sample=parts)
    print(ob.name, per, 'parts', len(parts))
json.dump(out, open('/home/teknetik/code/ao2/art/hydroponics_20261001/review/retrofit-hydro-parts.json', 'w'), indent=0)
