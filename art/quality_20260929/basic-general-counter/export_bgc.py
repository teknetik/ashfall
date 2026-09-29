"""Export the six counter-dressing modules (29 Sep 2026).

    sh bl.sh --python export_bgc.py

Reads basic-general-counter-source-v1.blend (never modifies it) and writes, per module:
  exports/glb/<Part>.glb           Y-up glTF in building-local A-space (metres). Origin = the module pivot listed in
                                   handoff.json. Materials are named BGC_<slot>; texture wiring is NOT trusted from the
                                   glTF (Unity packs MetalSmooth differently) - see materials.json.
  exports/glb/<Part>_LOD1.glb      reviewed distance LOD (only where warranted).
  exports/interchange/bgc-meshes-v1.json
                                   same idea as art/quality_20260909/basic-general/basic-general-meshes-v3.json, extended
                                   with per-material submeshes. Vertex coords are building-local, *Blender-frame converted
                                   with the project's U() mapping*, i.e. identical numbers to A-space (x, y, z); the Unity
                                   installer must apply the documented (-x, z_b, -y_b) handedness fix exactly like the
                                   Basic General v3 installer (reflect X, reverse winding, recalc tangents).
"""
import bpy, json, sys, hashlib, math
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
(OUT / 'exports/glb').mkdir(parents=True, exist_ok=True)
(OUT / 'exports/interchange').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1.blend'))
sc = bpy.data.scenes['Basic General architectural repair']
bpy.context.window.scene = sc
col = bpy.data.collections['BGC counter dressing (new)']
LOD1 = {'BGC_ShelfBay_L': .42, 'BGC_ShelfBay_R': .42, 'BGC_HookRail_L': .42, 'BGC_HookRail_R': .42, 'BGC_CounterProps': .42}


def A(v):                       # Blender world -> A-space
    return (v.x, v.z, -v.y)


def export_glb(o, path):
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    o_loc = o.location.copy()
    o.location = (0, 0, 0)          # pivot at the file origin
    bpy.ops.export_scene.gltf(filepath=str(path), use_selection=True, export_format='GLB', export_apply=False, export_yup=True,
                              export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
                              export_image_format='NONE', export_cameras=False, export_lights=False)
    o.location = o_loc


def interchange(o):
    me = o.data
    me.calc_loop_triangles()
    uvl = me.uv_layers['UV0']
    subs = {}
    verts, norms, uvs, cache = [], [], [], {}
    for tri in me.loop_triangles:
        for li in tri.loops:
            vi = me.loops[li].vertex_index
            p = o.matrix_world @ me.vertices[vi].co - o.matrix_world.translation      # relative to the pivot
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


report = {}
objs = sorted([o for o in col.objects if o.type == 'MESH'], key=lambda o: o.name)
for o in objs:
    export_glb(o, OUT / 'exports/glb' / f'{o.name}.glb')
# LOD1 via decimate on a duplicate, UVs preserved; reviewed visually afterwards
for name, ratio in LOD1.items():
    src = bpy.data.objects[name]
    d = src.copy(); d.data = src.data.copy(); d.name = name + '_LOD1'; d.data.name = name + '_LOD1'
    col.objects.link(d)
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    md = d.modifiers.new('LOD1 collapse', 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = ratio
    md.use_collapse_triangulate = True; md.delimit = {'MATERIAL', 'SEAM', 'UV'}; md.use_symmetry = False
    d.select_set(True); bpy.context.view_layer.objects.active = d
    bpy.ops.object.modifier_apply(modifier=md.name)
    export_glb(d, OUT / 'exports/glb' / f'{name}_LOD1.glb')
    d.hide_render = True; d.hide_viewport = True
parts = []
for o in sorted([o for o in col.objects if o.type == 'MESH'], key=lambda o: o.name):
    d = interchange(o)
    d['triangles'] = sum(len(s['triangles']) for s in d['submeshes']) // 3
    d['vertexCount'] = len(d['vertices'])
    parts.append(d)
    print(o.name, d['triangles'], 'tris', d['vertexCount'], 'verts', [s['material'] for s in d['submeshes']])
blob = {'convention': 'Building-local metres, +Y up, +Z avenue-facing front, +X screen-right from the avenue (A-space). '
                      'Positions are relative to each part pivot. Apply pivot offsets from handoff.json to place in the building. '
                      'Unity conversion: reflect X and reverse winding (project rule Blender(x,y,z)->Unity(-x,z,-y) with A==(x,z_b,-y_b)).',
        'buildingPivotUnity': [8, .5, 15.1], 'frontUnity': [0, 0, 1], 'parts': parts}
(OUT / 'exports/interchange/bgc-meshes-v1.json').write_text(json.dumps(blob, separators=(',', ':')))
print('EXPORT_DONE', len(parts))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1-with-lods.blend'), compress=True)
