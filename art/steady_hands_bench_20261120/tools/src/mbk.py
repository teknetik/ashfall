# mbk.py: what the tools and fixtures families share, on top of the programme kit (../../kit, by model-pistol).
# model-bench, Steady Hands bench programme, 20 November 2026.
#
# The kit carries one rig and one atlas per family. These two families are sets of separate objects, so this adds:
#   - BenchFamily: several small rigs per family (one per object with a mechanism, parented to that object so the
#     object is its own prefab), custom rigs (the skinned tool roll), and several texture sets per family, one of them
#     laid out by hand (the mats);
#   - building in an object's own frame and placing it on the bench from fixtures/layout/layout.json;
#   - helper empties given in the object's own frame, and seat marks (a mark that carries a whole pose);
#   - material layers spliced into a kit material (image masks, knurl about any axis, plain-weave cloth, stripes).
# Nothing in the kit is edited.
import bpy, bmesh, os, sys, json, math, time
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.abspath(os.path.join(HERE, '..', '..'))
KIT = os.path.join(PROG, 'kit')
if KIT not in sys.path:
    sys.path.insert(0, KIT)
from family import Family, G, MT, CT, RG, BK      # noqa: E402
import am_parts as AP                              # noqa: E402

MM = 0.001
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
O = Vector((0, 0, 0))
LAYOUT = json.load(open(os.path.join(PROG, 'fixtures', 'layout', 'layout.json')))


def R3(axis, deg):
    return Matrix.Rotation(math.radians(deg), 3, axis)


