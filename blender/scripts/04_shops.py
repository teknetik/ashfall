"""Author eight avenue frontages and the small Basic General stall.

Execute city_core.py first, then this file through the live Blender MCP.
All positions use Three.js metres. Collision is copied from buildShops();
facade ornament stays over the existing porches and out of the avenue.
"""
ACTIVE_LANDMARK = 'shop_rows'
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark') == ACTIVE_LANDMARK:
        bpy.data.objects.remove(obj, do_unlink=True)


def shop_prism(name, side, z, depth0, depth1, profile, key, bevel=.035):
    """Extrude an authored (facade-width, height) profile along building depth."""
    count = len(profile)
    verts = [(side * d, y, z + u) for d in (depth0, depth1) for u, y in profile]
    faces = [tuple(range(count)), tuple(reversed(range(count, count * 2)))]
    faces += [(i, i + count, (i + 1) % count + count, (i + 1) % count)
              for i in range(count)]
    if side < 0:
        faces = [tuple(reversed(face)) for face in faces]
    obj = mesh(name, verts, faces, key)
    if bevel:
        activate(obj)
        mod = obj.modifiers.new('chunky_profile_edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
        planar_uv(obj, 8 if key == 'stone' else 3)
    return obj


def shop_face(name, side, z, d, y0, y1, u0, u1, key, uvrect=(0, 0, 1, 1)):
    verts = [(side * d, y0, z + u0), (side * d, y0, z + u1),
             (side * d, y1, z + u1), (side * d, y1, z + u0)]
    face = (0, 1, 2, 3) if side > 0 else (3, 2, 1, 0)
    a, b, c, e = uvrect
    return mesh(name, verts, [face], key, [(a, b), (c, b), (c, e), (a, e)])


def shop_caption(name, text, pos, size, width, turn):
    obj = label(name, text, pos, size=size, width=width, turn=turn, key='stone')
    xs = [v.co.x for v in obj.data.vertices]
    if xs and max(xs) - min(xs) > width:
        obj.scale *= width / (max(xs) - min(xs))
        activate(obj)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def shop_collision(name, side, z, height):
    # Exact legacy collision volumes, including the 2.4 m clear door throat.
    specs = [
        ('first_step', (side * 14.1, .125, z), (.8, .25, 4.2)),
        ('porch', (side * 17, .25, z), (5, .5, 7.6)),
        ('interior_floor', (side * 20.25, .25, z), (1.5, .5, 6.5)),
        ('back', (side * 23, height / 2 + .5, z), (4, height, 7)),
        ('lintel', (side * 19.6, 3.8, z), (2.6, 1.6, 7)),
        ('roof', (side * 21.8, 4.8, z), (7.8, .35, 7.5)),
    ]
    for edge in (-1, 1):
        specs += [
            ('jamb_' + str(edge), (side * 18.7, 1.75, z + edge * 2.35), (.8, 2.5, 2.3)),
            ('side_' + str(edge), (side * 20, 1.75, z + edge * 3.25), (2.5, 2.5, .5)),
        ]
    for part, pos, size in specs:
        collider(name + '_' + part, pos, size)


def shop_module(side, index, title):
    z = (-18, -9, 9, 18)[index]
    height = (8, 10, 7, 9)[index] + (2 if side == -1 and index == 0 else 0)
    name = 'BLD_shop_' + ('e' if side == 1 else 'w') + '_%02d' % (index + 1)
    shop_collision(name, side, z, height)
    box(name + '_first_step', (side * 14.1, .125, z), (.8, .25, 4.2), 'stone', .014)
    box(name + '_porch', (side * 17, .25, z), (5, .5, 7.6), 'stone', .028)
    box(name + '_interior_floor', (side * 20.25, .25, z), (1.5, .5, 6.5), 'stone', .02)
    rear_lower_height = height - 1.2
    box(name + '_rear_mass', (side * 23, .5 + rear_lower_height / 2, z),
        (4, rear_lower_height, 7), 'metal', .055)
    for edge in (-1, 1):
        # Six-sided, chamfer-shouldered stone piers frame a deep dark stage set.
        profile = [(edge * u, y) for u, y in [(1.2, .5), (3.5, .5), (3.5, 2.60),
                                             (3.15, 3), (1.55, 3), (1.2, 2.60)]]
        if edge < 0:
            profile.reverse()
        shop_prism(name + '_angled_jamb_' + str(edge), side, z, 18.3, 19.1, profile, 'stone')
        box(name + '_side_' + str(edge), (side * 20, 1.75, z + edge * 3.25),
            (2.5, 2.5, .5), 'metal', .035)
        box(name + '_pier_shoe_' + str(edge), (side * 18.62, .69, z + edge * 2.35),
            (1.05, .38, 2.18), 'stone', .045)
        box(name + '_pier_flute_' + str(edge), (side * 18.265, 1.70, z + edge * 2.55),
            (.09, 1.54, .20), 'metal', .025)
    box(name + '_deep_lintel', (side * 19.6, 3.8, z), (2.6, 1.6, 7), 'metal', .055)
    box(name + '_overhanging_cornice', (side * 21.8, 4.8, z), (7.8, .35, 7.5), 'stone', .045)
    shop_face(name + '_dark_recess', side, z, 20.96, .5, 3, -1.24, 1.24, 'dark')
    box(name + '_sign_frame', (side * 18.21, 3.84, z), (.22, .78, 5.40), 'stone', .04)
    shop_face(name + '_sign_back', side, z, 18.087, 3.55, 4.11, -2.58, 2.58, 'dark')
    shop_caption(name + '_shop_name', title, (side * 18.071, 3.67, z), .29, 4.82, -side * math.pi / 2)
    # Upper fronts sit behind the cornice: two broad bands, not a flat tower.
    ledge_y = min(height - 1.55, 6.85)
    box(name + '_upper_belt', (side * 22.9, ledge_y, z), (4.48, .30, 7.34), 'stone', .038)
    shop_prism(name + '_shouldered_crown', side, z, 21.05, 24.95,
               [(-3.5, height - .7), (3.5, height - .7), (3.10, height + .5),
                (-3.10, height + .5)], 'metal', .05)
    box(name + '_roof_cap', (side * 23, height + .55, z), (4.4, .20, 7.4), 'stone', .04)
    box(name + '_upper_screen_frame', (side * 20.965, height - 1, z), (.12, .45, 4.7), 'dark', .024)
    shop_face(name + '_upper_screen', side, z, 20.899, height - 1.11, height - .89,
              -2.2, 2.2, 'cyan', (0, .50, .50, 1))
    # Offset cloth awnings and restrained antennae vary the repeated kit.
    if index != 1 or side == -1:
        points = [(side * 18.22, 3.30, z - 3.10), (side * 16.18, 2.95, z - 3.10),
                  (side * 16.18, 2.95, z + 3.10), (side * 18.22, 3.30, z + 3.10)]
        face = (0, 1, 2, 3) if side > 0 else (3, 2, 1, 0)
        mesh(name + '_porch_awning', points, [face], 'red' if index % 2 == 0 else 'metal',
             [(0, 1), (0, 0), (1, 0), (1, 1)])
        for edge in (-1, 1):
            # Supports sit over the blocked jamb side zones, not the door line.
            tube(name + '_awning_brace_' + str(edge),
                 [(side * 18.18, 2.3, z + edge * 2.88),
                  (side * 16.2, 2.93, z + edge * 2.88)], [.045, .045], 'metal', 5)
    if index % 2 == 0:
        shop_face(name + '_faction_banner', side, z, 18.16, .94, 2.75, 2.09, 2.80, 'red')
        tube(name + '_roof_aerial', [(side * 23.2, height + .66, z + 2.15),
                                    (side * 23.2, height + 1.75, z + 2.15)],
             [.042, .022], 'metal', 5)


names = {-1: ('FINERY', 'FIELD SUPPLY', 'REPAIRS', 'THREAD + HIDE'),
         1: ('RELAY WORKS', 'AIR + WATER', 'TOOL EXCHANGE', 'SALVAGE')}
for shop_side in (-1, 1):
    for shop_index, shop_title in enumerate(names[shop_side]):
        shop_module(shop_side, shop_index, shop_title)

# Existing separate Basic General porch, south-west of the hill. Its geometry
# remains within x[-10.75,-5.25], z[13.2,18.2]; the central standing area is open.
general_specs = [
    ('first_step', (-8, .125, 17.8), (3.2, .25, .8)),
    ('porch', (-8, .25, 15.7), (5.2, .5, 3.4)),
    ('back', (-8, 2, 13.6), (5.2, 3, .8)),
    ('side_w', (-10.4, 1.7, 14.6), (.4, 2.4, 1.8)),
    ('side_e', (-5.6, 1.7, 14.6), (.4, 2.4, 1.8)),
    ('awning', (-8, 3.1, 15.1), (5.5, .25, 3.5)),
]
for part, pos, size in general_specs:
    collider('BLD_general_' + part, pos, size)
    if part != 'awning':
        box('BLD_general_' + part, pos, size, 'metal' if part == 'back' else 'stone', .028)
mesh('BLD_general_canvas_canopy',
     [(-10.75, 3.21, 13.35), ( -5.25, 3.21, 13.35),
      (-5.25, 3.05, 16.85), (-10.75, 3.05, 16.85)], [(0, 3, 2, 1)], 'red',
     [(0, 1), (1, 1), (1, 0), (0, 0)])
box('BLD_general_sign_frame', (-8, 2.73, 16.90), (4.3, .62, .16), 'stone', .035)
box('BLD_general_sign_back', (-8, 2.73, 16.991), (4.05, .42, .035), 'dark', .008)
shop_caption('BLD_general_name', 'BASIC GENERAL', (-8, 2.60, 17.016), .29, 3.80, 0)
for gx in (-10.35, -5.65):
    tube('BLD_general_canopy_brace', [(gx, 1.96, 14.2), (gx, 3.04, 16.62)],
         [.042, .042], 'metal', 5)

stage_objects = [obj for obj in bpy.context.scene.objects
                 if obj.type == 'MESH' and obj.get('landmark') == ACTIVE_LANDMARK]
stage_triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons)
                      for obj in stage_objects if not obj.name.startswith('COL_'))
assert stage_triangles <= 14000, 'Shop render triangle budget exceeded: ' + str(stage_triangles)
AUTHORED[:] = list(dict.fromkeys(AUTHORED + [ACTIVE_LANDMARK]))
print(json.dumps({'stage': 'shops', 'triangles': stage_triangles,
                  'colliders': sum(obj.name.startswith('COL_') for obj in stage_objects)}))
save('04_shop_rows.blend')
export_world()
