"""Review renders for the Air + Water filter-bank fittings (Blender Cycles; SOURCE evidence only - not native Unity captures).

    sh bl.sh <blend> --python render_review_aw.py -- <set>[,<set>...] <old|new> [noon|shade] [scale]
Camera coordinates are A-space (building-local: +X screen-right from the avenue, +Y up, +Z toward the avenue).
"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector
OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/airwater-filters')
R = OUT / 'renders'; R.mkdir(exist_ok=True)
args = sys.argv[sys.argv.index('--') + 1:]
sets = args[0].split(','); which = args[1]; mode = args[2] if len(args) > 2 else 'noon'; scale_rods = 'scale' in args
sc = bpy.context.scene
B = lambda p: Vector((p[0], -p[2], p[1]))
sc.render.engine = 'CYCLES'
cp = bpy.context.preferences.addons['cycles'].preferences
cp.compute_device_type = 'OPTIX'; cp.get_devices()
for d in cp.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'; sc.cycles.samples = 160; sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPTIX'
sc.cycles.max_bounces = 8
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'
mat = bpy.data.materials.new('Figure proxy'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.62, .63, .65, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .55
prox = bpy.data.collections.new('Review proxies'); sc.collection.children.link(prox)

def add(kind, name, loc, dim):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    else:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32)
    o = bpy.context.object; o.name = name; o.dimensions = dim; o.location = B(loc); o.data.materials.append(mat)
    for c in o.users_collection: c.objects.unlink(o)
    prox.objects.link(o); return o
def figure(fx, fz):
    return [add('cyl', 'Fig legs', (fx, .44, fz), (.30, .30, .88)), add('cyl', 'Fig torso', (fx, 1.16, fz), (.40, .26, .60)),
            add('cyl', 'Fig shoulders', (fx, 1.41, fz), (.52, .24, .20)), add('cyl', 'Fig neck', (fx, 1.53, fz), (.11, .11, .12)),
            add('sphere', 'Fig head', (fx, 1.69, fz), (.24, .26, .29)),
            add('cyl', 'Fig arm L', (fx - .28, 1.05, fz), (.11, .11, .70)), add('cyl', 'Fig arm R', (fx + .28, 1.05, fz), (.11, .11, .70))]
fig = figure(4.9, 4.6)     # 1.8 m marker standing on the porch/paving in front of the bank, right of the vessels
rods = [add('cyl', 'Scale rod 1.8 m', (-.02, .9, 3.6), (.04, .04, 1.8)), add('cyl', 'Scale rod 1.0 m', (.14, .5, 3.6), (.04, .04, 1.0))]
for o in fig + rods: o.hide_render = True

# lights
for o in [o for o in sc.objects if o.type == 'LIGHT']: o.hide_render = True
sun = bpy.data.lights.new('Review noon sun', 'SUN'); sun.energy = 4.0; sun.angle = math.radians(1.0); sun.color = (1.0, .96, .90)
sun_o = bpy.data.objects.new('Review noon sun', sun); sc.collection.objects.link(sun_o)
sun_o.rotation_euler = (math.radians(32), math.radians(6), math.radians(-14))
bounce = bpy.data.lights.new('Review paving bounce', 'AREA'); bounce.shape = 'RECTANGLE'; bounce.size = 6; bounce.size_y = 2.0; bounce.energy = 380; bounce.color = (1.0, .90, .74)
b_o = bpy.data.objects.new('Review paving bounce', bounce); sc.collection.objects.link(b_o); b_o.location = B((1.7, -.02, 6.5))
b_o.rotation_euler = (B((1.7, 1.4, 2.5)) - b_o.location).to_track_quat('-Z', 'Y').to_euler()
sky = bpy.data.lights.new('Review sky fill', 'AREA'); sky.shape = 'RECTANGLE'; sky.size = 8; sky.size_y = 3; sky.color = (.85, .92, 1.0)
sky_o = bpy.data.objects.new('Review sky fill', sky); sc.collection.objects.link(sky_o); sky_o.location = B((1.5, 5.5, 7.0))
sky_o.rotation_euler = (B((1.7, 1.3, 2.4)) - sky_o.location).to_track_quat('-Z', 'Y').to_euler()
cam_d = bpy.data.cameras.new('Review cam'); cam = bpy.data.objects.new('Review cam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.sensor_width = 36

old_objs = [o for o in sc.objects if o.get('old_rev04')]
retired = [o for o in old_objs if o.get('aw_retired')]
new_col = bpy.data.collections.get('AW filter fittings (new)')
new_objs = list(new_col.all_objects) if new_col else []

def state(new, shade, fig_on, rods_on):
    for o in old_objs: o.hide_render = bool(new and o.get('aw_retired'))
    for o in new_objs: o.hide_render = not new
    for o in fig: o.hide_render = not fig_on
    for o in rods: o.hide_render = not rods_on
    sun_o.hide_render = shade; b_o.hide_render = shade
    sky.energy = 1400 if not shade else 2400

# name: (cam pos A, target A, lens)
EYE = 1.6
SETS = {
    'front':   ((1.7, EYE, 8.4), (1.7, 1.25, 2.8), 30),
    'oblique': ((6.6, EYE, 6.8), (1.75, 1.3, 2.9), 34),
    'oblique_l': ((-1.4, EYE, 6.4), (2.0, 1.4, 2.9), 34),
    'eye_valve': ((3.4, EYE, 5.2), (2.8, 2.0, 2.95), 36),
    'close_clamp': ((1.42, 1.08, 3.55), (1.54, .85, 3.13), 40),
    'close_valve': ((2.95, 1.78, 3.62), (2.86, 2.15, 2.95), 40),
    'close_label': ((1.7, 1.24, 3.45), (1.7, 1.17, 3.18), 30),
    'close_inlet': ((2.75, 2.05, 3.7), (2.9, 2.05, 3.05), 38),
    'close_feed': ((3.9, 2.4, 4.3), (3.15, 2.5, 3.05), 34),
    'close_foot': ((1.7, .95, 4.1), (1.7, .42, 3.0), 38),
    'top': ((1.7, 3.2, 5.3), (1.7, 1.9, 2.95), 30),
}
for k in sets:
    p, t, l = SETS[k]
    state(which == 'new', mode == 'shade', k in ('front', 'oblique', 'oblique_l', 'top') and not scale_rods, scale_rods)
    cam.location = B(p); cam.rotation_euler = (B(t) - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam_d.lens = l
    name = f'{which}_{k}_{mode}' + ('_scale' if scale_rods else '')
    sc.render.filepath = str(R / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', name)
print('RENDER_DONE')