def R4(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def T(v):
    return Matrix.Translation(Vector(v))


# ====================================================================== placing
def bench_pose(key, dz=0.0, yaw=None):
    """World (bench frame) matrix of a layout item: its position and yaw about Z."""
    it = LAYOUT['items'][key]
    p = Vector(it['pos']) + Vector((0, 0, dz))
    return T(p) @ R4('Z', it.get('yaw', 0) if yaw is None else yaw)


def put(o, M):
    """Give an object built about the origin (in its own frame) its place. The mesh stays in the object's frame, so
    object-space materials stay put."""
    o.matrix_world = Matrix(M)
    bpy.context.view_layer.update()
    return o


def xform(o, M):
    """Move the MESH inside its object (object frame unchanged). For the rest tilt of a tool."""
    o.data.transform(Matrix(M)); o.data.update()
    return o


def rest_tilt(objs, about=None):
    """Tools are modelled along +Y on the axis z = 0. Lying on a bench a tool with a fat handle tilts. Returns the 4x4
    that turns the pieces about X and lifts them so that they rest on z = 0 on the lower hull under their middle."""
    pts = []
    for o in objs:
        pts += [(o.matrix_world @ v.co) for v in o.data.vertices]
    ys = np.array([p.y for p in pts]); zs = np.array([p.z for p in pts])
    # lower hull of (y, z)
    order = np.argsort(ys)
    hull = []
    for i in order:
        p = (ys[i], zs[i])
        while len(hull) >= 2:
            (y1, z1), (y2, z2) = hull[-2], hull[-1]
            if (y2 - y1) * (p[1] - z1) - (z2 - z1) * (p[0] - y1) <= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    cy = float(about) if about is not None else float((ys.min() + ys.max()) / 2)
    seg = None
    for a, b in zip(hull, hull[1:]):
        if a[0] <= cy <= b[0] and b[0] - a[0] > 1e-6:
            seg = (a, b); break
    if seg is None:
        return T((0, 0, -float(zs.min())))
    (y1, z1), (y2, z2) = seg
    ang = math.atan2(z2 - z1, y2 - y1)
    Rm = Matrix.Rotation(-ang, 4, 'X')
    p1 = Rm @ Vector((0, y1, z1))
    return T((0, 0, -p1.z)) @ Rm


# ====================================================================== helpers given in the object's frame
def W(o, p):
    return o.matrix_world @ Vector(p)


def Wd(o, d):
    return (o.matrix_world.to_3x3() @ Vector(d)).normalized()


def tip(o, p, d):
    return CT.tip(o, W(o, p), Wd(o, d))


def grab(o, p):
    return CT.grab(o, W(o, p))


def mark(o, mid, p, n=None):
    return CT.mark(o, mid, W(o, p), Wd(o, n) if n is not None else None)


def seat(o, sid, M_local=None, p=None, yaw=0.0, pose=False, accepts=()):
    """'<node>__mark_seat_<id>': where another part rests on this one (SEAM.md section 2). pose=True: a full pose, the
    resting part's node takes the mark's world transform (kit contract.seat_pose, flagged "pose": true in parts.json,
    with the ids it accepts). Otherwise a point: the bench takes the position and keeps its own orientation."""
    if M_local is None:
        M_local = T(p) @ R4('Z', yaw)
    Mw = o.matrix_world @ Matrix(M_local)
    if pose:
        return CT.seat_pose(o, sid, Mw, accepts)
    return CT._empty('%s__mark_seat_%s' % (o.name, sid), Mw, 'ARROWS', 0.01)


def zone(o, zid, centre, half, rot=None):
    Rw = o.matrix_world.to_3x3() @ (Matrix(rot).to_3x3() if rot is not None else Matrix.Identity(3))
    return CT.zone(o, zid, W(o, centre), half, Rw)


def clear_local(o, offset=(0, 0, 0), rot=None):
    """'<node>__clear' at an offset given in the object's own frame."""
    return CT.clear(o, offset=o.matrix_world.to_3x3() @ Vector(offset), rot=rot)


# ====================================================================== geometry
def turned(name, prof, segs=20, mat=None, axis=Y, origin=O, ref=None, phase=0.0):
    """Lathe a profile [(s, r)] along `axis` from `origin` (ends at r = 0 close the solid)."""
    ref = ref or (Z if abs(Vector(axis).normalized().z) < 0.9 else X)
    return G.lathe(name, [(list(prof), False)], segs, origin, axis, ref, mat, phase=phase)


def ring_prof(name, prof, segs=20, mat=None, axis=Y, origin=O, ref=None):
    """Lathe a CLOSED profile (a ring, a bush, a bowl wall)."""
    ref = ref or (Z if abs(Vector(axis).normalized().z) < 0.9 else X)
    return G.lathe(name, [(list(prof), True)], segs, origin, axis, ref, mat)


def box(name, lo, hi, mat=None, bevel=0.0, segs=1):
    lo, hi = Vector(lo), Vector(hi)
    o = G.box(name, (lo + hi) / 2, hi - lo, None, mat)
    if bevel > 0:
        G.bevel(o, bevel, segs)
    return o


def extrude_x(name, poly_yz, x0, x1, mat=None, bevel=0.0, segs=1):
    """Extrude a (y, z) outline along X: side profiles of castings."""
    o = G.prism(name, poly_yz, x1 - x0, (x0, 0, 0), Y, Z, X, mat, w0=0.0)
    if bevel > 0:
        G.bevel(o, bevel, segs)
    return o


def extrude_z(name, poly_xy, z0, z1, mat=None, bevel=0.0, segs=1):
    o = G.prism(name, poly_xy, z1 - z0, (0, 0, z0), X, Y, Z, mat, w0=0.0)
    if bevel > 0:
        G.bevel(o, bevel, segs)
    return o


def extrude_y(name, poly_xz, y0, y1, mat=None, bevel=0.0, segs=1):
    o = G.prism(name, poly_xz, y1 - y0, (0, y0, 0), X, Z, -Y, mat, w0=-(y1 - y0))
    if bevel > 0:
        G.bevel(o, bevel, segs)
    return o


def mats_of(o, mat):
    o.data.materials.clear(); o.data.materials.append(mat)
    return o


def join(name, objs):
    objs = [o for o in objs if o]
    if len(objs) == 1:
        objs[0].name = name; objs[0].data.name = name
        return objs[0]
    return G.join(name, objs)


def tri_count(objs):
    return sum(G.tris(o) for o in objs)


def jitter(o, amount, seed=0, scale=40.0):
    """Small smooth displacement so a hand-made thing is not ruler straight (amount in metres)."""
    from mathutils import noise
    def f(co):
        n = noise.noise_vector(co * scale + Vector((seed * 7.1, seed * 3.3, seed * 1.7)))
        return co + n * amount
    return G.displace(o, f)


# ====================================================================== material layers
class Tap:
    """Splice more layers into a kit material (mats.make): colour, roughness, metal and height each get a mix by a
    mask placed after everything make() did. Coordinates are the object's own (metres)."""
    def __init__(self, m):
        self.m = m; self.nt = m.node_tree; self.b = MT.NB(m)
        self.P = next(n for n in self.nt.nodes if n.bl_idname == 'ShaderNodeTexCoord').outputs['Object']
        self.bump = self.nt.nodes['BUMP']
        self._xyz = None

    def xyz(self):
        if self._xyz is None:
            s = self.b.n('ShaderNodeSeparateXYZ'); self.b.l(self.P, s.inputs[0])
            self._xyz = (s.outputs['X'], s.outputs['Y'], s.outputs['Z'])
        return self._xyz

    def _src(self, ch):
        r = self.nt.nodes['CH_' + ch]
        return r, r.inputs[0].links[0].from_socket

    def colour(self, mask, col):
        r, src = self._src('base')
        self.b.l(self.b.mixc(mask, src, MT.srgb(col) if isinstance(col, (tuple, list)) else col), r.inputs[0])

    def multiply(self, mask, col):
        r, src = self._src('base')
        mx = self.b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mx.clamp_factor = True
        self.b.l(mask, mx.inputs[0]) if not isinstance(mask, (int, float)) else setattr(mx.inputs[0], 'default_value', mask)
        self.b.l(src, mx.inputs[6]); mx.inputs[7].default_value = tuple(MT.srgb(col)) + (1,)
        self.b.l(mx.outputs[2], r.inputs[0])

    def rough(self, mask, v):
        r, src = self._src('rough')
        new = self.b.mixf(mask, src, v)
        self.b.l(new, r.inputs[0])
        self._orm(1, new)

    def metal(self, mask, v):
        r, src = self._src('metal')
        new = self.b.mixf(mask, src, v)
        self.b.l(new, r.inputs[0])
        self._orm(2, new)

    def _orm(self, i, sock):
        orm = self.nt.nodes['ORM']
        cl = self.b.math('MAXIMUM', self.b.math('MINIMUM', sock, 1.0), 0.0)
        self.b.l(cl, orm.inputs[i])

    def height(self, h, strength=1.0):
        """Add h * strength to the bump height (units of the bump distance, 0.15 mm by default)."""
        old = self.bump.inputs['Height'].links[0].from_socket
        self.b.l(self.b.math('ADD', old, self.b.math('MULTIPLY', h, strength)), self.bump.inputs['Height'])

    def layer(self, mask, col=None, rough=None, metal=None, height=None):
        if col is not None: self.colour(mask, col)
        if rough is not None: self.rough(mask, rough)
        if metal is not None: self.metal(mask, metal)
        if height is not None: self.height(mask, height)
        return self

    # ---- masks
    def image(self, path, origin, size, axes=(0, 1), interp='Cubic', extend='CLIP'):
        """An image laid in the object's frame: its lower-left corner at `origin` (object metres), `size` metres wide
        and high, along the two object axes `axes`. Returns the colour socket (use .r() for the red channel)."""
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = 'Non-Color'
        tx = self.b.n('ShaderNodeTexImage'); tx.image = img; tx.interpolation = interp; tx.extension = extend
        xyz = self.xyz()
        u = self.b.math('DIVIDE', self.b.math('SUBTRACT', xyz[axes[0]], origin[0]), size[0])
        v = self.b.math('DIVIDE', self.b.math('SUBTRACT', xyz[axes[1]], origin[1]), size[1])
        cv = self.b.n('ShaderNodeCombineXYZ'); self.b.l(u, cv.inputs[0]); self.b.l(v, cv.inputs[1])
        self.b.l(cv.outputs[0], tx.inputs['Vector'])
        return tx.outputs['Color']

    def chan(self, col, i=0):
        s = self.b.n('ShaderNodeSeparateColor'); self.b.l(col, s.inputs[0])
        return s.outputs[i]

    def facing(self, axis=2, lo=0.6, hi=0.95, sign=1.0):
        """1 where the surface normal points along +axis (object space)."""
        geo = next(n for n in self.nt.nodes if n.bl_idname == 'ShaderNodeNewGeometry')
        tr = self.b.n('ShaderNodeVectorTransform', vector_type='NORMAL', convert_from='WORLD', convert_to='OBJECT')
        self.b.l(geo.outputs['Normal'], tr.inputs[0])
        s = self.b.n('ShaderNodeSeparateXYZ'); self.b.l(tr.outputs[0], s.inputs[0])
        return self.b.ramp(self.b.math('MULTIPLY', s.outputs[axis], sign), lo, hi)

    def band(self, axis, lo, hi, soft=0.0005):
        """1 between lo and hi along an object axis (metres)."""
        c = self.xyz()[axis]
        return self.b.math('MULTIPLY', self.b.ramp(c, lo - soft, lo + soft), self.b.math('SUBTRACT', 1.0, self.b.ramp(c, hi - soft, hi + soft)))

    def noise(self, scale, detail=4, rough=0.55, stretch=None):
        P = self.P
        if stretch:
            mp = self.b.n('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
            self.b.l(P, mp.inputs['Vector']); P = mp.outputs['Vector']
        return self.b.noise(P, scale, detail, rough)

    def cyl(self, origin, axis, ref=None):
        """(angle, along, radius) about an axis given in the object's frame."""
        ax = Vector(axis).normalized()
        e1 = Vector(ref) if ref is not None else (Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0)))
        e1 = (e1 - ax * ax.dot(e1)).normalized(); e2 = ax.cross(e1)
        d = self.b.vmath('SUBTRACT', self.P, tuple(origin))
        al = self.b.vmath('DOT_PRODUCT', d, tuple(ax))
        a = self.b.vmath('DOT_PRODUCT', d, tuple(e1)); c = self.b.vmath('DOT_PRODUCT', d, tuple(e2))
        th = self.b.math('ARCTAN2', c, a)
        rr = self.b.math('SQRT', self.b.math('ADD', self.b.math('MULTIPLY', a, a), self.b.math('MULTIPLY', c, c)))
        return th, al, rr

    def knurl(self, origin, axis, n=28, pitch=0.0011, strength=1.0, lo=None, hi=None):
        """Diamond knurl about an axis: n diamonds round, `pitch` metres along. Optional band lo..hi along the axis."""
        th, al, rr = self.cyl(origin, axis)
        k2 = math.pi / pitch
        a1 = self.b.math('SINE', self.b.math('ADD', self.b.math('MULTIPLY', th, n / 2.0), self.b.math('MULTIPLY', al, k2)))
        a2 = self.b.math('SINE', self.b.math('SUBTRACT', self.b.math('MULTIPLY', th, n / 2.0), self.b.math('MULTIPLY', al, k2)))
        kn = self.b.math('MULTIPLY', self.b.math('ABSOLUTE', a1), self.b.math('ABSOLUTE', a2))
        if lo is not None:
            kn = self.b.math('MULTIPLY', kn, self.b.math('MULTIPLY', self.b.ramp(al, lo - 0.0002, lo + 0.0002),
                                                           self.b.math('SUBTRACT', 1.0, self.b.ramp(al, hi - 0.0002, hi + 0.0002))))
        self.height(kn, strength)
        return kn

    def wrap(self, origin, axis, pitch, lo, hi, col_seam=(0.10, 0.09, 0.08), strength=0.9, fray=0.0):
        """Tape wound round a handle between lo and hi along the axis: a saw-tooth step per turn and a dark seam.
        Returns the mask of the wrapped band."""
        th, al, rr = self.cyl(origin, axis)
        ph = self.b.math('FRACT', self.b.math('ADD', self.b.math('DIVIDE', al, pitch), self.b.math('DIVIDE', th, 2 * math.pi)))
        band = self.b.math('MULTIPLY', self.b.ramp(al, lo - 0.0004, lo + 0.0004), self.b.math('SUBTRACT', 1.0, self.b.ramp(al, hi - 0.0004, hi + 0.0004)))
        saw = self.b.math('MULTIPLY', self.b.ramp(ph, 0.0, 0.9), self.b.math('SUBTRACT', 1.0, self.b.ramp(ph, 0.93, 1.0)))
        self.height(self.b.math('MULTIPLY', saw, band), strength)
        seam = self.b.math('MULTIPLY', self.b.ramp(ph, 0.9, 0.985), band)
        self.multiply(self.b.math('MULTIPLY', seam, 0.75), col_seam)
        return band

    def weave(self, scale=1400.0, strength=0.5, axes=(0, 1), tone=0.12):
        """Plain weave lying in two object axes: warp and weft ridges, and a little thread-to-thread colour change."""
        xyz = self.xyz()
        a = self.b.math('SINE', self.b.math('MULTIPLY', xyz[axes[0]], scale * math.pi))
        c = self.b.math('SINE', self.b.math('MULTIPLY', xyz[axes[1]], scale * math.pi))
        over = self.b.math('MULTIPLY', a, c)                 # +: warp on top, -: weft on top
        ridge = self.b.math('ADD', self.b.math('MULTIPLY', self.b.math('ABSOLUTE', a), self.b.ramp(over, -0.2, 0.2)),
                            self.b.math('MULTIPLY', self.b.math('ABSOLUTE', c), self.b.math('SUBTRACT', 1.0, self.b.ramp(over, -0.2, 0.2))))
        self.height(ridge, strength)
        if tone:
            self.multiply(self.b.math('MULTIPLY', self.b.math('SUBTRACT', 1.0, ridge), tone * 4), (0.25, 0.25, 0.25))
        return ridge

    def stripes(self, axes=(0, 1), period=0.03, duty=0.5, angle_deg=45.0):
        xyz = self.xyz()
        ca, sa = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
        t = self.b.math('ADD', self.b.math('MULTIPLY', xyz[axes[0]], ca / period), self.b.math('MULTIPLY', xyz[axes[1]], sa / period))
        f = self.b.math('FRACT', t)
        return self.b.math('SUBTRACT', 1.0, self.b.ramp(f, duty - 0.02, duty + 0.02))


