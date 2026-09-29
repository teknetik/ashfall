"""Shared builders for the Basic General counter/stock dressing (29 Sep 2026).

Authoring frame ("A-space", identical to the v1-v3 building source): +X = screen-right when viewed from the front,
+Y = up, +Z = towards the avenue (front). Metres. Origin = building pivot (Unity 8, 0.5, 15.1); Y=0 is the porch top.
Parts are built with A-space vertex coordinates; `Part.finalise()` bakes the A-space -> Blender Z-up rotation so the
exported objects are ordinary Blender data that line up with basic-general-source-v3.blend.

glTF/GLB is Y-up with the same handedness as A-space, so a GLB exported from these objects is in A-space; glTFast's
X flip then gives Unity local = (-Ax, Ay, Az), the project convention documented in docs/building-repairs-20260909.md.
"""
import bpy, bmesh, math, random
from pathlib import Path
from mathutils import Vector, Matrix, Euler

ROOT = Path('/home/teknetik/code/ao2')
OUT = ROOT / 'art/quality_20260929/basic-general-counter'
TEX = OUT / 'textures'
A2B = Matrix.Rotation(math.radians(90), 4, 'X')      # A-space (Y-up) -> Blender (Z-up):  B = (Ax, -Az, Ay)

MATS = {}       # slot -> bpy material
RECORDS = {}    # slot -> json record for the Unity hand-off


def _img(name, data):
    im = bpy.data.images.load(str(TEX / name), check_existing=True)
    im.colorspace_settings.name = 'Non-Color' if data else 'sRGB'
    return im


