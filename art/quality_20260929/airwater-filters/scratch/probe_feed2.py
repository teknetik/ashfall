import bpy
from mathutils import Vector
for n in ('air_water Roof to filter downfeed','air_water Filter manifold','air_water Twin vessel cross feed'):
    o=bpy.data.objects[n]
    bb=[o.matrix_world@Vector(c) for c in o.bound_box]
    print(n,[round(min(v[i] for v in bb),3) for i in range(3)],[round(max(v[i] for v in bb),3) for i in range(3)])
    if n.endswith('downfeed'):
        seen=set()
        for v in o.data.vertices:
            p=o.matrix_world@v.co
            k=(round(p.x,2),round(p.y,2),round(p.z,2))
            if k not in seen: seen.add(k)
        pts=sorted(seen)
        # cluster by ring centre: print 1 per 0.02
        print(len(pts)); 
        import itertools
        xs=sorted({p[0] for p in pts}); ys=sorted({p[1] for p in pts}); zs=sorted({p[2] for p in pts})
        print('x',xs[0],xs[-1],'y',ys[0],ys[-1],'z',zs[0],zs[-1])
        # centre-line segments: group verts by segment via connected components
        import bmesh
        bm=bmesh.new(); bm.from_mesh(o.data); 
        import collections
        vis=set(); comps=[]
        for v in bm.verts:
            if v.index in vis: continue
            st=[v]; c=[]
            while st:
                a=st.pop()
                if a.index in vis: continue
                vis.add(a.index); c.append(a)
                for e in a.link_edges: st.append(e.other_vert(a))
            comps.append(c)
        for c in comps:
            ps=[o.matrix_world@v.co for v in c]
            cen=sum(ps,Vector())/len(ps)
            A=lambda p:(round(9-p.y,3),round(p.z-.5,3),round(p.x+20.6,3))
            mn=[round(min(A(p)[i] for p in ps),3) for i in range(3)]; mx=[round(max(A(p)[i] for p in ps),3) for i in range(3)]
            print('comp',len(c),A(cen),mn,mx)
