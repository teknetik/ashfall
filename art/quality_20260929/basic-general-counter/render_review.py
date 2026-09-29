"""Review renders for the Basic General counter dressing (Blender Cycles, source evidence only - not native Unity captures).

    sh bl.sh --python render_review.py -- <set>        set = new | old | all
Opens basic-general-counter-source-v1.blend, adds a 1.8 m mannequin proxy for Mira at the existing NPC root (A-space 0, 0, 0.7),
and renders at the eye heights the brief asks for. Porch top is A-space Y=0; first step top is Y=-0.25 (z centre 2.70).
"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path('/home/teknetik/code/ao2/art/quality_20260929/basic-general-counter')
R = OUT / 'renders'
R.mkdir(exist_ok=True)
which = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'all'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'basic-general-counter-source-v1.blend'))
sc = bpy.data.scenes['Basic General architectural repair']
bpy.context.window.scene = sc
B = lambda p: Vector((p[0], -p[2], p[1]))                  # A-space -> Blender

# ---- cycles setup
sc.render.engine = 'CYCLES'
cp = bpy.context.preferences.addons['cycles'].preferences
cp.compute_device_type = 'OPTIX'; cp.get_devices()
for d in cp.devices:
    d.use = d.type == 'OPTIX'
sc.cycles.device = 'GPU'
sc.cycles.samples = 96
sc.cycles.use_denoising = True
sc.cycles.denoiser = 'OPTIX'
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'

# ---- Mira stand-in: 1.8 m, shoulder 0.52 m, roughly the Ward Guard proportions (review proxy only)
mat = bpy.data.materials.new('Mira proxy'); mat.diffuse_color = (.55, .56, .58, 1); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.62, .63, .65, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .55
prox = bpy.data.collections.new('Review proxies'); sc.collection.children.link(prox)


def add(kind, name, loc, dim, rot=(0, 0, 0)):
    if kind == 'sphere':
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    else:
        bpy.ops.mesh.primitive_cylinder_add(vertices=32)
    o = bpy.context.object
    o.name = name; o.dimensions = dim; o.location = B(loc); o.rotation_euler = rot
    o.data.materials.append(mat)
    for c in o.users_collection:
        c.objects.unlink(o)
    prox.objects.link(o)
    return o


mx, mz = 0.0, 0.70
add('cyl', 'Mira legs', (mx, .44, mz), (.30, .30, .88))           # 0 .. 0.88
add('cyl', 'Mira torso', (mx, 1.16, mz), (.40, .26, .60))         # 0.88 .. 1.46
add('cyl', 'Mira shoulders', (mx, 1.41, mz), (.52, .24, .20))
add('cyl', 'Mira neck', (mx, 1.53, mz), (.11, .11, .12))
add('sphere', 'Mira head', (mx, 1.69, mz), (.24, .26, .29))
add('cyl', 'Mira arm L', (mx - .28, 1.05, mz), (.11, .11, .70))
add('cyl', 'Mira arm R', (mx + .28, 1.05, mz), (.11, .11, .70))
marker = add('cyl', 'Scale rod 1.0 m', (-3.5, .5, 1.2), (.03, .03, 1.0))          # 1 m rod at the porch edge
mira_objs = [o for o in prox.objects if o.name.startswith('Mira')]

# ---- old/new toggling
retired = [o for o in sc.objects if o.get('bgc_retired')]
new_objs = list(bpy.data.collections['BGC counter dressing (new)'].objects)
sidewall = [o for o in sc.objects if o.name.startswith(('Side masonry core', 'Side stone', 'Pier head bearing', 'Front reveal plaster'))]


fill = bpy.data.lights.new('Review shade fill (source render only)', 'AREA')
fill.shape = 'RECTANGLE'; fill.size = 3.2; fill.size_y = 1.2; fill.color = (1.0, .93, .82); fill.energy = 700
fill_o = bpy.data.objects.new('Review shade fill', fill); sc.collection.objects.link(fill_o)
fill_o.location = B((0, 2.35, 2.9))
fill_o.rotation_euler = (B((0, 1.0, -.9)) - fill_o.location).to_track_quat('-Z', 'Y').to_euler()


def state(new=True, mira=True, side=False, rod=False, lit=False):
    fill_o.hide_render = not lit
    for o in retired:
        o.hide_render = new
    for o in new_objs:
        o.hide_render = not new
    for o in mira_objs:
        o.hide_render = not mira
    marker.hide_render = not rod
    for o in sidewall:
        o.hide_render = side


cam = sc.camera
sc.camera = cam


def shoot(name, pos, target, lens, **kw):
    state(**kw)
    cam.location = B(pos)
    cam.rotation_euler = (B(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    cam.data.sensor_width = 36
    sc.render.filepath = str(R / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    print('rendered', name)


EYE_STEP = -.25 + 1.6          # standing on the first step, eyes 1.6 m above the step
EYE_PORCH = 1.6                # standing on the porch
SETS = {
    # front, approach, 2.4 m interaction distance from Mira (z=.7 -> z=3.1): camera stands on the step, eye 1.6 m
    'eye_approach': ((0, EYE_STEP, 3.10), (0, 1.15, -.9), 34),
    # on the porch, ~1.1 m from Mira's shoulder, slightly right so Mira does not hide the stock
    'eye_porch_left': ((-.55, EYE_PORCH, 1.85), (-1.15, 1.2, -.95), 38),
    'eye_porch_right': ((.55, EYE_PORCH, 1.85), (1.15, 1.2, -.95), 38),
    # over the counter: leaning in at the counter, eye 1.6 m, looking down at the working surface and shelves
    'over_counter': ((0.0, 1.60, 0.10), (0.0, .80, -.90), 34),
    # material close-ups at player-height inspection distance
    'close_left_bay': ((-1.45, 1.55, .20), (-1.72, 1.20, -.93), 42),
    'close_right_bay': ((1.45, 1.55, .20), (1.72, 1.20, -.93), 42),
    'close_counter_face': ((-1.2, 1.15, 1.0), (-1.3, .55, -.72), 40),
    'close_counter_top': ((.15, 1.35, -.32), (-.4, .94, -.86), 50),
    'close_hooks': ((-.4, 1.65, .55), (-.88, 1.5, -1.05), 36),
    'close_material_steel': ((.15, 1.12, -.30), (.65, .93, -.88), 62),
}
if which in ('new', 'all'):
    for k, (p, t, l) in SETS.items():
        close = k.startswith('close') or k == 'over_counter'
        shoot('new_' + k, p, t, l, new=True, mira=(not close), lit=close)
    for k in ('eye_approach', 'eye_porch_left'):
        shoot('new_nomira_' + k, *SETS[k], new=True, mira=False)
    shoot('new_lit_eye_approach', *SETS['eye_approach'], new=True, mira=True, lit=True)
    shoot('new_lit_eye_porch_left', *SETS['eye_porch_left'], new=True, mira=False, lit=True)
    # plain front elevation-ish view matching the old source-v2 'door' view (same camera) for old/new comparison
    shoot('new_door', (0, 1.65, 4.6), (0, 1.45, -.2), 35, new=True, mira=False)
    shoot('new_door_mira', (0, 1.65, 4.6), (0, 1.45, -.2), 35, new=True, mira=True)
    # side section: side walls hidden so the profile against the rear wall is visible
    shoot('new_side_section_left', (-9, 1.5, -.9), (0, 1.25, -.95), 60, new=True, mira=False, side=True)
    shoot('new_side_section_right', (9, 1.5, -.9), (0, 1.25, -.95), 60, new=True, mira=False, side=True)
    shoot('new_measure_front', (0, 1.4, 6.5), (0, 1.15, 0), 40, new=True, mira=True, side=True, rod=True)
if which in ('old', 'all'):
    for k in ('eye_approach', 'eye_porch_left', 'eye_porch_right', 'over_counter'):
        p, t, l = SETS[k]
        shoot('old_' + k, p, t, l, new=False, mira=(k != 'over_counter'))
    shoot('old_door', (0, 1.65, 4.6), (0, 1.45, -.2), 35, new=False, mira=False)
    shoot('old_door_mira', (0, 1.65, 4.6), (0, 1.45, -.2), 35, new=False, mira=True)
print('RENDER_DONE')
