"""Review renders for the Tool Exchange display and shutter hardware (Blender Cycles; SOURCE evidence only - not native Unity captures).

    sh bl.sh --python render_review_te.py -- <set>      set = new | old | all | quick
Opens tool-exchange-display-source-v1.blend, adds a 1.8 m proxy figure and 1 m/1.8 m scale rods, and renders old (rev 04) vs new
from the avenue at 1.6 m eye height, an oblique, the display close-up and the shutter close-up, each in noon sun and in shade.
Camera coordinates are A-space (building-local: +X screen-right from the avenue, +Y up, +Z toward the avenue).
"""
import bpy, sys, math
from pathlib import Path
from mathutils import Vector

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/tool-exchange-display')
R = OUT / 'renders'
R.mkdir(exist_ok=True)
which = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'tool-exchange-display-source-v1.blend'))
sc = bpy.data.scenes[0]
bpy.context.window.scene = sc
B = lambda p: Vector((p[0], -p[2], p[1]))

sc.render.engine = 'CYCLES'
cp = bpy.context.preferences.addons['cycles'].preferences
cp.compute_device_type = 'OPTIX'; cp.get_devices()
for d in cp.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'
sc.cycles.samples = 128
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPTIX'
sc.cycles.max_bounces = 8
sc.cycles.transparent_max_bounces = 16
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'

# ---- 1.8 m figure proxy (review only) and scale rods
mat = bpy.data.materials.new('Figure proxy'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.62, .63, .65, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .55
prox = bpy.data.collections.new('Review proxies'); sc.collection.children.link(prox)


def add(kind, name, loc, dim):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    else:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32)
    o = bpy.context.object
    o.name = name; o.dimensions = dim; o.location = B(loc)
    o.data.materials.append(mat)
    for c in o.users_collection:
        c.objects.unlink(o)
    prox.objects.link(o)
    return o


fx, fz = -.50, 3.30
fig = [add('cyl', 'Fig legs', (fx, .44, fz), (.30, .30, .88)), add('cyl', 'Fig torso', (fx, 1.16, fz), (.40, .26, .60)),
       add('cyl', 'Fig shoulders', (fx, 1.41, fz), (.52, .24, .20)), add('cyl', 'Fig neck', (fx, 1.53, fz), (.11, .11, .12)),
       add('sphere', 'Fig head', (fx, 1.69, fz), (.24, .26, .29)),
       add('cyl', 'Fig arm L', (fx - .28, 1.05, fz), (.11, .11, .70)), add('cyl', 'Fig arm R', (fx + .28, 1.05, fz), (.11, .11, .70))]
rod18 = add('cyl', 'Scale rod 1.8 m', (-.02, .9, 3.3), (.04, .04, 1.8))
rod1 = add('cyl', 'Scale rod 1.0 m', (.14, .5, 3.3), (.04, .04, 1.0))
rods = [rod18, rod1]

new_objs = list(bpy.data.collections['TE display and shutter (new)'].objects)
retired = [o for o in sc.objects if o.get('te_retired')]

# ---- lights: noon sun (high, slightly from the avenue side) and shade (sun off, sky + a weak bounce from the paving)
for o in [o for o in sc.objects if o.type == 'LIGHT']:
    o.hide_render = True
sun = bpy.data.lights.new('Review noon sun', 'SUN'); sun.energy = 4.0; sun.angle = math.radians(1.0); sun.color = (1.0, .96, .90)
sun_o = bpy.data.objects.new('Review noon sun', sun); sc.collection.objects.link(sun_o)
sun_o.rotation_euler = (math.radians(58), 0, math.radians(-20))          # Blender: rot X 58 = high, tipped toward +Y (the building); -Z yaw
sun_o.rotation_euler = (math.radians(32), math.radians(6), math.radians(-14))
bounce = bpy.data.lights.new('Review paving bounce', 'AREA'); bounce.shape = 'RECTANGLE'; bounce.size = 6; bounce.size_y = 2.0
bounce.energy = 380; bounce.color = (1.0, .90, .74)
b_o = bpy.data.objects.new('Review paving bounce', bounce); sc.collection.objects.link(b_o)
b_o.location = B((0, -.02, 6.5))
b_o.rotation_euler = (B((-1.2, 1.4, 2.5)) - b_o.location).to_track_quat('-Z', 'Y').to_euler()
sky = bpy.data.lights.new('Review sky fill', 'AREA'); sky.shape = 'RECTANGLE'; sky.size = 8; sky.size_y = 3; sky.energy = 1400; sky.color = (.85, .92, 1.0)
sky_o = bpy.data.objects.new('Review sky fill', sky); sc.collection.objects.link(sky_o)
sky_o.location = B((-1.0, 5.5, 7.0))
sky_o.rotation_euler = (B((-1.0, 1.3, 2.4)) - sky_o.location).to_track_quat('-Z', 'Y').to_euler()

