import sys; sys.path.insert(0,'/home/teknetik/code/ao2/art/tutorial_set_20261002/blender')
from fitlib import *
import bmesh
bpy.ops.wm.open_mainfile(filepath=str(OUT/'mpfb'/'suit_v7.blend'))
o=bpy.data.objects['Human.high-poly']
bm=bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
uv=bm.loops.layers.uv.active
seen=set()
for v in bm.verts:
    if v.index in seen: continue
    st=[v]; isl=[]; seen.add(v.index)
    while st:
        x=st.pop(); isl.append(x)
        for e in x.link_edges:
            y=e.other_vert(x)
            if y.index not in seen: seen.add(y.index); st.append(y)
    c=sum((x.co for x in isl),Vector())/len(isl); r=sum((x.co-c).length for x in isl)/len(isl)
    us=[l[uv].uv for x in isl for l in x.link_loops]
    fn=sum((f.normal for x in isl for f in x.link_faces),Vector()); 
    out=sum(((f.calc_center_median()-c).normalized().dot(f.normal)) for x in isl[:50] for f in x.link_faces)/max(1,sum(len(x.link_faces) for x in isl[:50]))
    print('ISL n=%d c=%s r=%.4f uv x %.2f-%.2f y %.2f-%.2f outward %.2f'%(len(isl),[round(a,3) for a in c],r,min(u.x for u in us),max(u.x for u in us),min(u.y for u in us),max(u.y for u in us),out))
