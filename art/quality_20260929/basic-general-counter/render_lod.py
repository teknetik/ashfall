"""LOD1 review: render the recess from the avenue (6 m and 12 m in front of the counter, eye 1.6 m) with LOD0 then LOD1.

    sh bl.sh --python render_lod.py
Uses basic-general-counter-source-v1-with-lods.blend (LOD1 objects are hidden duplicates named <Part>_LOD1).
Then compose_lod.py builds renders/compare_lod_*.png (LOD0 left, LOD1 right) plus an absolute difference image.
"""
import bpy
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
R = OUT / 'renders'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1-with-lods.blend'))
sc = bpy.data.scenes['Basic General architectural repair']
bpy.context.window.scene = sc
B = lambda p: Vector((p[0], -p[2], p[1]))
sc.render.engine = 'CYCLES'
cp = bpy.context.preferences.addons['cycles'].preferences
cp.compute_device_type = 'OPTIX'; cp.get_devices()
for d in cp.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; sc.cycles.samples = 64; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPTIX'
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.view_settings.view_transform = 'AgX'
for o in sc.objects:
    if o.get('bgc_retired'):
        o.hide_render = True
lod0 = [o for o in sc.objects if o.name.startswith('BGC_') and not o.name.endswith('_LOD1') and o.type == 'MESH']
lod1 = [o for o in sc.objects if o.name.startswith('BGC_') and o.name.endswith('_LOD1')]
for o in lod0:
    o.hide_render = False; o.hide_viewport = False
for o in lod1:
    o.hide_viewport = False
fill = bpy.data.lights.new('fill', 'AREA'); fill.shape = 'RECTANGLE'; fill.size = 3.2; fill.size_y = 1.2; fill.color = (1, .93, .82); fill.energy = 700
fo = bpy.data.objects.new('fill', fill); sc.collection.objects.link(fo); fo.location = B((0, 2.35, 2.9))
fo.rotation_euler = (B((0, 1, -.9)) - fo.location).to_track_quat('-Z', 'Y').to_euler()
cam = sc.camera
# LOD1 shares LOD0 location (copy) so they overlap exactly
for name, dist, lens in (('6m', 6.0, 30), ('12m', 12.0, 30), ('3m_near', 3.2, 34)):
    cam.location = B((0, 1.6 - .25 if dist < 4 else 1.6, dist))
    cam.rotation_euler = (B((0, 1.1, -.9)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    for lodset, label in ((lod0, 'lod0'), (lod1, 'lod1')):
        for o in lod0:
            o.hide_render = (label != 'lod0') and (o.name + '_LOD1' in bpy.data.objects)      # parts without an LOD1 stay at LOD0
        for o in lod1:
            o.hide_render = label != 'lod1'
        sc.render.filepath = str(R / f'lod_{name}_{label}.png')
        bpy.ops.render.render(write_still=True)
        print('rendered', name, label)
print('LOD_RENDER_DONE')
