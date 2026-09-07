"""Original compact city prop kit; execute with city_core.py loaded in Blender.

These placements retain the existing world.ts footprints and leave the tested
hill stairs, avenue, shop porches and travel approach routes clear.
"""
ACTIVE_LANDMARK = 'props'
for ob in list(bpy.context.scene.objects):
    if ob.get('landmark') == ACTIVE_LANDMARK:
        bpy.data.objects.remove(ob, do_unlink=True)


def _prop_terminal(name, x, foot, z):
    box(name + '_foot', (x, foot + .07, z), (.86, .14, .76), 'stone', .022, True)
    box(name + '_body', (x, foot + .65, z), (.75, 1.30, .65), 'metal', .035, True)
    box(name + '_lower_access', (x, foot + .45, z + .34), (.52, .57, .025), 'dark', .009)
    box(name + '_screen_bezel', (x, foot + 1.10, z + .36), (.65, .48, .08), 'dark', .018)
    verts = [(x - .26, foot + .94, z + .405), (x + .26, foot + .94, z + .405),
             (x + .26, foot + 1.27, z + .405), (x - .26, foot + 1.27, z + .405)]
    mesh(name + '_interface', verts, [(0, 1, 2, 3)], 'cyan', [(0, 0), (1, 0), (1, 1), (0, 1)])
    for k in range(2):
        box(name + '_vent', (x, foot + .35 + k * .11, z + .36), (.31, .025, .02), 'metal', 0)
    box(name + '_button', (x + .20, foot + .79, z + .385), (.06, .06, .025), 'cyan', 0)


def _prop_bench(index, x, z):
    # One conservative body proxy matches the original low bench footprint.
    collider('bench_%02d' % index, (x, .36, z), (2.8, .72, .9))
    for dx in [-.96, .96]:
        box('PROP_bench_%02d_leg' % index, (x + dx, .27, z), (.25, .54, .67), 'metal', .025)
    box('PROP_bench_%02d_seat' % index, (x, .64, z), (2.8, .16, .9), 'stone', .04)
    box('PROP_bench_%02d_underbrace' % index, (x, .38, z), (2.2, .16, .19), 'metal', .018)
    for dx in [-.98, .98]:
        box('PROP_bench_%02d_seat_band' % index, (x + dx, .728, z), (.13, .016, .86), 'metal', 0)


def _prop_crate(index, x, z):
    box('PROP_crate_%02d_shell' % index, (x, .65, z), (1.3, 1.3, 1.3), 'rust', .045, True)
    box('PROP_crate_%02d_lid' % index, (x, 1.29, z), (1.32, .14, 1.32), 'metal', .018)
    for dx in [-.42, .42]:
        box('PROP_crate_%02d_strap_top' % index, (x + dx, 1.366, z), (.10, .012, 1.25), 'dark', 0)
        box('PROP_crate_%02d_strap_front' % index, (x + dx, .66, z + .656), (.10, 1.10, .012), 'dark', 0)
    box('PROP_crate_%02d_handle' % index, (x, .81, z + .67), (.35, .12, .04), 'metal', .01)
    box('PROP_crate_%02d_identifier' % index, (x - .20, .42, z + .677), (.15, .13, .015), 'stone', 0)


