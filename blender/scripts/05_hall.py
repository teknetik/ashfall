"""Author the north hall with battered piers, tiered roof and antenna.

Execute city_core.py first and run through Blender MCP after stage 04.
The hall retains buildHall() collision and its x/z footprint.
"""
ACTIVE_LANDMARK = 'vanguard_hall'
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark') == ACTIVE_LANDMARK:
        bpy.data.objects.remove(obj, do_unlink=True)


def hall_taper(name, center, bottom_size, top_size, y0, y1, key='metal', bevel=.045):
    cx, cz = center
    verts = []
    for sx, sz, y in [(bottom_size[0], bottom_size[1], y0),
                      (top_size[0], top_size[1], y1)]:
        verts += [(cx - sx / 2, y, cz - sz / 2), (cx + sx / 2, y, cz - sz / 2),
                  (cx + sx / 2, y, cz + sz / 2), (cx - sx / 2, y, cz + sz / 2)]
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    obj = mesh(name, verts, faces, key)
    if bevel:
        activate(obj)
        mod = obj.modifiers.new('hall_edge_bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
        planar_uv(obj, 8 if key == 'stone' else 3)
    return obj


def hall_front(name, x0, x1, y0, y1, z, key, uvrect=(0, 0, 1, 1)):
    a, b, c, d = uvrect
    return mesh(name, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)],
                [(0, 1, 2, 3)], key, [(a, b), (c, b), (c, d), (a, d)])


def hall_portal(name, zfront, zback):
    # An eight-corner recessed stone surround, with an open center.
    outer = [(-3.45, .50), (3.45, .50), (3.45, 3.12), (2.76, 3.89),
             (2.50, 4.0), (-2.50, 4.0), (-2.76, 3.89), (-3.45, 3.12)]
    inner = [(-2.55, .50), (2.55, .50), (2.55, 2.75), (2.20, 3.17),
             (2.02, 3.24), (-2.02, 3.24), (-2.20, 3.17), (-2.55, 2.75)]
    verts = [(10 + x, y, z) for z in (zfront, zback) for loop in (outer, inner) for x, y in loop]
    faces = []
    for i in range(8):
        j = (i + 1) % 8
        if i == 0:
            # The opening reaches the floor. Close each separate foot without
            # making coplanar zero-area faces across the walkable threshold.
            faces += [(0, 16, 24, 8), (1, 9, 25, 17)]
            continue
        faces += [(i, j, j + 8, i + 8), (i + 16, i + 24, j + 24, j + 16),
                  (i, i + 16, j + 16, j), (i + 8, j + 8, j + 24, i + 24)]
    obj = mesh(name, verts, faces, 'stone')
    activate(obj)
    mod = obj.modifiers.new('portal_chunky_bevel', 'BEVEL')
    mod.width = .04
    mod.segments = 1
    bpy.ops.object.modifier_apply(modifier=mod.name)
    planar_uv(obj, 8)
    return obj


# Exact original collision volumes. No new obstacle crosses the north route.
hall_specs = [
    ('step', (10, .125, -23.9), (6, .25, .8)),
    ('plinth', (10, .25, -30.8), (13, .5, 13)),
    ('main', (10, 6, -32.5), (11, 11, 8)),
    ('front_pier_w', (5.5, 2.2, -27.5), (2, 3.4, 2)),
    ('front_pier_e', (14.5, 2.2, -27.5), (2, 3.4, 2)),
    ('lintel', (10, 4.4, -27.5), (11.5, 1, 2.5)),
]
for part, pos, size in hall_specs:
    collider('BLD_hall_' + part, pos, size)
    if part in ('step', 'plinth', 'lintel'):
        box('BLD_hall_' + part, pos, size, 'stone', .028 if part == 'step' else .045)