# ====================================================================== the family
class BenchFamily(Family):
    """Family with several rigs and several texture sets. Sets: self.set_of[object name] = 'a' | 'b' | ... (default
    'a'); self.manual_uv[set] = function(objs, size) -> uv stats, for a set laid out by hand."""
    def __init__(self, name, build_file, budget=None):
        super().__init__(name, build_file, budget=budget)
        argv = self.argv
        self.only = argv[argv.index('--only') + 1].split(',') if '--only' in argv else None
        self.reuse = '--reuse' in argv        # keep the textures of the last bake (after a change to empties or data only)
        self.size_of = {}            # set -> size override
        self.rigs = []
        self.custom_arms = []        # (armature, bake function, keep map) for rigs the kit does not make
        self.set_of = {}
        self.manual_uv = {}
        self.extra_params = []
        self.param_notes = {}        # param id -> extra fields for parts.json (pitch of a screw, what a value means)
        self.post_hierarchy = []     # callables run after the kit has parented parts and helpers
        self.uv_angle, self.uv_margin = 66.0, 4.0     # fewer, larger islands than the kit's 58 degrees / 5 px
        bpy.context.scene['sh_rigs'] = '{}'

    def load_bake(self, tag, size):
        """The texture set of the last bake, for --reuse. Stops if a file is missing or of another size."""
        tex = {'emit': None, 'dirty': None, 'stats': {'size': size, 'reused': True}}
        for k in ('color', 'normal', 'orm'):
            path = os.path.join(self.out, 'tex', '%s_%s_%s.png' % (self.name, tag, k))
            if not os.path.exists(path):
                raise SystemExit('--reuse: %s is missing; bake first' % path)
            im = bpy.data.images.load(path)
            if im.size[0] != size:
                raise SystemExit('--reuse: %s is %d px, the build asks for %d' % (path, im.size[0], size))
            im.colorspace_settings.name = 'sRGB' if k == 'color' else 'Non-Color'
            im.name = '%s_%s_%s' % (self.name, tag, k)
            tex[k] = im
        old = os.path.join(self.out, 'stats.json')
        if os.path.exists(old):
            tex['stats'].update({'spp': (json.load(open(old)).get('sets', {}).get(tag, {}).get('bake') or {}).get('spp')})
        return tex

    def want(self, key):
        return self.only is None or key in self.only

    def new_rig(self, short, parent):
        R = RG.Rig(self.name, parent=parent, name='%s_%s_rig' % (self.name, short))
        R._short = short
        return R

    def end_rig(self, R):
        """Call instead of R.finish(): finishes the rig, gives its root bone a unique name and records its joints."""
        R.finish()
        root = '%s_root' % R._short
        R.arm.data.bones['root'].name = root
        for j in R.joints:
            if j['parent_bone'] == 'root':
                j['parent_bone'] = root
        sc = bpy.context.scene
        params = json.loads(sc.get('sh_params', '[]'))
        for p in params:
            if p['node'] == R.name and p.get('parent_bone') == 'root':
                p['parent_bone'] = root
        sc['sh_params'] = json.dumps(params)
        d = json.loads(sc.get('sh_rigs', '{}')); d[R.name] = R.joints; sc['sh_rigs'] = json.dumps(d)
        self.rigs.append(R)
        return R

    def sets(self, P):
        out = {}
        for o in P:
            out.setdefault(self.set_of.get(o.name, 'a'), []).append(o)
        return dict(sorted(out.items()))

    def finish(self, glb=None):
        name = self.name
        sc = bpy.context.scene
        CT.build_hierarchy(name)
        for fn in self.post_hierarchy:
            fn()
        bad = CT.validate(name, self.budget)
        for b in bad:
            self.log('CONTRACT', b)
        P = list(self.parts().values())
        for o in P:
            G.triangulate(o)       # tangents need triangles, and the normal bake must see the same ones
        pn = {o.name for o in P}
        helpers = [e for e in bpy.data.objects if e.type == 'EMPTY' and e.get('sh_helper') and e.get('sh_of') in pn]
        arms = [r.arm for r in self.rigs] + [c[0] for c in self.custom_arms]
        self.log('parts', len(P), 'helpers', len(helpers), 'rigs', len(arms), 'tris', sum(CT.tris(o) for o in P))
        stats_extra = {'notes': self.notes, 'nobake': self.nobake, 'sets': {}}
        S = self.sets(P)
        tex = {}
        for tag, objs in S.items():
            size = self.size_of.get(tag, self.size)
            if tag in self.manual_uv:
                uv = self.manual_uv[tag](objs, size)
            else:
                uv = BK.unwrap(objs, size, self.uv_weights, angle=self.uv_angle, margin_px=self.uv_margin)
            stats_extra['sets'][tag] = {'size': size, 'objects': [o.name for o in objs], 'uv': uv}
            dens = [v['px_per_cm'] for v in uv['objects'].values() if v['uv_fraction'] > 0]
            self.log('set', tag, 'size', size, 'uv fill', uv['fill'], 'px/cm min %.1f max %.1f' % (min(dens), max(dens)))
        if not self.nobake:
            for tag, objs in S.items():
                size = self.size_of.get(tag, self.size)
                if self.reuse:
                    t = self.load_bake(tag, size)      # same geometry and UVs as the last bake: only the data changed
                else:
                    t = BK.bake(objs, '%s_%s' % (name, tag), self.out, size, self.spp)
                tex[tag] = t
                stats_extra['sets'][tag]['textures'] = {k: os.path.relpath(t[k].filepath_raw, self.out) for k in ('color', 'normal', 'orm', 'emit') if t.get(k)}
                stats_extra['sets'][tag]['bake'] = t['stats']
        keep = {}
        for arm, bake_fn, kp in self.custom_arms:      # no drivers on these: their clips are made now, so the saved
            bake_fn()                                  # .blend has them for review and check
            keep.update(kp)
        sc['sh_custom'] = json.dumps([{'rig': a.name, 'clips': sorted(kp)} for a, _, kp in self.custom_arms])
        blend = os.path.join(self.out, name + '.blend')
        bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True, copy=True)
        self.log('saved', blend)
        # ---- export
        if tex:
            stats_extra['runtime_material_tris'] = {}
            for tag, objs in S.items():
                stats_extra['runtime_material_tris'].update(BK.assign_runtime(objs, '%s_%s' % (name, tag), tex[tag]))
        for r in self.rigs:
            sc['sh_joints'] = json.dumps(r.joints)
            RG.bake_actions(r.arm)
            for j in r.joints:
                if not j['continuous']:
                    keep[j['param'] + '_param'] = [j['bone']]
        path = os.path.join(self.out, glb or name + '.glb')
        BK.export_glb(path, P + helpers + arms, animations=bool(keep))
        if keep:
            stats_extra['animation_channels'] = BK.filter_animations(path, keep)
        stats_extra['glb'] = BK.glb_summary(path)
        stats_extra['glb_bytes'] = os.path.getsize(path)
        pl = json.loads(sc.get('sh_params', '[]')) + self.extra_params
        for p in pl:
            p.update(self.param_notes.get(p['id'], {}))
        sc['sh_params'] = json.dumps(pl)
        extra = {'frame': LAYOUT['frame'], 'rigs': json.loads(sc.get('sh_rigs', '{}')) and sorted(json.loads(sc['sh_rigs']))}
        pj, st = CT.write(name, self.out, glb or name + '.glb', extra=extra, stats_extra=stats_extra, budget=self.budget)
        self.log('wrote parts.json (%d parts, %d params) and stats.json (%d tris)' % (len(pj['parts']), len(pj['params']), st['tris_total']))
        if bad:
            self.log('FAILED: %d contract problems' % len(bad))
            sys.exit(1)
        return pj, st