def material(slot, maps, tile, tint=(1, 1, 1), unique_uv=False, note='', base=None, emissive=None):
    """PBR material with the project's Unity packing: BaseColor sRGB, Normal OpenGL, MetalSmooth (R metal, A smoothness).
    `base` overrides the BaseColor file (colour variants share Normal + MetalSmooth with their parent)."""
    if slot in MATS:
        return MATS[slot]
    m = bpy.data.materials.new('BGC_' + slot)
    m.use_nodes = True
    m['ward_slot'] = slot
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    p = n['Principled BSDF']
    uv = n.new('ShaderNodeUVMap'); uv.uv_map = 'UV0'

    def tex(file, data):
        t = n.new('ShaderNodeTexImage'); t.image = _img(file, data); t.interpolation = 'Linear'; t.extension = 'REPEAT'
        l.new(uv.outputs['UV'], t.inputs['Vector'])
        return t
    b = tex((base or (maps + '_BaseColor.png')), False)
    if tuple(tint) == (1, 1, 1):                      # direct link keeps the material exportable to glTF
        l.new(b.outputs['Color'], p.inputs['Base Color'])
    else:
        mix = n.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        l.new(b.outputs['Color'], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        l.new(mix.outputs[2], p.inputs['Base Color'])
    nm = n.new('ShaderNodeNormalMap'); nm.uv_map = 'UV0'; nm.inputs['Strength'].default_value = 1.0
    l.new(tex(maps + '_Normal.png', True).outputs['Color'], nm.inputs['Color']); l.new(nm.outputs['Normal'], p.inputs['Normal'])
    ms = tex(maps + '_MetalSmooth.png', True)
    sep = n.new('ShaderNodeSeparateColor'); l.new(ms.outputs['Color'], sep.inputs[0])
    l.new(sep.outputs['Red'], p.inputs['Metallic'])
    inv = n.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    l.new(ms.outputs['Alpha'], inv.inputs[1]); l.new(inv.outputs[0], p.inputs['Roughness'])
    m.diffuse_color = (*tint, 1)
    if emissive:
        p.inputs['Emission Color'].default_value = (*emissive[0], 1); p.inputs['Emission Strength'].default_value = emissive[1]
    MATS[slot] = m
    RECORDS[slot] = {'slot': slot, 'maps': maps, 'tileMetres': tile, 'tint': list(tint), 'uniqueLayoutUV': unique_uv, 'note': note,
                     'baseColor': (base or f'{maps}_BaseColor.png'), 'normal': f'{maps}_Normal.png', 'metalSmooth': f'{maps}_MetalSmooth.png',
                     'emission': ({'colour': list(emissive[0]), 'strength': emissive[1]} if emissive else None)}
    return m


class Part:
    """One exported mesh with several material slots. All geometry in A-space."""

    def __init__(self, name, seed=1):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new('UV0')
        self.gen = self.bm.faces.layers.int.new('gen')
        self.stack = []
        self.slots = []
        self.rng = random.Random(seed)
        self.off = {}

    # ---- bookkeeping ---------------------------------------------------
    def slot(self, mat):
        if mat not in self.slots:
            self.slots.append(mat)
        return self.slots.index(mat)

    def _offset(self, mat):
        if mat not in self.off:
            self.off[mat] = (self.rng.random() * 7, self.rng.random() * 7)
        return self.off[mat]

    def _new(self):
        out = []
        for f in self.bm.faces:
            if f[self.gen] == 0:
                f[self.gen] = 1
                out.append(f)
        for lst in self.stack:
            lst.extend(out)
        return out

    def begin(self):
        """Start collecting the faces of a prop so it can be placed with end(T). Calls may nest."""
        self.stack.append([])

    def end(self, T):
        faces = [f for f in self.stack.pop() if f.is_valid]
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.transform(self.bm, matrix=T, verts=verts)

    def _tag(self, faces, mat):
        i = self.slot(mat)
        for f in faces:
            f.material_index = i

    # ---- UV helpers ----------------------------------------------------
    def uv_box(self, faces, mat, tile):
        """Metric box projection: 1 UV unit = `tile` metres, dominant-axis projection."""
        ox, oy = self._offset(mat)
        for f in faces:
            nrm = f.normal
            ax = max(range(3), key=lambda a: abs(nrm[a]))
            for lp in f.loops:
                p = lp.vert.co
                if ax == 0:
                    a, b = p.z * (1 if nrm.x > 0 else -1), p.y
                elif ax == 1:
                    a, b = p.x, p.z * (1 if nrm.y > 0 else -1)
                else:
                    a, b = p.x * (1 if nrm.z > 0 else -1), p.y
                lp[self.uv].uv = (a / tile + ox, b / tile + oy)

    def uv_fn(self, faces, fn):
        for f in faces:
            for lp in f.loops:
                lp[self.uv].uv = fn(lp.vert.co, f.normal)

    # ---- primitives ----------------------------------------------------
    def box(self, c, size, mat, tile, bevel=.004, seg=2, rot=None, uvfn=None, over=None):
        """Bevelled box centred at c; rot = Euler xyz radians about its centre. size is (x, y, z) extent.
        over = [(axis_index, sign, mat2, tile2, uvfn2)]: faces whose dominant normal matches get another material/UV."""
        bm = self.bm
        M = Matrix.Translation(c) @ (Euler(rot).to_matrix().to_4x4() if rot else Matrix.Identity(4)) @ \
            Matrix.Diagonal((size[0], size[1], size[2], 1))
        res = bmesh.ops.create_cube(bm, size=1.0, matrix=M)
        if bevel:
            edges = list({e for v in res['verts'] for e in v.link_edges})
            bmesh.ops.bevel(bm, geom=edges, offset=min(bevel, min(size) * .45), offset_type='OFFSET', segments=seg, profile=.5, affect='EDGES')
        faces = self._new()
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        rest = list(faces)
        for ax, sg, m2, t2, fn2 in (over or []):
            sel = [f for f in rest if f.normal[ax] * sg > .5]
            for f in sel:
                rest.remove(f)
            if fn2:
                self.uv_fn(sel, fn2)
            else:
                self.uv_box(sel, m2, t2)
            self._tag(sel, m2)
        if uvfn:
            self.uv_fn(rest, uvfn)
        else:
            self.uv_box(rest, mat, tile)
        self._tag(rest, mat)
        return faces

    def prism(self, prof, axis, a0, a1, mat, tile, uvfn=None):
        """Extrude a 2D profile along an axis. axis 'x': prof=(z,y); 'y': prof=(x,z); 'z': prof=(x,y)."""
        bm = self.bm

        def at(a, p, q):
            return {'x': (a, q, p), 'y': (p, a, q), 'z': (p, q, a)}[axis]
        r0 = [bm.verts.new(at(a0, p, q)) for p, q in prof]
        r1 = [bm.verts.new(at(a1, p, q)) for p, q in prof]
        n = len(prof)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
        bm.faces.new(r0[::-1]); bm.faces.new(r1)
        faces = self._new()
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        if uvfn:
            self.uv_fn(faces, uvfn)
        else:
            self.uv_box(faces, mat, tile)
        self._tag(faces, mat)
        return faces

    def lathe(self, profile, mat, tile, pos=(0, 0, 0), axis=(0, 1, 0), segs=40, scale=(1, 1), rot_about=math.pi / 2, warp=None,
              caps=(True, True), swap_uv=False, wrap=None):
        """Surface of revolution. profile = [(radius, height), ...] bottom->top; radius 0 makes an apex (closed end).
        scale=(sx, sz) squashes the section across the two radial directions (baked into the geometry).
        warp(angle, height)->radius multiplier gives hand-made irregularity / dents / knurling.
        UV0 is isotropic: u = angle * ring circumference / tile (seam at angle=rot_about; the default puts it at the
        back, -Z, for Y-axis lathes), v = arc length / tile. swap_uv exchanges the axes (strands running round)."""
        bm = self.bm
        axis = Vector(axis).normalized()
        ref = Vector((0, 0, 1)) if abs(axis.z) < .9 else Vector((1, 0, 0))
        e1 = axis.cross(ref).normalized(); e2 = axis.cross(e1).normalized()
        rings, circ = [], []
        for pr in profile:
            r, h = pr[0], pr[1]
            kz = pr[2] if len(pr) > 2 else scale[1] / scale[0]
            if r < 1e-6:
                rings.append([bm.verts.new(Vector(pos) + axis * h)]); circ.append(0.0)
            else:
                ring = []
                for i in range(segs):
                    a = 2 * math.pi * i / segs + rot_about
                    rr = r * (warp(a, h) if warp else 1.0)
                    ring.append(bm.verts.new(Vector(pos) + axis * h + e1 * (math.cos(a) * rr * scale[0]) + e2 * (math.sin(a) * rr * scale[0] * kz)))
                rings.append(ring); circ.append(2 * math.pi * r * scale[0] * (1 + kz) / 2)
        for ra, rb in zip(rings[:-1], rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                if len(ra) == 1 and len(rb) == 1:
                    continue
                if len(ra) == 1:
                    bm.faces.new((ra[0], rb[j], rb[i]))
                elif len(rb) == 1:
                    bm.faces.new((ra[i], ra[j], rb[0]))
                else:
                    bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
        for ring, first, keep in ((rings[0], True, caps[0]), (rings[-1], False, caps[1])):
            if len(ring) > 1 and keep:               # open end -> flat cap
                bm.faces.new(ring if first else ring[::-1])
        faces = self._new()
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        ox, oy = self._offset(mat)
        ox += self.rng.random() * 3; oy += self.rng.random() * 3      # every call gets its own texture window
        wraps = wrap if wrap else max(1, round(max(circ) / tile))     # ONE integer wrap count for the whole part -> seam tiles
        arc = [0.0]
        for (r0, h0, *_), (r1, h1, *_) in zip(profile[:-1], profile[1:]):
            arc.append(arc[-1] + math.hypot(r1 - r0, h1 - h0))
        info_v = {}
        for ri, ring in enumerate(rings):
            for i, v in enumerate(ring):
                info_v[v] = (i / segs, arc[ri] / tile, len(ring), circ[ri])
        for f in faces:
            if all(lp.vert in info_v for lp in f.loops) and len(f.loops) in (3, 4):
                info = [info_v[lp.vert] for lp in f.loops]
                fr = [i[0] for i in info]
                sizes = [i[2] for i in info]
                if 1 in sizes and len(set(sizes)) > 1:
                    real = [u for u, s in zip(fr, sizes) if s > 1]
                    m = sum(real) / len(real)
                    fr = [m if s == 1 else u for u, s in zip(fr, sizes)]
                if max(fr) - min(fr) > .5:
                    fr = [u + 1 if u < .5 else u for u in fr]
                cmean = max(i[3] for i in info)
                for lp, u, i in zip(f.loops, fr, info):
                    uu, vv = u * wraps + ox, i[1] + oy
                    lp[self.uv].uv = (vv, uu) if swap_uv else (uu, vv)
            else:                                    # flat caps: planar in metres
                for lp in f.loops:
                    d = lp.vert.co - Vector(pos)
                    lp[self.uv].uv = (d.dot(e1) / tile + ox, d.dot(e2) / tile + oy)
        self._tag(faces, mat)
        return faces

    def sweep(self, pts, section, ref, mat, tile, closed=False, caps=True, scale_fn=None):
        """Sweep a closed 2D `section` [(a, b), ...] along polyline `pts`.
        Frame at each point: t = tangent, a-axis = ref x t, b-axis = t x a. `ref` is a Vector or callable(point)->Vector
        (use the outward normal for straps that wrap something). scale_fn(t01)->section scale (tapers, bulges).
        UV0: u = section perimeter / tile, v = path length / tile (isotropic, metres)."""
        bm = self.bm
        P = [Vector(p) for p in pts]
        dedup = [P[0]]
        for q in P[1:]:
            if (q - dedup[-1]).length > 2e-4:        # coincident/near-coincident samples make zero-area, zero-UV quads
                dedup.append(q)
        P = dedup
        N = len(P)
        tang = []
        for i in range(N):
            a = P[(i - 1) % N] if closed else P[max(i - 1, 0)]
            b = P[(i + 1) % N] if closed else P[min(i + 1, N - 1)]
            tang.append((b - a).normalized())
        rings = []
        for i in range(N):
            rv = Vector(ref(P[i])) if callable(ref) else Vector(ref)
            av = rv.cross(tang[i])
            if av.length < 1e-5:
                av = Vector((1, 0, 0)).cross(tang[i]) if abs(tang[i].x) < .9 else Vector((0, 1, 0)).cross(tang[i])
            av.normalize()
            bv = tang[i].cross(av).normalized()
            s = scale_fn(i / max(N - 1, 1)) if scale_fn else 1.0
            rings.append([bm.verts.new(P[i] + av * (a_ * s) + bv * (b_ * s)) for a_, b_ in section])
        n = len(section)
        for i in (range(N) if closed else range(N - 1)):
            ra, rb = rings[i], rings[(i + 1) % N]
            for k in range(n):
                k2 = (k + 1) % n
                bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
        if caps and not closed:
            bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
        faces = self._new()
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        ox, oy = self._offset(mat)
        per = [0.0]
        for k in range(n):
            a0, b0 = section[k]; a1, b1 = section[(k + 1) % n]
            per.append(per[-1] + math.hypot(a1 - a0, b1 - b0))
        acc = [0.0]
        for i in range(1, N):
            acc.append(acc[-1] + (P[i] - P[i - 1]).length)
        lookup = {}
        # closed sweeps: rescale so the section perimeter and the path length are whole numbers of texture tiles (seamless wrap)
        su = 1.0 / tile
        sv = 1.0 / tile
        total = acc[-1] + ((P[0] - P[-1]).length if closed else 0.0)
        if closed:
            sv = max(1, round(total / tile)) / total
        su = max(1, round(per[-1] / tile)) / per[-1] if per[-1] / tile > .5 else su
        for i in range(N):
            for k, v in enumerate(rings[i]):
                lookup[v] = (per[k], acc[i])
        for f in faces:
            if len(f.loops) == 4 and all(lp.vert in lookup for lp in f.loops) and len({round(lookup[lp.vert][1], 7) for lp in f.loops}) > 1:
                ks = [lookup[lp.vert] for lp in f.loops]
                us = [k[0] for k in ks]
                if max(us) - min(us) > per[-1] * .5:
                    us = [u + per[-1] if u < per[-1] * .5 else u for u in us]
                vs = [k[1] for k in ks]
                if closed and max(vs) - min(vs) > acc[-1] * .5:
                    vs = [v + total if v < acc[-1] * .5 else v for v in vs]
                for lp, u, v in zip(f.loops, us, vs):
                    lp[self.uv].uv = (u * su + ox, v * sv + oy)
            else:                                    # end caps: metric box projection (a planar x/z map collapses on Z-running wires)
                self.uv_box([f], mat, tile)
        self._tag(faces, mat)
        return faces

    def tube(self, pts, radius, mat, tile, sides=6, closed=False, caps=True):
        """Round wire/rope: circular sweep. radius: float or callable(t 0..1)."""
        sec = [(math.cos(2 * math.pi * k / sides), math.sin(2 * math.pi * k / sides)) for k in range(sides)]
        if callable(radius):
            return self.sweep(pts, sec, (0.3, 1.0, 0.2), mat, tile, closed, caps, scale_fn=radius)
        sec = [(a * radius, b * radius) for a, b in sec]
        return self.sweep(pts, sec, (0.3, 1.0, 0.2), mat, tile, closed, caps)

    def grid(self, nx, nz, height_fn, xr, zr, mat, tile, base=0.0004):
        """Heightfield patch over [xr]x[zr]; settled-dust drifts (height_fn >= 0, ~0 on the border)."""
        bm = self.bm
        vs = []
        for j in range(nz + 1):
            row = []
            for i in range(nx + 1):
                x = xr[0] + (xr[1] - xr[0]) * i / nx; z = zr[0] + (zr[1] - zr[0]) * j / nz
                row.append(bm.verts.new((x, base + max(0.0, height_fn(x, z)), z)))
            vs.append(row)
        for j in range(nz):
            for i in range(nx):
                bm.faces.new((vs[j][i], vs[j + 1][i], vs[j + 1][i + 1], vs[j][i + 1]))
        faces = self._new()
        bmesh.ops.recalc_face_normals(bm, faces=faces)
        for f in faces:
            if f.normal.y < 0:
                f.normal_flip()
        self.uv_box(faces, mat, tile)
        self._tag(faces, mat)
        return faces

    def transform_new(self, M, faces):
        verts = list({v for f in faces for v in f.verts})
        bmesh.ops.transform(self.bm, matrix=M, verts=verts)

    # ---- output --------------------------------------------------------
    def finalise(self, collection, origin=(0, 0, 0), sharp_deg=50):
        """Create the Blender object with its origin at `origin` (A-space), A-space -> Blender Z-up baked, split normals set."""
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp_deg):
                e.smooth = False
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(self.name)
        bm.faces.layers.int.remove(self.gen)
        bm.to_mesh(me)
        for s in self.slots:
            me.materials.append(MATS[s])
        me.transform(Matrix.Translation(-Vector(origin)))
        me.transform(A2B)
        o = bpy.data.objects.new(self.name, me)
        collection.objects.link(o)
        o.location = A2B @ Vector(origin)
        bpy.context.view_layer.objects.active = o
        for ob in bpy.context.view_layer.objects:
            ob.select_set(False)
        o.select_set(True)
        md = o.modifiers.new('Weighted planar normals', 'WEIGHTED_NORMAL'); md.keep_sharp = True; md.weight = 50
        bpy.ops.object.modifier_apply(modifier=md.name)
        o['ward_part'] = self.name
        o['pivotAuthoring'] = list(origin)
        bm.free()
        return o


def stats(o):
    """Triangle count and A-space bounds/size of an object at its current transform."""
    me = o.data
    me.calc_loop_triangles()
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xs = [b.x for b in bb]; ys = [b.y for b in bb]; zs = [b.z for b in bb]
    return {'tris': len(me.loop_triangles), 'verts': len(me.vertices),
            'boundsAmin': [round(min(xs), 4), round(min(zs), 4), round(-max(ys), 4)],
            'boundsAmax': [round(max(xs), 4), round(max(zs), 4), round(-min(ys), 4)],
            'sizeA': [round(max(xs) - min(xs), 4), round(max(zs) - min(zs), 4), round(max(ys) - min(ys), 4)]}
