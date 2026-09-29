"""Export the twelve Tool Exchange display/shutter modules (29 Sep 2026, task t_3751e0fd).

    sh bl.sh --python export_te.py

Reads tool-exchange-display-source-v1.blend (never modifies it) and writes, per module:
  exports/glb/<Part>.glb   Y-up glTF in building-local A-space (metres), origin = module pivot (see handoff.json).
                           Materials are named TE_<slot>; texture wiring is not trusted from glTF - see materials.json.
  exports/interchange/te-meshes-v1.json   per-material submeshes, A-space relative to each pivot, same layout as the
                           Basic General interchange (Unity installer: reflect X, reverse winding, regenerate tangents).
"""
import bpy, json
from pathlib import Path

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/tool-exchange-display')
(OUT / 'exports/glb').mkdir(parents=True, exist_ok=True)
(OUT / 'exports/interchange').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'tool-exchange-display-source-v1.blend'))
col = bpy.data.collections['TE display and shutter (new)']


def A(v):
    return (v.x, v.z, -v.y)


def export_glb(o, path):
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    loc = o.location.copy()
    o.location = (0, 0, 0)
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB', export_apply=False, export_yup=True,
                              export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
                              export_image_format='NONE', export_cameras=False, export_lights=False)
    o.location = loc


def interchange(o):
    me = o.data
    me.calc_loop_triangles()
    uvl = me.uv_layers['UV0']
    subs, verts, norms, uvs, cache = {}, [], [], [], {}
    for tri in me.loop_triangles:
        for li in tri.loops:
            vi = me.loops[li].vertex_index
            p = o.matrix_world @ me.vertices[vi].co - o.matrix_world.translation
            n = (o.matrix_world.to_3x3() @ me.corner_normals[li].vector).normalized()
            t = uvl.data[li].uv
            a = A(p); an = A(n)
            key = (round(a[0], 6), round(a[1], 6), round(a[2], 6), round(an[0], 4), round(an[1], 4), round(an[2], 4), round(t.x, 6), round(t.y, 6))
            if key not in cache:
                cache[key] = len(verts)
                verts.append([round(x, 6) for x in a]); norms.append([round(x, 5) for x in an]); uvs.append([round(t.x, 6), round(t.y, 6)])
            subs.setdefault(tri.material_index, []).append(cache[key])
    return {'name': o.name, 'pivotAuthoring': list(o['pivotAuthoring']), 'vertices': verts, 'normals': norms, 'uv0': uvs,
            'submeshes': [{'material': me.materials[k].get('ward_slot'), 'triangles': v} for k, v in sorted(subs.items())]}


objs = sorted([o for o in col.objects if o.type == 'MESH'], key=lambda o: o.name)
for o in objs:
    export_glb(o, OUT / 'exports/glb' / f'{o.name}.glb')
parts = []
for o in objs:
    d = interchange(o)
    d['triangles'] = sum(len(s['triangles']) for s in d['submeshes']) // 3
    d['vertexCount'] = len(d['vertices'])
    parts.append(d)
    print(o.name, d['triangles'], 'tris', d['vertexCount'], 'verts', [s['material'] for s in d['submeshes']])
blob = {'convention': 'Building-local metres, +Y up, +Z avenue-facing front, +X screen-right from the avenue (A-space). '
                      'Positions are relative to each part pivot. Apply pivot offsets from handoff.json. '
                      'Unity conversion: reflect X and reverse winding (project rule Blender(x,y,z)->Unity(-x,z,-y) with A==(x,z_b,-y_b)).',
        'buildingPivotUnity': [-20.6, .5, 9.0], 'buildingYawUnity': 90.0, 'parts': parts}
(OUT / 'exports/interchange/te-meshes-v1.json').write_text(json.dumps(blob, separators=(',', ':')))
print('EXPORT_DONE', len(parts))