# ====================================================================== hand-laid UV sets
def uv_stats(objs, size):
    out = {}; fill = 0.0
    for o in objs:
        me = o.data; uv = me.uv_layers.active.data
        a3 = a2 = 0.0
        for p in me.polygons:
            pts = [uv[li].uv for li in p.loop_indices]
            aa = 0.0
            for i in range(1, len(pts) - 1):
                aa += abs((pts[i] - pts[0]).cross(pts[i + 1] - pts[0])) / 2
            if aa > 0:
                a3 += p.area; a2 += aa
        fill += a2
        out[o.name] = {'uv_fraction': round(a2, 4), 'px_per_cm': round(math.sqrt(a2 * size * size / max(a3 * 1e4, 1e-12)), 1)}
    return {'size': size, 'fill': round(fill, 3), 'objects': out}


def uv_rects(objs, size, rects, misc_rect, margin_px=4.0):
    """Hand layout. rects: list of (object, face test(poly, mesh) -> bool, (px x0, y0, x1, y1), (object-space u axis,
    v axis as index or (index, sign)), (lo_u, hi_u, lo_v, hi_v) metres mapped to the rectangle). Faces no test claims
    are smart-projected, packed and squeezed into misc_rect (px)."""
    for o in objs:
        if o.data.users > 1:
            o.data = o.data.copy()
        while len(o.data.uv_layers) > 0:
            o.data.uv_layers.remove(o.data.uv_layers[0])
        o.data.uv_layers.new(name='UVMap')
        o.data.polygons.foreach_set('select', [False] * len(o.data.polygons))
    claimed = {o.name: set() for o in objs}
    for (o, test, rect, axes, span) in rects:
        me = o.data; uv = me.uv_layers.active.data
        x0, y0, x1, y1 = [v / size for v in rect]
        (au, av) = axes
        su = 1.0; sv = 1.0
        if isinstance(au, tuple): au, su = au
        if isinstance(av, tuple): av, sv = av
        lu, hu, lv, hv = span
        for p in me.polygons:
            if p.index in claimed[o.name] or not test(p, me):
                continue
            claimed[o.name].add(p.index)
            for li, vi in zip(p.loop_indices, p.vertices):
                co = me.vertices[vi].co
                fu = (co[au] * su - lu) / (hu - lu); fv = (co[av] * sv - lv) / (hv - lv)
                uv[li].uv = (x0 + fu * (x1 - x0), y0 + fv * (y1 - y0))
    # the rest
    rest = []
    for o in objs:
        sel = [i not in claimed[o.name] for i in range(len(o.data.polygons))]
        o.data.polygons.foreach_set('select', sel)
        o.data.update()
        if any(sel):
            rest.append(o)
    if rest:
        bpy.ops.object.select_all(action='DESELECT')
        for o in rest:
            o.select_set(True)
        bpy.context.view_layer.objects.active = rest[0]
        keep = {}
        for o in rest:      # remember the hand-laid UVs: the operators below work on selected faces only, but be safe
            a = np.empty(len(o.data.loops) * 2, np.float32); o.data.uv_layers.active.data.foreach_get('uv', a); keep[o.name] = a
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.mesh_select_mode = (False, False, True)
        bpy.ops.uv.smart_project(angle_limit=math.radians(58), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.average_islands_scale()
        try:
            bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=margin_px / (misc_rect[2] - misc_rect[0]), shape_method='CONCAVE')
        except TypeError:
            bpy.ops.uv.pack_islands(rotate=True, margin=margin_px / (misc_rect[2] - misc_rect[0]))
        bpy.ops.object.mode_set(mode='OBJECT')
        mx0, my0, mx1, my1 = [v / size for v in misc_rect]
        # the packer fills the unit square; keep the islands' shape by using one scale and the smaller side
        s = min(mx1 - mx0, my1 - my0)
        for o in rest:
            me = o.data; uv = me.uv_layers.active.data
            a = np.empty(len(me.loops) * 2, np.float32); uv.foreach_get('uv', a)
            a = a.reshape(-1, 2); old = keep[o.name].reshape(-1, 2)
            mask = np.zeros(len(me.loops), bool)
            for p in me.polygons:
                if p.index not in claimed[o.name]:
                    mask[list(p.loop_indices)] = True
            a[mask, 0] = mx0 + a[mask, 0] * s; a[mask, 1] = my0 + a[mask, 1] * s
            a[~mask] = old[~mask]
            uv.foreach_set('uv', a.ravel())
            me.update()
    return uv_stats(objs, size)