hall_taper('BLD_hall_lower_body', (10, -32.5), (11, 8), (11, 8), .5, 7.60)
hall_taper('BLD_hall_battered_shoulders', (10, -32.5), (11, 8), (8.8, 6.25), 7.60, 10.15)
hall_taper('BLD_hall_high_block', (10, -32.5), (8.8, 6.25), (8.15, 5.65), 10.15, 11.5)
box('BLD_hall_upper_belt', (10, 7.59, -32.5), (11.45, .29, 8.40), 'stone', .04)
box('BLD_hall_crown', (10, 11.70, -32.5), (8.8, .5, 6.3), 'stone', .045)
hall_taper('BLD_hall_antenna_house', (10, -32.5), (4.2, 3.8), (2.3, 2.25), 11.96, 13.92, 'stone')
box('BLD_hall_antenna_house_cap', (10, 13.98, -32.5), (2.65, .22, 2.65), 'metal', .04)

for hx in (5.5, 14.5):
    # Existing piers have a broad foot, long shaft and heavy chamfered head.
    box('BLD_hall_pier_foot', (hx, .76, -27.5), (2, .52, 2), 'stone', .05)
    hall_taper('BLD_hall_pier_shaft', (hx, -27.5), (1.82, 1.84), (1.46, 1.55), 1.02, 3.45, 'stone')
    box('BLD_hall_pier_cap', (hx, 3.67, -27.5), (1.92, .44, 1.94), 'stone', .045)
    box('BLD_hall_pier_metal_inlay', (hx, 2.2, -26.553), (.27, 1.92, .07), 'metal', .022)
    # Tall flanking pilasters support the battered upper silhouette.
    hall_taper('BLD_hall_upper_pilaster', (hx, -28.74), (1.18, .60), (.82, .46), 4.91, 7.76, 'stone', .035)
    hall_front('BLD_hall_pilaster_screen', hx - .17, hx + .17, 5.5, 6.66, -28.421, 'cyan', (.5, 0, 1, .5))

hall_front('BLD_hall_deep_entry_shadow', 7.15, 12.85, .5, 3.65, -28.461, 'dark')
hall_portal('BLD_hall_octagonal_portal', -28.16, -28.42)
box('BLD_hall_door_central_seam', (10, 1.8, -28.429), (.075, 2.58, .045), 'metal', .008)
box('BLD_hall_entry_sign_frame', (10, 4.39, -26.205), (6.15, .46, .08), 'metal', .02)
hall_front('BLD_hall_entry_sign_back', 7.07, 12.93, 4.235, 4.545, -26.158, 'dark')
label('BLD_hall_name', 'VANGUARD HALL', (10, 4.277, -26.135), size=.235, width=5.45, key='stone')
hall_front('BLD_hall_faction_banner', 8.75, 11.25, 5.10, 7.22, -28.442, 'red')
box('BLD_hall_banner_hanger', (10, 7.30, -28.382), (2.9, .13, .15), 'metal', .022)

# Side-wall ribs and one broad service panel add depth without small greebles.
for hx in (4.47, 15.53):
    for hz in (-30.4, -34.65):
        box('BLD_hall_side_rib', (hx, 4.1, hz), (.22, 6.55, .42), 'stone', .033)
box('BLD_hall_rear_service_band', (10, 5.6, -36.545), (7.2, .5, .13), 'dark', .02)
tube('BLD_hall_antenna', [(10, 14.05, -32.5), (10, 16.55, -32.5)], [.13, .035], 'metal', 8)
tube('BLD_hall_antenna_crossbar', [(8, 15.4, -32.5), (12, 15.4, -32.5)], [.06, .06], 'metal', 6)
tube('BLD_hall_aerial_tine', [(11.2, 15.4, -32.5), (11.2, 16.14, -32.5)], [.035, .021], 'metal', 5)

stage_objects = [obj for obj in bpy.context.scene.objects
                 if obj.type == 'MESH' and obj.get('landmark') == ACTIVE_LANDMARK]
stage_triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons)
                      for obj in stage_objects if not obj.name.startswith('COL_'))
assert stage_triangles <= 4000, 'Hall render triangle budget exceeded: ' + str(stage_triangles)
AUTHORED[:] = list(dict.fromkeys(AUTHORED + [ACTIVE_LANDMARK]))
print(json.dumps({'stage': 'hall', 'triangles': stage_triangles,
                  'colliders': sum(obj.name.startswith('COL_') for obj in stage_objects)}))
save('05_vanguard_hall.blend')
export_world()