def _prop_beam(name, position, size, axis, angle):
    # Render and proxy keep identical rotations; do not bake an expanded AABB.
    vertical = size[1] > size[2]
    width, depth, length = size[0], (size[2] if vertical else size[1]), max(size[1], size[2])
    t = min(width, depth) * .19
    profile = [(-width / 2, -depth / 2), (width / 2, -depth / 2),
               (width / 2, -depth / 2 + t), (t / 2, -depth / 2 + t),
               (t / 2, depth / 2 - t), (width / 2, depth / 2 - t),
               (width / 2, depth / 2), (-width / 2, depth / 2),
               (-width / 2, depth / 2 - t), (-t / 2, depth / 2 - t),
               (-t / 2, -depth / 2 + t), (-width / 2, -depth / 2 + t)]
    verts = [(a, end, b) if vertical else (a, b, end)
             for end in [-length / 2, length / 2] for a, b in profile]
    n = len(profile)
    faces = [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    faces += [(i, i + n, (i + 1) % n + n, (i + 1) % n) for i in range(n)]
    if not vertical:
        faces = [tuple(reversed(face)) for face in faces]
    ob = mesh(name, verts, faces, 'rust')
    ob.location = xyz(position)
    proxy = collider(name, position, size)
    if axis == 'z':
        # A Three.js Z axis is Blender negative Y.
        ob.rotation_euler[1] = -angle
        proxy.rotation_euler[1] = -angle
    else:
        ob.rotation_euler[0] = angle
        proxy.rotation_euler[0] = angle
    return ob


box('ENV_mission_plinth', (-8, .125, -13), (7, .25, 3.5), 'stone', .025, True)
for i, x in enumerate([-10, -8, -6]):
    _prop_terminal('PROP_mission_%02d' % i, x, .25, -13.8)
for i, (x, z) in enumerate([(-5, -4), (5, -4), (5, 1)]):
    _prop_terminal('PROP_hill_market_%02d' % i, x, 1.5, z)

# Root-directed silhouette correction: a smaller north-east billboard sits
# beside the tree. Replacing the props tag also removes the old south collider.
billboard_z = -5.3
box('PROP_billboard_foot', (5.4, 1.65, billboard_z), (.70, .30, .70), 'stone', .035, True)
box('PROP_billboard_post', (5.4, 3.65, billboard_z), (.35, 4.30, .35), 'metal', .028, True)
for x in [3.71, 7.09]:
    box('PROP_billboard_frame_vertical', (x, 5.7, billboard_z), (.12, 1.8, .35), 'metal', .018)
for y in [4.86, 6.54]:
    box('PROP_billboard_frame_horizontal', (5.4, y, billboard_z), (3.5, .12, .35), 'metal', .018)
box('PROP_billboard_back', (5.4, 5.7, billboard_z), (3.22, 1.52, .13), 'dark', .01)
# High panels receive their own simple overhead collision proxy.
collider('billboard_panel', (5.4, 5.7, billboard_z), (3.5, 1.8, .35))
screen = [(3.90, 5.08, billboard_z + .081), (5.78, 5.08, billboard_z + .081),
          (5.78, 6.32, billboard_z + .081), (3.90, 6.32, billboard_z + .081)]
mesh('PROP_billboard_hill_map', screen, [(0, 1, 2, 3)], 'cyan', [(0, 0), (1, 0), (1, 1), (0, 1)])
for j, width in enumerate([.68, .55, .73, .47]):
    box('PROP_billboard_bulletin', (6.42, 6.12 - j * .24, billboard_z + .086), (width, .055, .018), 'stone', 0)
for x in [3.90, 6.90]:
    box('PROP_billboard_corner_signal', (x, 6.48, billboard_z + .19), (.18, .04, .025), 'cyan', 0)

for i, (x, z) in enumerate([(-31, -8), (-30, 8), (29, 8), (28, -10)]):
    _prop_bench(i, x, z)
for i, (x, z) in enumerate([(-29, -23), (-31, -22), (28, 22), (30, 23), (29, -24)]):
    _prop_crate(i, x, z)

for i, (x, z) in enumerate([(-35, -5), (-35, 5), (-12, -25), (12, 25), (32, 5)]):
    box('PROP_avenue_lamp_%02d_foot' % i, (x, .12, z), (.48, .24, .48), 'stone', .035, True)
    box('PROP_avenue_lamp_%02d_post' % i, (x, 2.3, z), (.18, 4.6, .18), 'metal', .018, True)
    box('PROP_avenue_lamp_%02d_head' % i, (x, 4.5, z), (.47, .52, .47), 'dark', .032, True)
    box('PROP_avenue_lamp_%02d_cap' % i, (x, 4.78, z), (.61, .13, .61), 'metal', .018)
    for side in [-1, 1]:
        box('PROP_avenue_lamp_%02d_lens' % i, (x, 4.51, z + side * .239), (.28, .24, .012), 'cyan', 0)

# Broken east-wall supports frame the existing distant opening. Rust I-beam
# flanges make the silhouette legible without filling the avenue with rubble.
box('ENV_wreck_plinth_n', (53, 1.5, -7), (7, 3, 3), 'stone', .035, True)
box('ENV_wreck_plinth_s', (54, 2, 8), (6, 4, 3), 'stone', .035, True)
_prop_beam('PROP_wreck_beam_a', (53, 5.2, -6), (.90, 8, .80), 'z', -.24)
_prop_beam('PROP_wreck_beam_b', (55, 4.7, 7), (.70, 8, .70), 'z', .25)
_prop_beam('PROP_wreck_crossbeam', (54, 8.5, 0), (1, 1, 15), 'x', .15)
for x, y, z in [(51, 2.1, -7), (54.2, 3.0, 8)]:
    box('PROP_wreck_exposed_inner', (x, y, z + 1.52), (1.2, 1.05, .10), 'dark', .018)
    for k in [-1, 1]:
        box('PROP_wreck_bolt_plate', (x + k * .42, y, z + 1.60), (.13, .79, .06), 'rust', .015)
for x, z in [(51.0, -4.9), (55.5, 5.8)]:
    box('PROP_wreck_severed_foot', (x, .20, z), (1.70, .40, 1.15), 'rust', .025, True)

if ACTIVE_LANDMARK not in AUTHORED:
    AUTHORED.append(ACTIVE_LANDMARK)
prop_triangles = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons)
                     for ob in bpy.context.scene.objects
                     if ob.type == 'MESH' and ob.get('landmark') == 'props' and not ob.name.startswith('COL_'))
combined_triangles = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons)
                         for ob in bpy.context.scene.objects
                         if ob.type == 'MESH' and ob.get('landmark') in ['props', 'grid_kiosk', 'whompah']
                         and not ob.name.startswith('COL_'))
assert combined_triangles <= 12000, 'Travel + props exceed 12,000 render triangles: %s' % combined_triangles
print('Props render triangles:', prop_triangles, 'Travel + props:', combined_triangles)
save('07_props.blend')
export_world()