# ====================================================================== rigs the kit does not make
def new_armature(name, bones):
    """bones: [(name, head, tail, parent or None, roll reference vector or None)] in the armature's own frame."""
    ad = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, ad)
    bpy.context.scene.collection.objects.link(arm)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = ad.edit_bones
    for (bn, head, tail, parent, ref) in bones:
        b = eb.new(bn)
        b.head = Vector(head); b.tail = Vector(tail)
        if ref is not None:
            b.align_roll(Vector(ref))
        if parent:
            b.parent = eb[parent]
        b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def bone_parent(o, arm, bone):
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
    bpy.context.view_layer.update()
    o.matrix_world = mw


def _nla(arm, act):
    for fc in RG._fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
    act.use_fake_user = True
    trk = arm.animation_data.nla_tracks.new(); trk.name = act.name
    st = trk.strips.new(act.name, 1, act)
    try:
        if st.action_slot is None and act.slots:
            st.action_slot = act.slots[0]
    except Exception:
        pass
    trk.mute = False
    arm.animation_data.action = None


def bake_pose_action(arm, name, bones, pose_fn, keys=25, loc=(), scale=()):
    """A clip one second long at 24 fps whose time is the parameter: pose_fn(v) poses the armature for v in 0..1 and the
    named bones are keyed. Leaves the bones at rest."""
    sc = bpy.context.scene
    sc.render.fps = RG.FPS
    sc.frame_start, sc.frame_end = 1, RG.FPS + 1
    if not arm.animation_data:
        arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    last = {}
    for i in range(keys):
        v = i / (keys - 1)
        fr = 1 + RG.FPS * v
        pose_fn(v)
        for bn in bones:
            pb = arm.pose.bones[bn]
            q = pb.rotation_quaternion.copy()
            if bn in last and last[bn].dot(q) < 0:
                q.negate(); pb.rotation_quaternion = q
            last[bn] = q
            pb.keyframe_insert('rotation_quaternion', frame=fr)
            if bn in loc:
                pb.keyframe_insert('location', frame=fr)
            if bn in scale:
                pb.keyframe_insert('scale', frame=fr)
    _nla(arm, act)
    for bn in bones:
        pb = arm.pose.bones[bn]
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    return act


