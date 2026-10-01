"""Blender 5.2 headless: assemble the eight basin mountain chunks from work/chunks/*.npz (Unity space) and export
Assets/AthenHill/Art/Terrain/BasinMountains/BasinMountains.glb, one chunk object at a time (memory cap 6 GB).

Space: glTFast imports glTF (x, y, z) as Unity (-x, y, z); Blender's exporter writes Blender (x, y, z) as glTF
(x, z, -y). So a Unity point (X, Y, Z) is authored at Blender (-X, -Z, Y), the same convention as the original
blender/scripts/18_desert_terrain.py. Normals are written as custom split normals; COLOR_0 is the 'TerrainLight'
point attribute (R sun visibility, G sky access), UV0 = Unity XZ / 16.

Run: $O/blender.sh art/basin_mountains_20261001/basin_blender.py
"""
import json, sys, time
from pathlib import Path
import bpy
import numpy as np

ROOT = Path('/home/teknetik/code/ao2')
HERE = ROOT / 'art/basin_mountains_20261001'
CHUNKS = HERE / 'work/chunks'
OUT = ROOT / 'unity/AthenHill/Assets/AthenHill/Art/Terrain/BasinMountains/BasinMountains.glb'
BLEND = HERE / 'basin_mountains.blend'
NAMES = ['BasinMountains_%02d' % s for s in range(8)]


def clear():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes): bpy.data.meshes.remove(m)


def build(name):
    d = np.load(CHUNKS / (name + '.npz'))
    P, Nn, C, UV, I = d['P'].astype(np.float64), d['N'].astype(np.float64), d['C'], d['UV'], d['I'].astype(np.int64)
    vb = np.stack([-P[:, 0], -P[:, 2], P[:, 1]], 1)
    nb = np.stack([-Nn[:, 0], -Nn[:, 2], Nn[:, 1]], 1)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(vb)); me.vertices.foreach_set('co', vb.ravel())
    me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel())
    me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3))
    me.update(calc_edges=True)
    me.polygons.foreach_set('use_smooth', np.ones(len(I), bool))
    me.normals_split_custom_set_from_vertices([tuple(n) for n in nb])
    col = me.color_attributes.new(name='TerrainLight', type='FLOAT_COLOR', domain='POINT')
    col.data.foreach_set('color', C.astype(np.float64).ravel())
    uv = me.uv_layers.new(name='UV0')
    uv.data.foreach_set('uv', UV[I.ravel()].astype(np.float64).ravel())
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob['source'] = 'art/basin_mountains_20261001 (numpy heightfield + stream-power erosion, RTIN mesh)'
    return ob, len(I), len(vb)


def main():
    t0 = time.time()
    clear()
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    rec = {}
    objs = []
    for n in NAMES:
        ob, nt, nv = build(n)
        objs.append(ob); rec[n] = dict(triangles=nt, vertices=nv)
        print(n, nt, nv, round(time.time() - t0, 1), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT), export_format='GLB', use_selection=True, export_cameras=False,
                              export_lights=False, export_normals=True, export_texcoords=True, export_materials='NONE',
                              export_vertex_color='NAME', export_vertex_color_name='TerrainLight', export_all_vertex_colors=False,
                              export_yup=True, export_apply=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    rec['glb'] = str(OUT.relative_to(ROOT)); rec['seconds'] = round(time.time() - t0, 1)
    (HERE / 'blender-export.json').write_text(json.dumps(rec, indent=1))
    print('EXPORTED', json.dumps(rec))


if __name__ == '__main__':
    main()