cam = [o for o in sc.objects if o.type == 'CAMERA'][0]
sc.camera = cam
cam.data.sensor_width = 36


def state(new=True, fig_on=True, rods_on=False, shade=False):
    for o in retired:
        o.hide_render = new
    for o in new_objs:
        o.hide_render = not new
    if HIDE_GLASS:
        bpy.data.objects['TE_DisplayGlazing'].hide_render = True
    for o in fig:
        o.hide_render = not fig_on
    for o in rods:
        o.hide_render = not rods_on
    sun_o.hide_render = shade
    b_o.hide_render = shade
    sky_o.hide_render = False
    sky.energy = 1400 if not shade else 2400


HIDE_GLASS = False


def shoot(name, pos, target, lens, **kw):
    global HIDE_GLASS
    HIDE_GLASS = 'close_tools' in name
    state(**kw)
    cam.location = B(pos)
    cam.rotation_euler = (B(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    sc.render.filepath = str(R / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


EYE = 1.6
SETS = {
    'front':       ((-.55, EYE, 8.5), (.45, 1.55, 0), 30),                     # avenue front, both display and shutter
    'oblique':     ((-5.2, EYE, 6.2), (-.6, 1.35, 1.0), 34),                   # from the left-front along the wall
    'eye_display': ((-2.15, EYE, 4.7), (-2.15, 1.45, 0), 34),                  # 1.6 m eye, 2.5 m in front of the glass
    'close_display': ((-2.0, 1.55, 3.35), (-2.15, 1.45, 0), 42),               # leaning in at the glass
    'close_tools': ((-2.15, 1.50, 3.05), (-2.15, 1.50, 2.0), 22),               # through the glass (glass hidden): whole board
    'close_tools_L': ((-2.62, 1.75, 2.90), (-2.62, 1.60, 2.0), 40),            # wrench + rail + tags
    'close_tools_R': ((-1.75, 1.35, 2.90), (-1.75, 1.35, 2.0), 40),            # hammer + cutters
    'close_shutter': ((.85, 1.45, 4.0), (1.025, .70, 2.7), 42),                # handle plates + lock at 1.6 m eye
    'close_guide': ((-.55, 1.5, 3.7), (-.66, 1.1, 2.7), 42),
}
if which.startswith('only:'):
    for k in which[5:].split(','):
        p, t, l = SETS[k]
        shoot(f'new_{k}_noon', p, t, l, new=True, fig_on=False, shade=False)
        if k == 'close_tools':
            pass
if which in ('new', 'all', 'quick'):
    for k, (p, t, l) in SETS.items():
        if which == 'quick' and k not in ('front', 'close_display'):
            continue
        for mode in ('noon', 'shade'):
            if k == 'close_tools' and mode == 'shade':
                continue
            shoot(f'new_{k}_{mode}', p, t, l, new=True, fig_on=(k in ('front', 'oblique')), shade=(mode == 'shade'))
    shoot('new_front_scale', *SETS['front'], new=True, fig_on=True, rods_on=True)
if which in ('old', 'all', 'quick'):
    for k in ('front', 'oblique', 'eye_display', 'close_display', 'close_shutter'):
        if which == 'quick' and k not in ('front', 'close_display'):
            continue
        for mode in ('noon', 'shade'):
            p, t, l = SETS[k]
            shoot(f'old_{k}_{mode}', p, t, l, new=False, fig_on=(k in ('front', 'oblique')), shade=(mode == 'shade'))
print('RENDER_DONE')
if which == 'scale':
    shoot('new_front_scale', *SETS['front'], new=True, fig_on=True, rods_on=True)
    shoot('new_eye_display_scale', *SETS['eye_display'], new=True, fig_on=False, rods_on=False)