def rest_all():
    """Every rig at rest: clips of the custom rigs muted (their bones were left at rest), driven rigs untouched."""
    for o in bpy.data.objects:
        if o.type == 'ARMATURE' and o.animation_data:
            for tr in o.animation_data.nla_tracks:
                tr.mute = True
    sc = bpy.context.scene
    sc.frame_set(1)
    bpy.context.view_layer.update()


def sample_clip(arm, clips, v):
    """Pose an armature from one clip (or several, at the same value) at parameter v, in a scene opened from the .blend."""
    if isinstance(clips, str):
        clips = [clips]
    for tr in arm.animation_data.nla_tracks:
        tr.mute = tr.name not in clips
    sc = bpy.context.scene
    f = 1 + RG.FPS * v
    sc.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()


def scale_rig(F, short, param, parent_obj, origin, axis, parts, s0=(1, 1, 1), s1=(0.6, 1, 0.6), note=None):
    """A squeeze: one bone on `axis` through `origin` (world) whose scale goes s0 -> s1 (bone space, Y along the axis)."""
    origin = Vector(origin); ax = Vector(axis).normalized()
    root = '%s_root' % short
    arm = new_armature('%s_%s_rig' % (F.name, short), [(root, origin, origin + ax * 0.01, None, None), (param, origin, origin + ax * 0.02, root, None)])
    for o in parts:
        bone_parent(o, arm, param)
        if 'sh' in o:
            d = json.loads(o['sh']); d['rides'] = param; o['sh'] = json.dumps(d)
    bpy.context.view_layer.update()
    mw = arm.matrix_world.copy()
    arm.parent = parent_obj; arm.matrix_parent_inverse = parent_obj.matrix_world.inverted(); arm.matrix_world = mw
    arm['anymachine'] = json.dumps({'joints': [{'param': param, 'type': 'scale', 'bone': param, 'min': list(s0), 'max': list(s1), 'unit': 'ratio',
                                                'continuous': False, 'axis': 'bone +Y'}]})

    def pose(v):
        pb = arm.pose.bones[param]; pb.rotation_mode = 'QUATERNION'
        pb.scale = [a + (b - a) * v for a, b in zip(s0, s1)]
        bpy.context.view_layer.update()

    def bake():
        bake_pose_action(arm, param + '_param', [param], pose, keys=2, scale=[param])
    F.custom_arms.append((arm, bake, {param + '_param': [param]}))
    F.extra_params.append({'id': '%s.%s' % (F.name, param), 'node': arm.name, 'bone': param, 'action': param + '_param', 'type': 'scale',
                           'min': list(s0), 'max': list(s1), 'unit': 'ratio', 'continuous': False, 'rest': 0.0, 'parent_bone': root, 'requires': {},
                           'parts': [json.loads(o['sh'])['id'] for o in parts if 'sh' in o], 'note': note})
    return arm
