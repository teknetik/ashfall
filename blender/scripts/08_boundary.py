ACTIVE_LANDMARK='boundary'
for obj in list(bpy.context.scene.objects):
    if obj.get('landmark')==ACTIVE_LANDMARK:bpy.data.objects.remove(obj,do_unlink=True)
random.seed(960)
for x in [-59,59]:box('BLD_boundary_side',(x,1.5,0),(2,3,90),'stone',.04,True)
for z in [-44.5,44.5]:
    box('BLD_boundary_wall',(0,2.5,z),(120,5,1),'stone',.045,True)
    box('BLD_boundary_coping',(0,5.13,z),(120,.26,1.35),'metal',.04)
    for x in range(-56,57,7):
        box('BLD_boundary_pier',(x,2.7,z),(1.1,5.4,1.5),'stone',.04)
        box('BLD_boundary_recess',(x+2.8,4.4,z+(-.54 if z>0 else .54)),(3,.22,.04),'metal',.008)

# Original distant sandstone cliffs. Keep the same centres, nominal radii and
# maximum heights, with no collision outside the playfield. The former common
# 1.0 -> .43 radial taper made every mesa resemble a tiered polygon roof.
# These profiles retain nearly their full width up to a broken plateau rim.


def boundary_cliff_mesh(name, rings, top_center):
    """Close irregular strata rings using outward-facing side quads."""
    n = len(rings[0])
    verts = [point for ring_points in rings for point in ring_points]
    faces = []
    for row in range(len(rings) - 1):
        for j in range(n):
            a = row * n + j
            b = row * n + (j + 1) % n
            faces.append((a, a + n, b + n, b))
    bottom_center = (sum(p[0] for p in rings[0]) / n, -2,
                     sum(p[2] for p in rings[0]) / n)
    bottom_index = len(verts)
    verts.append(bottom_center)
    top_index = len(verts)
    verts.append(top_center)
    last = (len(rings) - 1) * n
    for j in range(n):
        following = (j + 1) % n
        faces.append((bottom_index, j, following))
        faces.append((top_index, last + following, last + j))
    obj = mesh(name, verts, faces, 'rust')
    obj['castShadow'] = False
    return obj


mesa_layout = [(-85,-75,25,21),(-44,-94,31,22),(-2,-105,22,25),(43,-94,29,22),
               (82,-72,34,21),(96,-30,25,16),(99,7,30,18),(94,48,28,24),(-88,56,20,28)]
for i, (x, z, h, r) in enumerate(mesa_layout):
    n = 22
    phase = random.uniform(0, math.tau)
    angles = [math.tau * j / n + random.uniform(-.025, .025) for j in range(n)]
    outline = [r * (.90 + .11 * math.sin(3 * a + phase)
                    + .06 * math.sin(7 * a - phase)) for a in angles]
    # Broad high and low sections of rim break the skyline into natural towers;
    # isolated notches read as fissures rather than identical triangular peaks.
    rim_heights = [min(h + .3, h * (.88 + .085 * math.sin(2 * a + phase)
                                  + .065 * math.sin(5 * a - phase))) for a in angles]
    for j in (i % n, (i + 9) % n):
        rim_heights[j] -= h * .075
        outline[j] *= .93
    # Small ledges are staggered across the cliff; there is no repeated wide
    # sloping roof band. Profile height and horizontal drift vary by mesa.
    split = .35 + .04 * math.sin(phase)
    levels = [(0, 1.0), (.18, .985), (split, .955),
              (split + .045, .982), (.66, .948), (.79, .959), (1, .925)]
    rings = []
    for layer, (fraction, ratio) in enumerate(levels):
        drift_x = math.sin(phase + layer * .62) * r * .022 * fraction
        drift_z = math.cos(phase * .7 + layer * .71) * r * .025 * fraction
        ring_points = []
        for j, angle in enumerate(angles):
            # Vertically coherent ribs with small changes across the strata.
            erosion = 1 + .018 * math.sin(j * 1.73 + layer * .48 + phase)
            radius = outline[j] * ratio * erosion
            y = -2 if layer == 0 else rim_heights[j] * fraction + .20 * math.sin(angle * 3 + phase + layer)
            point = (x + drift_x + math.cos(angle) * radius, y,
                     z + drift_z + math.sin(angle) * radius)
            assert math.hypot(point[0] - x, point[2] - z) <= r * 1.2
            assert point[1] <= h + .7
            ring_points.append(point)
        rings.append(ring_points)
    boundary_cliff_mesh('ENV_sandstone_mesa_%02d' % i, rings,
                        (x + r * .02 * math.sin(phase), h * .855, z))

    # Three attached broken buttresses interrupt the long side facets. They
    # occupy the original nominal mesa envelope and do not touch city walls.
    for buttress in range(3):
        angle = phase + buttress * math.tau / 3 + random.uniform(-.20, .20)
        bx = x + math.cos(angle) * r * .82
        bz = z + math.sin(angle) * r * .82
        br = r * random.uniform(.17, .245)
        bh = h * random.uniform(.36, .72)
        count = 8
        ba = [angle + math.tau * j / count for j in range(count)]
        widths = [br * random.uniform(.78, 1.04) for _ in ba]
        peaks = [bh * random.uniform(.81, 1.02) for _ in ba]
        buttress_rings = []
        for layer, (fraction, ratio) in enumerate([(0, 1), (.48, .97), (1, .91)]):
            points = []
            for j, a in enumerate(ba):
                point = (bx + math.cos(a) * widths[j] * ratio,
                         -2 if layer == 0 else peaks[j] * fraction,
                         bz + math.sin(a) * widths[j] * ratio)
                assert math.hypot(point[0] - x, point[2] - z) <= r * 1.2
                points.append(point)
            buttress_rings.append(points)
        boundary_cliff_mesh('ENV_mesa_buttress_%02d_%02d' % (i, buttress),
                            buttress_rings, (bx, bh * .84, bz))

boundary_triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons)
                         for obj in bpy.context.scene.objects
                         if obj.type == 'MESH' and obj.get('landmark') == ACTIVE_LANDMARK
                         and not obj.name.startswith('COL_'))
assert boundary_triangles < 8000, 'Boundary render triangle budget exceeded: ' + str(boundary_triangles)
print(json.dumps({'stage': 'boundary', 'renderTriangles': boundary_triangles,
                  'mesaBodies': len(mesa_layout), 'brokenButtresses': len(mesa_layout) * 3}))
if ACTIVE_LANDMARK not in AUTHORED:AUTHORED.append(ACTIVE_LANDMARK)
save('08_world_complete.blend');export_world()
