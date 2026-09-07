"""Authored travel landmarks. Execute with city_core.py loaded through Blender MCP.

All positions remain Three.js metres (Y up). The two travel pads retain the
accepted Phase 1 support heights and route. Render frames never fill apertures.
"""

def _travel_clear(landmark):
    global ACTIVE_LANDMARK
    ACTIVE_LANDMARK = landmark
    for ob in list(bpy.context.scene.objects):
        if ob.get('landmark') == landmark:
            bpy.data.objects.remove(ob, do_unlink=True)


def _travel_outward(ob):
    # The shared ring helper's Z-facing winding is inward; correct this local
    # asset without changing the helper used by other authors.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return ob


def _travel_wedge(name, center, outer, inner, depth, a0, a1, key='stone'):
    # Stone voussoir in the YZ plane: each ring faces along X.
    verts = []
    for xoff in [-depth / 2, depth / 2]:
        for angle, radius in [(a0, outer), (a1, outer), (a1, inner), (a0, inner)]:
            verts.append((center[0] + xoff, center[1] + radius * math.sin(angle),
                          center[2] + radius * math.cos(angle)))
    faces = [(0, 1, 2, 3), (7, 6, 5, 4), (4, 5, 1, 0),
             (5, 6, 2, 1), (6, 7, 3, 2), (7, 4, 0, 3)]
    ob = mesh(name, verts, faces, key)
    activate(ob)
    edge = ob.modifiers.new('stone_edge', 'BEVEL')
    edge.width = .022
    edge.segments = 1
    bpy.ops.object.modifier_apply(modifier=edge.name)
    planar_uv(ob, 8)
    return ob


def _travel_arc(name, center, outer, inner, depth, start, span, key, segments=32, axis='x'):
    # Unlike a torus, this is an authored flat-faced band with an open centre.
    verts, faces = [], []
    for j in range(segments + 1):
        angle = start + span * j / segments
        for d, radius in [(-depth / 2, outer), (-depth / 2, inner),
                          (depth / 2, outer), (depth / 2, inner)]:
            local = ((d, radius * math.sin(angle), radius * math.cos(angle))
                     if axis == 'x' else (radius * math.cos(angle), radius * math.sin(angle), d))
            verts.append(tuple(center[k] + local[k] for k in range(3)))
    for j in range(segments):
        a, b = j * 4, (j + 1) * 4
        faces.extend([(a, b, b + 1, a + 1), (a + 2, a + 3, b + 3, b + 2),
                      (a, a + 2, b + 2, b), (a + 1, b + 1, b + 3, a + 3)])
    end = segments * 4
    faces.extend([(0, 1, 3, 2), (end, end + 2, end + 3, end + 1)])
    return mesh(name, verts, faces, key)


def _travel_terminal(x, foot, z):
    box('PROP_lattice_terminal_foot', (x, foot + .10, z), (1.60, .20, 1.30), 'stone', .045, True)
    box('PROP_lattice_terminal_body', (x, foot + .70, z), (1.32, 1.20, 1.0), 'metal', .045, True)
    # Sloping console top, facing the player arriving from the south.
    verts = [(x - .70, foot + 1.20, z + .58), (x + .70, foot + 1.20, z + .58),
             (x + .70, foot + 1.75, z - .45), (x - .70, foot + 1.75, z - .45),
             (x - .70, foot + 1.06, z + .58), (x + .70, foot + 1.06, z + .58),
             (x + .70, foot + 1.60, z - .45), (x - .70, foot + 1.60, z - .45)]
    mesh('PROP_lattice_console_bezel', verts,
         [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], 'dark')
    collider('lattice_console_head', (x, foot + 1.40, z + .065), (1.4, .70, 1.03))
    screen = [(x - .55, foot + 1.294, z + .425), (x + .55, foot + 1.294, z + .425),
              (x + .55, foot + 1.674, z - .285), (x - .55, foot + 1.674, z - .285)]
    mesh('PROP_lattice_interface', screen, [(0, 1, 2, 3)], 'cyan', [(0, 0), (1, 0), (1, 1), (0, 1)])
    for sx in [-1, 1]:
        box('PROP_lattice_console_cheek', (x + sx * .69, foot + .68, z), (.12, 1.0, .92), 'stone', .025)
    box('PROP_lattice_console_access', (x, foot + .60, z + .515), (.94, .73, .035), 'dark', .01)
    for j in range(3):
        box('PROP_lattice_console_vent', (x, foot + .45 + j * .12, z + .54), (.53, .035, .025), 'metal', 0)
    box('PROP_lattice_status', (x, foot + .93, z + .55), (.24, .055, .04), 'cyan', 0)


_travel_clear('grid_kiosk')
box('ENV_lattice_step', (0, .125, -33.6), (4.4, .25, .8), 'stone', .018, True)
box('ENV_lattice_pad', (0, .25, -38), (8, .5, 8), 'stone', .035, True)
for x in [-3.72, 3.72]:
    box('ENV_lattice_pad_edge', (x, .505, -38), (.14, .01, 7.4), 'dark', 0)
    box('ENV_lattice_pad_signal', (x, .514, -38.9), (.04, .008, 2.8), 'cyan', 0)

