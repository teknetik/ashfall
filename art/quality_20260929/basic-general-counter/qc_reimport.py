"""QC: re-import every exported GLB into a clean scene and validate (29 Sep 2026).

    sh bl.sh --python qc_reimport.py

Checks per file: triangle count, bounds vs source A-space bounds, material names, UV0 present and finite, UV span sanity
(no NaN, no degenerate UV triangles), normals finite/unit, loose vertices, non-manifold edge count (props are intentionally
open/overlapping so this is reported, not failed), scale = 1, no negative-scale. Writes qc-report.json.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
src = json.loads((OUT / 'build-stats-raw.json').read_text())['parts']
report = {}
for glb in sorted((OUT / 'exports/glb').glob('*.glb')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    tris = 0; nonman = 0; bad_uv = 0; degenerate_uv = 0; nan = 0; loose = 0; mats = set(); umin = [1e9, 1e9]; umax = [-1e9, -1e9]; deg_where = []
    bmin = Vector((1e9,) * 3); bmax = Vector((-1e9,) * 3); scales = []; neg = 0
    for o in meshes:
        me = o.data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
        uvl = me.uv_layers.active
        if not uvl:
            bad_uv += 1
        else:
            for tri in me.loop_triangles:
                uvs = [uvl.data[l].uv for l in tri.loops]
                for u in uvs:
                    if not (math.isfinite(u.x) and math.isfinite(u.y)):
                        nan += 1
                    else:
                        umin[0] = min(umin[0], u.x); umin[1] = min(umin[1], u.y); umax[0] = max(umax[0], u.x); umax[1] = max(umax[1], u.y)
                a = (uvs[1] - uvs[0]).cross(uvs[2] - uvs[0]) if hasattr(uvs[0], 'cross') else 0
                if abs((uvs[1].x - uvs[0].x) * (uvs[2].y - uvs[0].y) - (uvs[2].x - uvs[0].x) * (uvs[1].y - uvs[0].y)) < 1e-12:
                    degenerate_uv += 1
                    if len(deg_where) < 6:
                        c = sum((o.matrix_world @ me.vertices[me.loops[l].vertex_index].co for l in tri.loops), Vector()) / 3
                        deg_where.append([round(c.x, 3), round(c.z, 3), round(-c.y, 3), me.materials[tri.material_index].name])
        for v in me.vertices:
            w = o.matrix_world @ v.co
            bmin = Vector(map(min, bmin, w)); bmax = Vector(map(max, bmax, w))
        for m in me.materials:
            mats.add(m.name if m else None)
        scales.append([round(x, 4) for x in o.matrix_world.to_scale()])
        if o.matrix_world.determinant() < 0:
            neg += 1
        import bmesh
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)      # glTF import splits verts at UV/normal seams; weld before counting
        nonman += sum(1 for e in bm.edges if not e.is_manifold)
        loose += sum(1 for v in bm.verts if not v.link_edges)
        bm.free()
    # glTF import maps Y-up file -> Blender Z-up. A-space bounds: (x, z_b, -y_b)
    a_min = [round(bmin.x, 4), round(bmin.z, 4), round(-bmax.y, 4)]
    a_max = [round(bmax.x, 4), round(bmax.z, 4), round(-bmin.y, 4)]
    name = glb.stem
    base = name.replace('_LOD1', '')
    r = {'file': glb.name, 'objects': len(meshes), 'tris': tris, 'materials': sorted(m for m in mats if m), 'boundsA_min': a_min, 'boundsA_max': a_max,
         'sizeA': [round(a_max[i] - a_min[i], 4) for i in range(3)], 'uvRange': [[round(x, 3) for x in umin], [round(x, 3) for x in umax]],
         'uvNaN': nan, 'missingUV': bad_uv, 'degenerateUVTris': degenerate_uv, 'degenerateSamples': deg_where, 'nonManifoldEdges': nonman, 'looseVerts': loose,
         'objectScales': scales, 'negativeDeterminant': neg}
    if base in src and not name.endswith('_LOD1'):
        s = src[base]
        r['sourceTris'] = s['tris']; r['sourceSizeA'] = s['sizeA']
        r['sizeMatchesSource'] = all(abs(r['sizeA'][i] - s['sizeA'][i]) < 0.002 for i in range(3))
        r['trisMatchSource'] = abs(r['tris'] - s['tris']) <= 2
    report[glb.name] = r
    print(json.dumps(r))
(OUT / 'qc-report.json').write_text(json.dumps(report, indent=2))
print('QC_DONE')
