"""Fitted original colonist armour for the MPFB game_engine skeleton.

Load this module, then call build_armour(body, rig) in the live Blender session.
The caller owns body masking, posing, scene setup and export. This module never
changes the supplied body/rig and creates only tagged, skinned armour meshes.
Coordinates are Blender world XYZ, with the character facing -Y. Dimensions
come from actual rest bones and rays against the evaluated skin surface.
"""
import bpy
import bmesh
import json
import math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ARMOUR_TAG = 'colonistArmourV1'
ARMOUR_LIMIT = 12000


def armour_diagnostics(objects):
    """Counts actual constructed topology; no subdivision or hidden copies."""
    materials = set()
    triangles = 0
    for obj in objects:
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
        materials.update(mat.name for mat in obj.data.materials if mat)
    return {'objects': len(objects), 'triangles': triangles,
            'materials': sorted(materials), 'materialCount': len(materials),
            'triangleLimit': ARMOUR_LIMIT,
            'weightedVertices': sum(len(o.data.vertices) for o in objects)}


def build_armour(body, rig):
    """Build and return <=12k triangles of segmented, three-material armour."""
    required = ['pelvis', 'spine_01', 'spine_02', 'spine_03'] + [part + '_' + side for side in ('l', 'r')
                for part in ('upperarm', 'lowerarm', 'thigh', 'calf', 'foot')]
    missing = [name for name in required if name not in rig.data.bones]
    if missing:
        raise ValueError('Missing game_engine bones: ' + ', '.join(missing))
    if body.type != 'MESH' or rig.type != 'ARMATURE':
        raise TypeError('build_armour requires an MPFB mesh and armature')

    # Idempotence is scoped to this kit attached to this rig. Other characters,
    # accepted assets, world objects, skin materials and rig data are untouched.
    for old in list(bpy.context.scene.objects):
        if old.get(ARMOUR_TAG) and old.parent == rig:
            data = old.data
            bpy.data.objects.remove(old, do_unlink=True)
            if data.users == 0:
                bpy.data.meshes.remove(data)

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(depsgraph)
    skin_mesh = evaluated.to_mesh()
    try:
        skin_vertices = [evaluated.matrix_world @ v.co for v in skin_mesh.vertices]
        surface = BVHTree.FromPolygons(skin_vertices,
                                      [tuple(p.vertices) for p in skin_mesh.polygons])
    finally:
        evaluated.to_mesh_clear()
    to_local = rig.matrix_world.inverted()
    objects = []
    fit_counts = {'skinHits': 0, 'boundedFallbacks': 0}
    height = max(v.z for v in skin_vertices) - min(v.z for v in skin_vertices)
    scale = height / 1.8

    def bone(name):
        b = rig.data.bones[name]
        return rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local

    def make_material(name, color, roughness, metallic, emissive=False):
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*color, 1)
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*color, 1)
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Metallic'].default_value = metallic
        shader.inputs['Specular IOR Level'].default_value = .32
        # Broad faces carry one coherent colour. Only the narrow bevel faces
        # receive a slightly lighter edge; no centre-fan colour interpolation.
        if not emissive:
            attr = mat.node_tree.nodes.get('Armour_color')
            if not attr:
                attr = mat.node_tree.nodes.new('ShaderNodeVertexColor')
                attr.name = 'Armour_color'
            attr.layer_name = 'COLOR_0'
            mat.node_tree.links.new(attr.outputs['Color'], shader.inputs['Base Color'])
        if emissive:
            shader.inputs['Emission Color'].default_value = (*color, 1)
            shader.inputs['Emission Strength'].default_value = 1.35
        return mat

    palette = {'olive': (.095, .113, .076),
               'dark': (.025, .032, .030),
               'cyan': (.045, .65, .64)}
    mats = {'olive': make_material('MAT_colonist_armour_olive', palette['olive'], .71, .32),
            'dark': make_material('MAT_colonist_armour_graphite', palette['dark'], .86, .08),
            'cyan': make_material('MAT_colonist_armour_cyan', palette['cyan'], .42, .12, True)}

    def mesh(name, verts, faces, material, weights, wear=None, smooth=False,
             top_normals=None, top_face_start=None, top_face_end=None):
        data = bpy.data.meshes.new('ARM_' + name)
        data.from_pydata([to_local @ Vector(p) for p in verts], [], faces)
        data.update()
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(data)
        bm.free()
        obj = bpy.data.objects.new('ARM_' + name, data)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = rig
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = Matrix.Identity(4)
        obj[ARMOUR_TAG] = True
        obj['assetRole'] = 'segmented_colonist_armour'
        data.materials.append(mats[material])
        color = data.color_attributes.new(name='COLOR_0', type='FLOAT_COLOR', domain='CORNER')
        uv = data.uv_layers.new(name='UV0')
        base = palette[material]
        split_normals = []
        normal_to_local = rig.matrix_world.transposed().to_3x3()
        for poly in data.polygons:
            is_top = top_face_start is not None and top_face_start <= poly.index < top_face_end
            poly.use_smooth = smooth or is_top
            for li in poly.loop_indices:
                vi = data.loops[li].vertex_index
                # Per-face assignment is deliberate: broad face loops share the
                # exact same albedo, even where they meet a worn bevel loop.
                amount = .14 if top_face_start is not None and 0 <= poly.index < top_face_start else 0
                p = Vector(verts[vi])
                target = (.19, .20, .15) if material == 'olive' else (.055, .06, .052)
                color.data[li].color = ((1., 1., 1., 1.) if material == 'cyan' else
                                       tuple(base[k] * (1 - amount) + target[k] * amount
                                             for k in range(3)) + (1.,))
                uv.data[li].uv = (p.x * 3.0, p.z * 3.0)
                split_normals.append(tuple((normal_to_local @ top_normals[vi]).normalized())
                                     if is_top and top_normals else tuple(poly.normal))
        if top_normals:
            data.normals_split_custom_set(split_normals)
        for i, point in enumerate(verts):
            influences = weights(Vector(point)) if callable(weights) else {weights: 1.}
            total = sum(influences.values())
            for key, value in influences.items():
                if value <= 0:
                    continue
                group = obj.vertex_groups.get(key) or obj.vertex_groups.new(name=key)
                group.add([i], value / total, 'REPLACE')
        armature = obj.modifiers.new('Colonist_skin', 'ARMATURE')
        armature.object = rig
        objects.append(obj)
        return obj

    def ray_surface(core, direction, fallback, clearance=0):
        direction = Vector(direction).normalized()
        hit, _, _, distance = surface.ray_cast(Vector(core), direction, fallback * 2.2)
        if hit is not None and distance > .006 * scale and distance < fallback * 2.15:
            fit_counts['skinHits'] += 1
            radius = max(fallback * .63, min(distance, fallback * 1.65))
        else:
            fit_counts['boundedFallbacks'] += 1
            radius = fallback
        return Vector(core) + direction * (radius + clearance)

    def torso_point(x, z, clearance=0, back=False):
        x, z = x * scale, z * scale
        y = 1.5 * scale if back else -1.5 * scale
        direction = Vector((0, -1 if back else 1, 0))
        hit, _, _, _ = surface.ray_cast(Vector((x, y, z)), direction, 2 * scale)
        if hit is not None:
            fit_counts['skinHits'] += 1
            return hit - direction * clearance
        fit_counts['boundedFallbacks'] += 1
        return Vector((x, (.09 if back else -.105) * scale, z)) - direction * clearance

    def plate(name, outline, mapper, material, weights, thickness=.012,
              clearance=.012, crown=.005, inset=.08):
        """Closed contoured shell: backing, chamfer, inset face, raised centre.

        Skin fitting is sampled once for each plate/frame. The broad surface
        is analytic and smooth; chamfer loops keep their own hard normals.
        """
        angular = getattr(mapper, 'angular', False)
        if angular:
            sampled = []
            for a, b in zip(outline, outline[1:] + outline[:1]):
                steps = max(1, math.ceil(abs(b[0] - a[0]) / .70))
                sampled.extend([(a[0] + (b[0] - a[0]) * i / steps,
                                 a[1] + (b[1] - a[1]) * i / steps) for i in range(steps)])
            outline = sampled
        n = len(outline)
        center = (sum(p[0] for p in outline) / n, sum(p[1] for p in outline) / n)
        if getattr(mapper, 'torso', False):
            mapper = fitted_torso_mapper(mapper, center)
        crown *= .20
        verts, faces, wear, normals = [], [], [], []

        def surface_normal(u, v, depth):
            eps = .001
            du = mapper(u+eps,v,depth)-mapper(u-eps,v,depth)
            dv = mapper(u,v+eps,depth)-mapper(u,v-eps,depth)
            outward = mapper(u,v,depth+.001*scale)-mapper(u,v,depth)
            normal = du.cross(dv)
            if normal.length_squared < 1e-12:
                normal = outward
            if normal.dot(outward) < 0:
                normal = -normal
            return normal.normalized()
        rings = [(0, clearance, 0),
                 (0, clearance + thickness * .40, .17),
                 (inset, clearance + thickness, .30)]
        if angular and max(p[0] for p in outline) - min(p[0] for p in outline) > .80:
            # A refitted interior ring keeps the plate's broad face outside
            # the curved limb. A single centre fan would cut across its skin.
            rings.append((.52, clearance + thickness + crown * .7, 0))
        for shrink, depth, edge_wear in rings:
            for u, v in outline:
                p = (u + (center[0] - u) * shrink,
                     v + (center[1] - v) * shrink)
                verts.append(mapper(*p, depth * scale))
                wear.append(edge_wear if material != 'cyan' else 0)
                normals.append(surface_normal(*p,depth*scale))
        for ring in range(len(rings) - 1):
            for j in range(n):
                k = (j + 1) % n
                a, b = ring * n + j, ring * n + k
                faces.append((a, b, b + n, a + n))
        verts.append(mapper(*center, (clearance + thickness + crown) * scale))
        wear.append(0)
        normals.append(surface_normal(*center,(clearance+thickness+crown)*scale))
        last = (len(rings) - 1) * n
        for j in range(n):
            faces.append((last + j, last + (j + 1) % n, len(rings) * n))
        faces.append(tuple(reversed(range(n))))
        return mesh(name, verts, faces, material, weights, wear,
                    top_normals=normals, top_face_start=2*n,
                    top_face_end=len(faces)-1)

    def fitted_torso_mapper(raw, center):
        """Fit one restrained quadratic skin patch, avoiding vertex ray spikes."""
        u,v=center
        h=.026
        c=raw(u,v,0)
        left,right=raw(u-h,v,0),raw(u+h,v,0)
        low,high=raw(u,v-h,0),raw(u,v+h,0)
        # XY body front/back uses world Y for depth. Chest contour is smooth,
        # while small armour attachments use this same fitted local frame.
        sy=max(-1.1,min(1.1,(right.y-left.y)/(2*h*scale)))
        sz=max(-1.0,min(1.0,(high.y-low.y)/(2*h*scale)))
        cy=max(-4.,min(4.,(right.y+left.y-2*c.y)/(h*h*scale)))
        cz=max(-3.,min(3.,(high.y+low.y-2*c.y)/(h*h*scale)))
        outward=(raw(u,v,.001)-c).normalized()

        def point(x,z,depth):
            dx,dz=x-u,z-v
            y=c.y+scale*(sy*dx+sz*dz+.5*cy*dx*dx+.5*cz*dz*dz)
            return Vector((c.x+dx*scale,y,c.z+dz*scale))+outward*depth
        return point

    def octagon(cx, cy, width, height, bevel=.14):
        x, y, a, b = cx, cy, width / 2, height / 2
        return [(x-a+a*bevel, y-b), (x+a-a*bevel, y-b), (x+a, y-b+b*bevel),
                (x+a, y+b-b*bevel), (x+a-a*bevel, y+b), (x-a+a*bevel, y+b),
                (x-a, y+b-b*bevel), (x-a, y-b+b*bevel)]

    def ribbon(name, points, mapper, width, material, weights, clearance=.032):
        for i, (a, b) in enumerate(zip(points, points[1:])):
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            if length < 1e-5:
                continue
            px, py = -dy/length*width/2, dx/length*width/2
            outline = [(a[0]+px,a[1]+py),(a[0]-px,a[1]-py),
                       (b[0]-px,b[1]-py),(b[0]+px,b[1]+py)]
            plate(name+'_'+str(i), outline, mapper, material, weights,
                  thickness=.003, clearance=clearance, crown=0, inset=.12)

    def limb_mapper(bone_name, radius, extra=0):
        a, b = bone(bone_name)
        axis = (b-a).normalized()
        front = Vector((0, -1, 0))
        front = (front - axis * front.dot(axis)).normalized()
        side = axis.cross(front).normalized()
        if side.x * a.x < 0:
            side = -side

        # Measure a few sections, then evaluate a bounded smooth elliptical
        # sleeve. Independent rays at every vertex amplified armpit/shoulder
        # discontinuities into long shards in the original audition.
        sections=[]
        for t in (0.,.25,.50,.75,1.):
            core=a.lerp(b,t)
            expected=radius*scale*(1.07-.28*t)
            measured=[]
            for direction in (front,-front,side,-side):
                hit,_,_,distance=surface.ray_cast(core,direction,expected*1.50)
                if hit is not None and distance>.006*scale:
                    fit_counts['skinHits']+=1
                    measured.append(max(expected*.78,min(distance,expected*1.15)))
                else:
                    fit_counts['boundedFallbacks']+=1
                    measured.append(expected)
            sections.append(((measured[0]+measured[1])/2,
                             (measured[2]+measured[3])/2))

        def profile(t):
            t=max(0.,min(1.,t))*4
            i=min(3,int(t));w=t-i
            # Smoothstep joins remove slope jumps between sampled cross sections.
            w=w*w*(3.-2.*w)
            return tuple(sections[i][j]*(1-w)+sections[i+1][j]*w for j in (0,1))

        def point(theta, t, clearance):
            core = a.lerp(b, t)
            rf,rs=profile(t)
            padding=clearance+extra*scale
            return core+front*(math.cos(theta)*(rf+padding))+side*(math.sin(theta)*(rs+padding))
        point.angular = True
        return point

    def wrap_band(name, lo, hi, t, half_width, mapper, material, weights,
                  clearance=.015, thickness=.007):
        # Several fitted short sectors preserve curvature around the back of
        # a limb; one broad quadrilateral would bridge through the body.
        count = max(1, math.ceil((hi - lo) / .63))
        for i in range(count):
            a = lo + (hi - lo) * i / count
            b = lo + (hi - lo) * (i + 1) / count
            plate(name+'_'+str(i), [(a,t-half_width),(b,t-half_width),
                                    (b,t+half_width),(a,t+half_width)],
                  mapper,material,weights,clearance=clearance,
                  thickness=thickness,crown=0,inset=.035)

    def fastener(name, u, v, mapper, weights, clearance, radius=.0028):
        """A small recessed mechanical fixing, measured in metres on any map."""
        p=mapper(u,v,clearance*scale)
        ax=(mapper(u+.001,v,clearance*scale)-mapper(u-.001,v,clearance*scale)).normalized()
        ay=(mapper(u,v+.001,clearance*scale)-mapper(u,v-.001,clearance*scale)).normalized()
        normal=ax.cross(ay).normalized()
        outward=mapper(u,v,clearance*scale+.001)-p
        if normal.dot(outward)<0:normal=-normal
        ay=normal.cross(ax).normalized()
        vv,ff=[],[]
        for depth,r in ((0,radius),(.0012,radius*.72)):
            for j in range(8):
                a=math.tau*j/8
                vv.append(p+normal*(depth*scale)+(ax*math.cos(a)+ay*math.sin(a))*(r*scale))
        for j in range(8):ff.append((j,(j+1)%8,(j+1)%8+8,j+8))
        ff.extend([tuple(reversed(range(8))),tuple(range(8,16))])
        mesh(name,vv,ff,'dark',weights)

    # Rigid chest laminae form a broad broken V. Spine bending occurs in the
    # overlapping abdominal lames below, rather than bending the breastplates.
    front = lambda x, z, d: torso_point(x, z, d)
    back = lambda x, z, d: torso_point(x, z, d, True)
    front.torso = True
    back.torso = True
    chest = 'spine_03'

    # A standing textile collar covers the neckline transition. Its open top
    # follows the neck instead of leaving a saw-toothed material boundary.
    neck_center = bone('neck_01')[0] if 'neck_01' in rig.data.bones else Vector((0,0,1.552*scale))

    def collar_map(theta, t, d):
        zlow=neck_center.z-.110*scale
        zhigh=neck_center.z+(.025-.013*max(0,math.cos(theta)))*scale
        # Flared cloth foundation overlaps the shoulder/upper-chest skin-mask
        # edge. The narrow standing part rises under the beard at the top.
        shoulder_flare=max(0.,1.-t/.42)**2
        rx=(.083-.003*t+.099*shoulder_flare)*scale+d
        ry=(.090-.004*t+.042*shoulder_flare)*scale+d
        return Vector((neck_center.x+math.sin(theta)*rx,
                       neck_center.y-math.cos(theta)*ry,zlow+(zhigh-zlow)*t))
    collar_map.angular = True
    cv,cf=[],[]
    collar_segments=28
    collar_rings=[(0,0),(.22,0),(.45,0),(1,0),
                  (1,-.005*scale),(.45,-.005*scale),(.22,-.005*scale),(0,-.005*scale)]
    for t,depth in collar_rings:
        for j in range(collar_segments):
            cv.append(collar_map(math.tau*j/collar_segments,t,depth))
    for ring in range(len(collar_rings)):
        nextring=(ring+1)%len(collar_rings)
        for j in range(collar_segments):
            k=(j+1)%collar_segments
            cf.append((ring*collar_segments+j,ring*collar_segments+k,
                       nextring*collar_segments+k,nextring*collar_segments+j))
    mesh('standing_textile_collar',cv,cf,'dark',chest,smooth=True)
    for i,t in enumerate((.58,.67,.76,.85,.94)):
        vv,ff=[],[]
        for band_t,depth in ((t-.017,0),(t,.0015*scale),(t+.017,0)):
            for j in range(collar_segments):
                vv.append(collar_map(math.tau*j/collar_segments,band_t,depth))
        for ring in range(2):
            for j in range(collar_segments):
                k=(j+1)%collar_segments
                ff.append((ring*collar_segments+j,ring*collar_segments+k,
                           (ring+1)*collar_segments+k,(ring+1)*collar_segments+j))
        mesh('collar_knit_welt_'+str(i),vv,ff,'dark',chest,smooth=True)
    for sign,suffix in ((1,'L'),(-1,'R')):
        plate('collar_edge_'+suffix,
              [(sign*.73,.45),(sign*.97,.29),(sign*1.40,.35),
               (sign*1.48,.99),(sign*1.08,1.05),(sign*.77,.93)],
              collar_map,'olive',chest,clearance=.003,thickness=.004,crown=0,inset=.08)

    for sign, suffix in ((1, 'L'), (-1, 'R')):
        def mirrored(points):
            return [(sign*x, z) for x, z in points]
        breast = mirrored([(.015,1.395),(.057,1.462),(.138,1.449),(.191,1.391),
                           (.178,1.301),(.092,1.250),(.025,1.289)])
        pec_surface=fitted_torso_mapper(front,
                    (sum(p[0] for p in breast)/len(breast),sum(p[1] for p in breast)/len(breast)))
        plate('pectoral_gasket_'+suffix, breast, front, 'dark', chest,
              clearance=.009, thickness=.014, crown=.006, inset=.04)
        plate('pectoral_'+suffix, breast, front, 'olive', chest,
              clearance=.025, thickness=.019, crown=.012)
        ribbon('pectoral_panel_seam_'+suffix,
               mirrored([(.042,1.413),(.080,1.392),(.153,1.427)]),
               pec_surface,.0028,'dark',chest,.046)
        plate('pectoral_service_cover_'+suffix,octagon(sign*.127,1.385,.032,.025),
              pec_surface,'olive',chest,clearance=.046,thickness=.002,crown=0,inset=.10)
        for i,(x,z) in enumerate(((.063,1.441),(.163,1.388),(.115,1.385))):
            fastener('pectoral_fixing_'+suffix+str(i),sign*x,z,pec_surface,chest,.049)
        # Secondary overlapping diagonal lamina gives a real cut into silhouette.
        lower = mirrored([(.023,1.340),(.072,1.312),(.177,1.373),(.183,1.333),
                          (.101,1.275),(.048,1.276),(.024,1.298)])
        plate('lower_breast_lamina_'+suffix, lower, front, 'olive', chest,
              clearance=.048, thickness=.010, crown=.004)
        ribbon('chest_channel_'+suffix, mirrored([(.046,1.310),(.086,1.293),(.149,1.332)]),
               front, .014, 'dark', chest, .062)
        ribbon('chest_cyan_'+suffix, mirrored([(.053,1.310),(.084,1.300),(.139,1.333)]),
               front, .005, 'cyan', chest, .067)
        plate('clavicle_'+suffix,
              mirrored([(.018,1.468),(.050,1.508),(.110,1.494),(.153,1.459),
                        (.118,1.439),(.061,1.458)]), front, 'olive', chest,
              clearance=.018, thickness=.013, crown=.004)
        ribbon('collar_cyan_'+suffix, mirrored([(.030,1.469),(.064,1.482),(.087,1.475)]),
               front, .004, 'cyan', chest, .040)
        # Side ribs wrap under the armpit; visible dark gaps permit compression.
        for i in range(3):
            z = 1.265 - .054*i
            plate('side_rib_'+suffix+str(i),
                  mirrored([(.097,z+.026),(.157,z+.062),(.181,z+.027),
                            (.157,z-.019),(.116,z-.033)]), front, 'olive',
                  chest if i == 0 else 'spine_02', clearance=.014,
                  thickness=.010, crown=.004)
        # Load-bearing shoulder straps are segmented instead of one thick slab.
        for i in range(4):
            z = 1.445 + .018*i
            plate('strap_link_'+suffix+str(i), octagon(sign*.128,z,.047,.024),
                  front, 'dark' if i%2 else 'olive', chest,
                  clearance=.035, thickness=.009, crown=.001)
        plate('back_scapula_'+suffix,
              mirrored([(.018,1.440),(.111,1.474),(.184,1.405),(.173,1.286),
                        (.066,1.250),(.017,1.301)]), back, 'olive', chest,
              clearance=.016, thickness=.013, crown=.007)

    # Central sternum closure and articulated abdominal stack.
    for i in range(5):
        z = 1.398 - i*.034
        plate('sternum_lock_'+str(i), octagon(0,z,.046 if i<3 else .061,.040),
              front, 'dark' if i%2 else 'olive', chest,
              clearance=.050, thickness=.010, crown=.002)
    for i, (z, w) in enumerate(((1.214,.156),(1.164,.143),(1.114,.134))):
        bname = 'spine_02' if i == 0 else 'spine_01'
        plate('abdomen_lame_'+str(i),
              [(-w/2,z+.027),(-w*.34,z+.039),(w*.34,z+.039),(w/2,z+.027),
               (w*.39,z-.022),(0,z-.032),(-w*.39,z-.022)],
              front, 'olive' if i != 1 else 'dark', bname,
              clearance=.014, thickness=.012, crown=.004)
    plate('rear_power_shell', octagon(0,1.354,.108,.190), back, 'dark', chest,
          clearance=.038, thickness=.024, crown=.006)
    for i in range(4):
        plate('rear_power_lame_'+str(i), octagon(0,1.417-i*.040,.088,.025),
              back, 'olive', chest, clearance=.066, thickness=.008, crown=.001)

    # Pelvis belt uses a fitted radial band. Pouches have a tapered sculpted
    # body, separate lid, closing tab and worn lower guards.
    pa, pb = bone('pelvis')
    belt_z = pb.z / scale - .012
    for i in range(12):
        angle = math.tau*i/12
        half = math.tau/12*.45

        def belt_map(theta, z, d):
            core = Vector((pa.x, pa.y, z*scale))
            direction = Vector((math.sin(theta),-math.cos(theta),0))
            return ray_surface(core,direction,.14*scale,d)
        belt_map.angular = True
        plate('belt_segment_'+str(i),
              [(angle-half,belt_z-.023),(angle+half,belt_z-.023),
               (angle+half,belt_z+.023),(angle-half,belt_z+.023)],
              belt_map, 'dark', 'pelvis', clearance=.018, thickness=.010, crown=.001)
    plate('belt_buckle', octagon(0,belt_z,.082,.060), front, 'olive','pelvis',
          clearance=.030, thickness=.014,crown=.002)
    plate('buckle_recess', octagon(0,belt_z,.048,.033), front, 'dark','pelvis',
          clearance=.046,thickness=.003,crown=0)
    for sign,suffix in ((1,'L'),(-1,'R')):
        for i in range(2 if sign == 1 else 1):
            x = sign*(.113+i*.062)
            z = belt_z-.032
            shape = octagon(x,z,.060,.123, .24)
            plate('belt_pouch_'+suffix+str(i),shape,front,'dark','pelvis',
                  clearance=.030,thickness=.033,crown=.008,inset=.18)
            plate('pouch_lid_'+suffix+str(i),octagon(x,z+.042,.062,.044),front,
                  'olive','pelvis',clearance=.071,thickness=.008,crown=.002)
            plate('pouch_tab_'+suffix+str(i),octagon(x,z+.008,.018,.040),front,
                  'olive','pelvis',clearance=.075,thickness=.005,crown=0)
        plate('hip_guard_'+suffix,
              [(sign*x,z) for x,z in [(.036,1.012),(.096,1.013),(.140,.962),
                                      (.096,.868),(.061,.890),(.020,.970)]],
              front,'olive','pelvis',clearance=.022,thickness=.014,crown=.003)

    for side, suffix in (('l','L'),('r','R')):
        upper = 'upperarm_'+side
        lower = 'lowerarm_'+side
        thigh = 'thigh_'+side
        calf = 'calf_'+side
        shoulder = limb_mapper(upper,.074,extra=.003)
        arm = limb_mapper(upper,.063)
        forearm = limb_mapper(lower,.052)
        leg = limb_mapper(thigh,.088)
        shin = limb_mapper(calf,.066)
        # Compact rounded laminae follow the deltoid, keeping a visible seam
        # between layers without the original tall, pointed fan silhouette.
        for i in range(3):
            t = -.035 + i*.135
            width=1.34-i*.08
            outline = [(-width,t+.035),(-width*.73,t-.030),(-.34,t-.060),
                       (.34,t-.060),(width*.76,t-.025),(width,t+.045),
                       (width*.93,t+.165),(.54,t+.198),(-.54,t+.198),(-width*.93,t+.155)]
            plate('pauldron_'+suffix+str(i),outline,shoulder,'olive',upper,
                  clearance=.010-i*.002,thickness=.007,crown=.002,inset=.07)
            ribbon('pauldron_seam_'+suffix+str(i),[(-.85,t+.128),(.80,t+.128)],
                   shoulder,.010,'dark',upper,.018-i*.002)
            for j,u in enumerate((-.92,.90)):
                fastener('pauldron_fixing_'+suffix+str(i)+'_'+str(j),u,t+.085,
                         shoulder,upper,.019-i*.002,radius=.0025)
        ribbon('pauldron_cyan_'+suffix,[(-.66,.235),(.34,.240)],shoulder,.019,
               'cyan',upper,.024)
        plate('bicep_outer_'+suffix,[(-1.18,.39),(-.58,.35),(.64,.40),(1.0,.55),
                                   (.74,.84),(-.64,.87),(-1.07,.74)],
              arm,'olive',upper,clearance=.018,thickness=.010,crown=.004)
        # Alternating shallow ribs read as flexible textile at the elbow and
        # underarm. They are short open wraps, not tubes that erase anatomy.
        for i in range(7):
            t=.40+i*.074
            plate('underarm_rib_'+suffix+str(i),
                  [(1.90,t),(3.30,t),(3.30,t+.026),(1.90,t+.026)],arm,'dark',upper,
                  clearance=.005,thickness=.003,crown=0,inset=.02)
        plate('elbow_guard_'+suffix,[(-1.13,-.07),(-.40,-.14),(.63,-.11),
                                    (1.16,.04),(.56,.16),(-.67,.15)],
              forearm,'olive',lower,clearance=.023,thickness=.012,crown=.004)
        fore_outline=[(-1.12,.23),(-.50,.12),(.63,.17),(1.18,.31),
                      (.96,.90),(.60,.99),(-.61,.98),(-1.08,.82)]
        plate('vambrace_base_'+suffix,fore_outline,forearm,'dark',lower,
              clearance=.012,thickness=.011,crown=.001)
        plate('vambrace_shell_'+suffix,fore_outline,forearm,'olive',lower,
              clearance=.027,thickness=.013,crown=.005)
        plate('vambrace_raised_'+suffix,octagon(0,.57,.82,.55),forearm,'olive',lower,
              clearance=.046,thickness=.008,crown=.004)
        ribbon('wrist_light_'+suffix,[(-.62,.89),(.62,.89)],forearm,.029,
               'cyan',lower,.052)
        for t in (.24,.89):
            wrap_band('forearm_strap_'+suffix+str(t),1.18,4.96,t,.035,
                      forearm,'dark',lower,clearance=.013,thickness=.006)
        # Hand dorsal plates stop before the first finger joints: the imported
        # anatomical fingers and skin remain visible and fully movable.
        hand_name='hand_'+side
        if hand_name in rig.data.bones:
            ha,hb=bone(hand_name)
            axis=(hb-ha).normalized()
            across=Vector((1,0,0))
            across=(across-axis*across.dot(axis)).normalized()
            normal=across.cross(axis).normalized()
            if normal.y>0:normal=-normal
            center=ha+axis*(.040*scale)
            hit,_,_,distance=surface.ray_cast(center,normal,.040*scale)
            dorsal_depth=max(.009*scale,min(distance,.025*scale)) if hit is not None else .015*scale

            def hand_map(u,v,d):
                p=ha+axis*(v*scale)+across*(u*scale)
                curvature=.002*scale*max(0.,1.-(u/.033)**2)
                return p+normal*(dorsal_depth+d+curvature)
            plate('dorsal_glove_'+suffix,octagon(0,.041,.061,.072),hand_map,
                  'dark',hand_name,clearance=.002,thickness=.005,crown=.002)
            plate('dorsal_knuckle_'+suffix,octagon(0,.037,.049,.046),hand_map,
                  'olive',hand_name,clearance=.008,thickness=.004,crown=.001)

        # Thigh armour leaves an inside compression strip and the hip crease
        # visible, with two real straps crossing its segmented front shell.
        thigh_shape=[(-1.05,.14),(-.53,.075),(.63,.11),(1.13,.25),
                     (.90,.80),(.28,.91),(-.66,.84),(-1.02,.67)]
        plate('thigh_shell_'+suffix,thigh_shape,leg,'olive',thigh,
              clearance=.018,thickness=.012,crown=.006)
        plate('thigh_lateral_'+suffix,
              [(1.03,.21),(1.78,.18),(2.15,.31),(1.96,.78),(1.12,.85)],
              leg,'olive',thigh,clearance=.018,thickness=.010,crown=.003)
        for i,t in enumerate((.37,.70)):
            wrap_band('thigh_strap_'+suffix+str(i),-1.20,1.98,t,.045,
                      leg,'dark',thigh,clearance=.039,thickness=.008)
            plate('thigh_buckle_'+suffix+str(i),octagon(.58,t,.36,.075),leg,
                  'olive',thigh,clearance=.052,thickness=.006,crown=.001)
        ribbon('thigh_cyan_'+suffix,[(-.77,.18),(-.67,.32)],leg,.025,
               'cyan',thigh,.035)
        knee_shape=[(-1.02,-.08),(-.53,-.145),(.57,-.13),(1.0,-.035),
                    (.90,.18),(.33,.27),(-.49,.23),(-.97,.13)]
        plate('knee_gasket_'+suffix,knee_shape,shin,'dark',calf,
              clearance=.017,thickness=.012,crown=.003)
        plate('knee_cup_'+suffix,knee_shape,shin,'olive',calf,
              clearance=.032,thickness=.013,crown=.011)
        plate('knee_ridge_'+suffix,octagon(0,.04,.66,.24),shin,'olive',calf,
              clearance=.057,thickness=.008,crown=.003)
        greave=[(-1.20,.35),(-.70,.23),(.30,.25),(1.11,.40),
                (.90,.98),(.34,1.02),(-.64,.98),(-1.09,.80)]
        plate('shin_gasket_'+suffix,greave,shin,'dark',calf,
              clearance=.012,thickness=.010,crown=.001)
        plate('shin_shell_'+suffix,greave,shin,'olive',calf,
              clearance=.025,thickness=.012,crown=.006)
        plate('shin_spine_'+suffix,
              [(-.38,.39),(-.02,.31),(.44,.44),(.35,.96),(-.31,.96)],
              shin,'olive',calf,clearance=.046,thickness=.009,crown=.004)
        for i,t in enumerate((.44,.90)):
            wrap_band('calf_strap_'+suffix+str(i),1.18,5.06,t,.035,
                      shin,'dark',calf,clearance=.015,thickness=.008)
        ribbon('shin_cyan_'+suffix,[(-.72,.81),(-.67,.92)],shin,.025,
               'cyan',calf,.048)

        # Boot is a shaped last with flattened sole, broad toe and rising heel.
        # Its surface is constructed around the actual foot/ball endpoints.
        fa,fb=bone('foot_'+side)
        toe=bone('ball_'+side)[1] if 'ball_'+side in rig.data.bones else fb+Vector((0,-.075,0))*scale
        foot_length=max(.22*scale,math.hypot(toe.x-fa.x,toe.y-fa.y)+.060*scale)
        fwd=Vector((toe.x-fa.x,toe.y-fa.y,0)).normalized()
        lateral=Vector((-fwd.y,fwd.x,0))
        origin=Vector((fa.x,fa.y,.026*scale))
        width=.061*scale
        outline=[(-.74,-.23),(.74,-.23),(1.,.04),(1.,.67),(.80,1.),
                 (.37,1.06),(-.56,1.04),(-.92,.83),(-1.,.14)]
        verts=[]; faces=[]; wear=[]
        for z,shrink in ((.007,.98),(.035,1.),(.066,.97)):
            for u,v in outline:
                p=origin+lateral*(u*width*shrink)+fwd*(v*foot_length*.88)
                p.z=z*scale
                verts.append(p);wear.append(.05)
        n=len(outline)
        for k in range(2):
            for j in range(n):faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
        faces.extend([tuple(reversed(range(n))),tuple(range(2*n,3*n))])
        mesh('boot_sole_'+suffix,verts,faces,'dark','foot_'+side,wear)

        def boot_map(u,v,d):
            p=origin+lateral*(u*width)+fwd*(v*foot_length*.88)
            top=.085 + .040*(1-max(0,min(1,v)))
            p.z=(top-.024*abs(u))*scale+d
            return p
        plate('boot_upper_'+suffix,outline,boot_map,'olive','foot_'+side,
              clearance=.003,thickness=.011,crown=.006,inset=.08)
        for i,v in enumerate((.24,.47,.72)):
            plate('boot_instep_lame_'+suffix+str(i),
                  [(-.86,v-.075),(.86,v-.075),(.85,v+.060),(.52,v+.095),
                   (-.58,v+.09),(-.88,v+.04)],boot_map,'olive','foot_'+side,
                  clearance=.020,thickness=.008,crown=.003)
        # Sole notches are deliberate silhouette chunks, not texture lines.
        for sign in (-1,1):
            for i in range(5):
                v=.07+i*.18

                def tread_map(u,w,d):
                    p=origin+lateral*(sign*(width+.004*scale))+fwd*(u*foot_length*.88)
                    p.z=w*scale
                    return p+lateral*(sign*d)
                plate('sole_lug_'+suffix+str(sign)+'_'+str(i),
                      octagon(v,.031,.11,.038),tread_map,'dark','foot_'+side,
                      clearance=0,thickness=.003,crown=0,inset=.07)

    bpy.context.view_layer.update()
    diagnostics = armour_diagnostics(objects)
    diagnostics['surfaceFit'] = fit_counts
    diagnostics['bodyHeight'] = round(height, 6)
    if diagnostics['triangles'] > ARMOUR_LIMIT:
        raise RuntimeError('Armour exceeds authored triangle budget: ' + json.dumps(diagnostics))
    if diagnostics['materialCount'] != 3:
        raise RuntimeError('Armour must share exactly three material families')
    # Diagnostics live on the armour only, never on the supplied base or rig.
    if objects:
        objects[0]['armourDiagnostics'] = json.dumps(diagnostics)
    print(json.dumps({'colonistArmour': diagnostics}))
    return objects