_travel_terminal(0, .5, -39)
# A low-mass technological hoop, distinct from the heavy stone gate pair.
hoop = (0, 4.0, -40.7)
_travel_outward(ring('PROP_lattice_hoop_shell', hoop, 2.65, 2.23, .34, 'metal', 'z', 40))
_travel_outward(ring('PROP_lattice_hoop_recess', (0, 4, -40.515), 2.53, 2.32, .035, 'dark', 'z', 40))
_travel_outward(ring('PROP_lattice_hoop_light', (0, 4, -40.489), 2.32, 2.275, .02, 'cyan', 'z', 40))
for j in range(16):
    angle = math.tau * (j + .5) / 16
    radial = 2.445
    center = (math.cos(angle) * radial, 4 + math.sin(angle) * radial, -40.7)
    proxy = collider('lattice_hoop_%02d' % j, center, (.96, .44, .34))
    # Local X runs along the tangent; Blender Z is Three.js Y.
    proxy.rotation_euler[1] = -(angle + math.pi / 2)
    if j % 2 == 0:
        clamp = box('PROP_lattice_hoop_clamp_%02d' % j, center, (.30, .50, .44), 'stone', .025)
        clamp.rotation_euler[1] = -(angle + math.pi / 2)
for x in [-1.45, 1.45]:
    box('PROP_lattice_pedestal', (x, .69, -40.7), (.95, .38, 1.0), 'stone', .045, True)
    box('PROP_lattice_support', (x, 1.45, -40.7), (.42, 1.28, .46), 'metal', .035, True)
for x in [-3.3, 3.3]:
    for z in [-34.7, -41.25]:
        box('PROP_lattice_bollard_base', (x, .60, z), (.55, .20, .55), 'stone', .035, True)
        box('PROP_lattice_bollard', (x, 1.04, z), (.34, .70, .34), 'metal', .028, True)
        box('PROP_lattice_bollard_signal', (x, 1.355, z + .175), (.22, .08, .025), 'cyan', 0)
if ACTIVE_LANDMARK not in AUTHORED:
    AUTHORED.append(ACTIVE_LANDMARK)


_travel_clear('whompah')
box('ENV_ring_step_n', (0, .125, 32.8), (4.4, .25, .8), 'stone', .018, True)
box('ENV_ring_step_s', (0, .125, 39.4), (4.4, .25, .8), 'stone', .018, True)
box('ENV_ring_pad', (0, .25, 36.1), (12, .5, 5.8), 'stone', .035, True)
# An open lower sector meets two feet instead of a raised threshold: a 2 m-wide
# passage remains clear from pad height through the centre of each aperture.
start, span, count = math.radians(-40), math.radians(260), 18
for index, x in enumerate([-4.2, 4.2]):
    center = (x, 3.4, 36.1)
    for j in range(count):
        a0 = start + span * j / count + .004
        a1 = start + span * (j + 1) / count - .004
        depth = 1.10 if j == count // 2 else 1.0
        _travel_wedge('PROP_ring_%d_stone_%02d' % (index, j), center, 3.10, 2.36, depth, a0, a1)
        a = (a0 + a1) / 2
        proxy = collider('ring_%d_segment_%02d' % (index, j),
                         (x, 3.4 + math.sin(a) * 2.73, 36.1 + math.cos(a) * 2.73),
                         (depth, .74, .72))
        proxy.rotation_euler[0] = math.pi / 2 - a
    _travel_arc('PROP_ring_%d_inner_lining' % index, center, 2.37, 2.23, 1.02,
                start, span, 'dark', 36)
    # Only a thin signal on the facing edge; the entire hole remains transparent.
    facing = x + (.523 if x < 0 else -.523)
    _travel_arc('PROP_ring_%d_interface_edge' % index, (facing, 3.4, 36.1), 2.265, 2.225, .022,
                start, span, 'cyan', 36)
    for sign in [-1, 1]:
        z = 36.1 + sign * 2.03
        box('PROP_ring_%d_foot' % index, (x, .71, z), (1.65, .42, 1.50), 'stone', .045, True)
        box('PROP_ring_%d_brace' % index, (x, 1.24, z), (1.24, .88, .93), 'metal', .045, True)
        box('PROP_ring_%d_foot_inset' % index, (facing + (.12 if x < 0 else -.12), 1.25, z),
            (.04, .50, .58), 'dark', .01)
        box('PROP_ring_%d_foot_signal' % index, (facing + (.145 if x < 0 else -.145), 1.30, z),
            (.02, .20, .06), 'cyan', 0)
    box('PROP_ring_%d_keystone' % index, (x, 6.45, 36.1), (1.20, .46, .66), 'stone', .03, True)
# Compact controls sit beside, never on, the central route to z=36.
box('PROP_ring_status_foot', (2.52, .60, 38.05), (.84, .20, .65), 'stone', .025, True)
box('PROP_ring_status_body', (2.52, 1.12, 38.05), (.64, .84, .52), 'metal', .035, True)
box('PROP_ring_status_face', (2.52, 1.31, 38.32), (.48, .23, .025), 'dark', .01)
box('PROP_ring_status_signal', (2.52, 1.39, 38.34), (.27, .04, .015), 'cyan', 0)
if ACTIVE_LANDMARK not in AUTHORED:
    AUTHORED.append(ACTIVE_LANDMARK)

travel_triangles = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons)
                       for ob in bpy.context.scene.objects
                       if ob.type == 'MESH' and ob.get('landmark') in ['grid_kiosk', 'whompah']
                       and not ob.name.startswith('COL_'))
assert travel_triangles <= 6600, 'Travel geometry exceeds its 6,600-triangle allocation: %s' % travel_triangles
print('Travel authored render triangles:', travel_triangles)
save('06_travel.blend')
export_world()
