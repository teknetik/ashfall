# pistol/px.py: the scrap pistol's own surfaces (model-pistol-surface, 20 Nov 2026). The kit is not edited: this
# module builds layered materials that expose the same taps the kit's baker reads (OUT, BSDF, BUMP, ORM, CH_base,
# CH_metal, CH_rough, CH_emit, CH_orm), the pistol's hand-wound wrap, its forged trigger guard, strip UVs for wires
# and straps, a replacement for the kit's unwrap (same atlas, strips unrolled, per-face texel weights), the dirty
# glass of the cell and the 2048 texture set of the in-hand copy.
#
# Materials are written in the pistol frame P (metres, muzzle -X, up +Z): every material takes the origin of the
# part it goes on, so wear fields are given once in pistol millimetres and stay put when the part's origin moves.
# Colours are sRGB triples (as in kit/mats.py) unless a name says linear.
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

KIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit')
if KIT not in sys.path:
    sys.path.insert(0, KIT)
import geo as G
import mats as MT
import pgeom as PG

MM = 0.001
C = MT.srgb
DIAG = set(x for x in os.environ.get('PX_DIAG', '').split(',') if x)      # bisecting switches (work/diag.sh)
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def mm(p):
    return Vector(p) * MM


# ====================================================================== the layer stack
class Stack:
    """A material built as layers over a base: each layer is a mask and what it changes (colour, metallic, roughness,
    height). finish() wires the kit's taps."""

    def __init__(self, name, base, metal, rough, origin=(0, 0, 0)):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        self.m, self.nt = m, m.node_tree
        self.nt.nodes.clear()
        b = self.b = MT.NB(m)
        out = b.n('ShaderNodeOutputMaterial'); out.name = 'OUT'
        bsdf = b.n('ShaderNodeBsdfPrincipled'); bsdf.name = 'BSDF'
        tc = b.n('ShaderNodeTexCoord')
        self.geo = b.n('ShaderNodeNewGeometry')
        o = Vector(origin)
        self.P = b.vmath('ADD', tc.outputs['Object'], tuple(o)) if o.length > 0 else tc.outputs['Object']
        self.N = self.geo.outputs['Normal']
        self.col = b.rgb(C(base))
        self.metal = b.value(metal)
        self.rough = b.value(rough)
        self.h = b.value(0.0)
        self._c = {}
        m['px_flat'] = [float(x) for x in C(base)] + [float(metal), float(rough)]

    # ---------------------------------------------------------------- arithmetic
    def add(self, a, c):
        return self.b.math('ADD', a, c)

    def sub(self, a, c):
        return self.b.math('SUBTRACT', a, c)

    def mul(self, a, c, clamp=False):
        return self.b.math('MULTIPLY', a, c, clamp=clamp)

    def mx(self, a, c):
        return self.b.math('MAXIMUM', a, c)

    def mn(self, a, c):
        return self.b.math('MINIMUM', a, c)

    def inv(self, a):
        return self.b.math('SUBTRACT', 1.0, a, clamp=True)

    def ramp(self, v, lo, hi):
        return self.b.ramp(v, lo, hi)

    def sat(self, a):
        return self.b.math('MINIMUM', self.b.math('MAXIMUM', a, 0.0), 1.0)

    def wsum(self, *terms):
        """sum of (socket, weight) pairs and plain numbers"""
        acc = None
        const = 0.0
        for t in terms:
            if isinstance(t, (int, float)):
                const += t; continue
            s, w = t
            v = s if w == 1.0 else self.mul(s, w)
            acc = v if acc is None else self.add(acc, v)
        if const:
            acc = self.add(acc, const) if acc is not None else self.b.value(const)
        return acc

    # ---------------------------------------------------------------- coordinates and noise
    def sepP(self):
        if 'sep' not in self._c:
            s = self.b.n('ShaderNodeSeparateXYZ'); self.b.l(self.P, s.inputs[0])
            self._c['sep'] = s.outputs
        return self._c['sep']

    def dot(self, v, offset=(0, 0, 0)):
        """(P - offset) . v, metres"""
        o = Vector(offset)
        p = self.b.vmath('SUBTRACT', self.P, tuple(o)) if o.length > 0 else self.P
        return self.b.vmath('DOT_PRODUCT', p, tuple(Vector(v)))

    def noise(self, scale, detail=4, rough=0.55, vec=None, shift=None):
        v = self.P if vec is None else vec
        if shift is not None:
            v = self.b.vmath('ADD', v, tuple(shift))
        return self.b.noise(v, scale, detail, rough)

    def coords(self, a, sa, c, sc, e=None, se=0.0):
        """vector (a * sa, c * sc, e * se) from scalar sockets"""
        cb = self.b.n('ShaderNodeCombineXYZ')
        for i, (s, k) in enumerate(((a, sa), (c, sc), (e, se))):
            if s is None:
                continue
            self.b.l(self.mul(s, k) if k != 1.0 else s, cb.inputs[i])
        return cb.outputs[0]

    def aniso(self, d, along, across, detail=3, rough=0.5, shift=0.0):
        """noise stretched along direction d (pistol frame): `along` and `across` are scales per metre"""
        d = Vector(d).normalized()
        e1 = d.cross(Y)
        if e1.length < 1e-3:
            e1 = d.cross(Z)
        e1.normalize(); e2 = d.cross(e1)
        a = self.add(self.dot(d), shift) if shift else self.dot(d)
        return self.b.noise(self.coords(a, along, self.dot(e1), across, self.dot(e2), across), 1.0, detail, rough)

    def voronoi(self, scale, vec=None, feature='F1'):
        v = self.b.n('ShaderNodeTexVoronoi', feature=feature)
        v.inputs['Scale'].default_value = scale
        self.b.l(self.P if vec is None else vec, v.inputs['Vector'])
        return v.outputs

    # ---------------------------------------------------------------- geometry masks
    def edge(self, radius, lo=0.004, hi=0.05, samples=4):
        """1 near an edge (convex or concave) within about `radius`"""
        key = ('edge', radius)
        if key not in self._c:
            bev = self.b.n('ShaderNodeBevel', samples=samples)
            bev.inputs['Radius'].default_value = radius
            self._c[key] = self.b.math('SUBTRACT', 1.0, self.b.vmath('DOT_PRODUCT', bev.outputs['Normal'], self.N))
        return self.ramp(self._c[key], lo, hi)

    def cavity(self, dist, lo=0.12, hi=0.6, samples=4, inside=False):
        """1 in recesses (inside=False) or on thin and convex places (inside=True), looking only at this object"""
        key = ('ao', dist, inside)
        if key not in self._c:
            ao = self.b.n('ShaderNodeAmbientOcclusion', only_local=True, samples=samples, inside=inside)
            ao.inputs['Distance'].default_value = dist
            self._c[key] = self.b.math('SUBTRACT', 1.0, ao.outputs['AO'])
        return self.ramp(self._c[key], lo, hi)

    def facing(self, axis, lo=0.0, hi=1.0):
        return self.ramp(self.b.vmath('DOT_PRODUCT', self.N, tuple(Vector(axis).normalized())), lo, hi)

    def field(self, items):
        """items: [(centre mm, radii mm)] ellipsoids in the pistol frame: 1 at a centre, 0 at and beyond its surface"""
        f = None
        for c, r in items:
            dv = self.b.vmath('MULTIPLY', self.b.vmath('SUBTRACT', self.P, tuple(mm(c))), (1.0 / (r[0] * MM), 1.0 / (r[1] * MM), 1.0 / (r[2] * MM)))
            v = self.b.math('SUBTRACT', 1.0, self.b.vmath('LENGTH', dv), clamp=True)
            f = v if f is None else self.mx(f, v)
        return f

    def seg(self, a, c):
        """distance (metres) from P to the segment a-c (points in mm, pistol frame)"""
        a = mm(a); c = mm(c); ab = c - a
        pa = self.b.vmath('SUBTRACT', self.P, tuple(a))
        t = self.b.math('DIVIDE', self.b.vmath('DOT_PRODUCT', pa, tuple(ab)), ab.length_squared)
        t = self.sat(t)
        sc = self.b.n('ShaderNodeVectorMath', operation='SCALE')
        sc.inputs[0].default_value = tuple(ab)
        self.b.l(t, sc.inputs['Scale'])
        return self.b.vmath('LENGTH', self.b.vmath('SUBTRACT', pa, sc.outputs['Vector']))

    def attr(self, name):
        key = ('attr', name)
        if key not in self._c:
            a = self.b.n('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name=name)
            s = self.b.n('ShaderNodeSeparateXYZ'); self.b.l(a.outputs['Vector'], s.inputs[0])
            self._c[key] = s.outputs
        return self._c[key]

    def dings(self, scale=45.0, r=0.05, density=0.22, shift=(0.013, 0.007, 0.021)):
        """sparse round nicks: (mask, soft rim)"""
        v = self.voronoi(scale, self.b.vmath('ADD', self.P, tuple(shift)))
        gate = self.ramp(v['Color'], 1.0 - density - 0.02, 1.0 - density + 0.02)
        return self.mul(self.inv(self.ramp(v['Distance'], r * 0.35, r)), gate), self.mul(self.inv(self.ramp(v['Distance'], r, r * 1.7)), gate)

    # ---------------------------------------------------------------- layers
    def colour(self, c):
        return self.b.rgb(C(c))

    def mixcol(self, fac, a, c):
        return self.b.mixc(fac, C(a) if isinstance(a, (tuple, list)) else a, C(c) if isinstance(c, (tuple, list)) else c)

    def layer(self, mask, col=None, metal=None, rough=None, h=0.0, amount=1.0):
        b = self.b
        if isinstance(mask, (int, float)):
            mask = b.value(mask)
        if amount != 1.0:
            mask = b.math('MULTIPLY', mask, amount, clamp=True)
        if col is not None:
            self.col = b.mixc(mask, self.col, C(col) if isinstance(col, (tuple, list)) else col)
        if metal is not None:
            self.metal = b.mixf(mask, self.metal, metal)
        if rough is not None:
            self.rough = b.mixf(mask, self.rough, rough)
        if h:
            self.h = b.math('ADD', self.h, b.math('MULTIPLY', mask, h))
        return mask

    def darken(self, mask, f, amount=1.0):
        """multiply the colour by f (a number or a colour) where mask is 1"""
        b = self.b
        if amount != 1.0:
            mask = b.math('MULTIPLY', mask, amount, clamp=True)
        m = b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); m.clamp_factor = True
        b.l(mask, m.inputs[0]); b.l(self.col, m.inputs[6])
        m.inputs[7].default_value = (tuple(f) if isinstance(f, (tuple, list)) else (f, f, f)) + (1.0,)
        self.col = m.outputs[2]
        return mask

    def roughen(self, v, k):
        """rough += (v - 0.5) * 2k"""
        self.rough = self.add(self.rough, self.mul(self.sub(v, 0.5), 2 * k))

    def bump(self, v, k):
        self.h = self.add(self.h, self.mul(v, k))

    def finish(self, emit=None, bevel_r=0.0003, bump_dist=0.00015, ao_dist=0.006, strength=1.0, alpha=None):
        """emit: (colour, strength, mask socket or None). alpha: a socket (the cell glass). Returns the material.
        Emission is stored as colour x strength with an emission strength of 1 (not the kit's colour x strength / 8
        with a strength of 8): glTFast 6.x does not read KHR_materials_emissive_strength, so only what is in the
        texture reaches Unity."""
        b, nt = self.b, self.nt
        bump = b.n('ShaderNodeBump'); bump.name = 'BUMP'
        if bevel_r > 0:
            bvn = b.n('ShaderNodeBevel', samples=8); bvn.inputs['Radius'].default_value = bevel_r
            b.l(bvn.outputs['Normal'], bump.inputs['Normal'])
        bump.inputs['Strength'].default_value = strength
        bump.inputs['Distance'].default_value = bump_dist
        b.l(self.h, bump.inputs['Height'])
        if emit:
            ecol = b.rgb(C(emit[0]))
            if emit[2] is not None:
                ecol = b.mixc(emit[2], (0, 0, 0), ecol)
            sc8 = b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); sc8.clamp_factor = True
            sc8.inputs[0].default_value = 1.0
            b.l(ecol, sc8.inputs[6]); sc8.inputs[7].default_value = (emit[1],) * 3 + (1,)
            emit_s = sc8.outputs[2]; emit_str = 1.0
        else:
            emit_s = b.rgb((0, 0, 0)); emit_str = 0.0
        aon = b.n('ShaderNodeAmbientOcclusion', only_local=True, samples=8)
        aon.inputs['Distance'].default_value = ao_dist
        orm = b.n('ShaderNodeCombineColor'); orm.name = 'ORM'
        b.l(aon.outputs['AO'], orm.inputs[0])
        for i, v in ((1, self.rough), (2, self.metal)):
            b.l(self.sat(v), orm.inputs[i])
        bsdf = nt.nodes['BSDF']
        taps = [('CH_base', self.col), ('CH_metal', self.metal), ('CH_rough', self.rough), ('CH_emit', emit_s), ('CH_orm', orm.outputs[0])]
        if alpha is not None:
            ac = b.n('ShaderNodeCombineColor')              # red = alpha, green = 1: marks the glass texels in px.bake_alpha
            b.l(self.sat(alpha), ac.inputs[0]); ac.inputs[1].default_value = 1.0; ac.inputs[2].default_value = 0.0
            taps.append(('CH_alpha', ac.outputs[0]))
        for nm, sock in taps:
            r = b.n('NodeReroute'); r.name = nm; b.l(sock, r.inputs[0])
        b.l(nt.nodes['CH_base'].outputs[0], bsdf.inputs['Base Color'])
        b.l(nt.nodes['CH_metal'].outputs[0], bsdf.inputs['Metallic'])
        b.l(nt.nodes['CH_rough'].outputs[0], bsdf.inputs['Roughness'])
        b.l(nt.nodes['CH_emit'].outputs[0], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = emit_str
        b.l(bump.outputs['Normal'], bsdf.inputs['Normal'])
        if alpha is not None:
            b.l(self.sat(alpha), bsdf.inputs['Alpha'])
            self.m['px_glass'] = 1
            try:
                self.m.surface_render_method = 'BLENDED'
            except Exception:
                pass
        b.l(bsdf.outputs[0], nt.nodes['OUT'].inputs['Surface'])
        self.m['emissive'] = 1 if emit else 0
        self.m['wipe'] = 0
        self.m['px'] = 1
        return self.m


# ====================================================================== recipes
RUST_A, RUST_B, RUST_D = (0.46, 0.235, 0.10), (0.31, 0.15, 0.07), (0.15, 0.085, 0.05)      # 21 Nov: a touch more orange, so recess rust reads as rust and not as grime
OIL = (0.052, 0.045, 0.038)


def steel(name, origin=(0, 0, 0), finish=(0.33, 0.335, 0.355), finish_metal=0.85, finish_rough=0.54, patina=(0.385, 0.32, 0.275), patina_amt=0.6,
          worn=(0.62, 0.605, 0.585), worn_rough=0.40, bare=(0.84, 0.825, 0.79), bare_rough=0.26, thin=0.02, edge_gain=0.75, fields=(), field_gain=0.36,
          dir1=(1, 0, 0.06), dir2=(1, 0, -0.42), scratch=1.0, mach=None, mach_amt=0.3, rust=1.0, pits=1.0, grime=1.0, dings=0.2,
          edge_w=0.0008, wide_w=0.0024, edge_amt=1.0, oil=0.12, cav_w=0.004, stain=0.5, convex=0.0, bevel_r=0.0003):
    """Old finished steel: a dark finish (blued, parkerised, black oxide) thinned to grey where it is handled and
    worn to bright metal on edges, scratched along dir1 (and a few along dir2), rust in the recesses and in a few
    freckled blooms, old oil and dirt in the tight corners. fields: ellipsoids (centre mm, radii mm) where hand and
    holster rub. mach: direction of the machining or filing marks (default dir1). convex: extra thinning on thin and
    convex places (ribs, lips)."""
    s = Stack(name, finish, finish_metal, finish_rough, origin)
    n_big = s.noise(20, 2, 0.5)
    n_mid = s.noise(420, 5, 0.6)
    n_fine = s.noise(1500, 3, 0.5)
    n_soft = s.noise(75, 3, 0.55, shift=(0.21, 0.4, 0.13))
    cavW = s.cavity(cav_w, 0.10, 0.55)
    cavN = s.cavity(0.0016, 0.18, 0.70)
    edgeN = s.edge(edge_w)
    edgeW = s.edge(wide_w, 0.002, 0.10)
    opn = s.inv(cavW)
    # the finish drifts toward a plum-brown patina in broad soft areas
    s.layer(s.ramp(n_big, 0.35, 0.70), col=patina, rough=finish_rough + 0.05, amount=patina_amt)
    s.layer(s.ramp(s.noise(31, 2, 0.5, shift=(0.4, 0.15, 0.3)), 0.52, 0.80), col=tuple(min(1.0, c * 1.2 + 0.01) for c in finish), rough=finish_rough - 0.05, amount=0.55)
    # where the finish has thinned: near edges, in the handled fields (a soft gradient), in smears along the draw
    streak = s.aniso(dir1, 17, 250, 3)
    terms = [(streak, 0.42), (n_soft, 0.18), (n_mid, 0.26), (n_fine, 0.14), (edgeW, edge_gain), thin]
    F = s.field(fields) if fields else None
    if F is not None:
        terms.append((F, field_gain))
    if convex:
        terms.append((s.cavity(0.0014, 0.25, 0.8, inside=True), convex))
    drive = s.wsum(*terms)
    thin_m = s.mul(s.ramp(drive, 0.56, 0.82), opn)
    s.layer(thin_m, col=worn, metal=1.0, rough=worn_rough, h=-0.15)
    # scratches: a fine grain of them along the draw that only changes the sheen; a few that show, in loose groups
    hair = s.aniso(dir1, 22, 2600, 2)
    s.roughen(hair, 0.07)
    if scratch:
        g1 = s.ramp(s.noise(34, 2, 0.5), 0.46, 0.66)
        if F is not None:
            g1 = s.mx(g1, s.ramp(F, 0.25, 0.7))
        sc1 = s.mul(s.ramp(s.aniso(dir1, 15, 1500, 2), 0.70, 0.745), g1)
        sc2 = s.mul(s.ramp(s.aniso(dir2, 11, 1250, 2, shift=0.37), 0.725, 0.76), s.ramp(s.noise(27, 2, 0.5, shift=(0.11, 0.05, 0.23)), 0.5, 0.68))
        scr = s.mul(s.mx(sc1, sc2), opn)
        s.layer(scr, col=worn, metal=1.0, rough=0.32, h=-0.55, amount=0.75 * scratch)
        s.layer(s.mul(scr, s.ramp(n_mid, 0.5, 0.7)), col=bare, metal=1.0, rough=0.28, amount=0.5 * scratch)
    # bright metal on the edges, broken up
    wear = s.mul(s.mul(edgeN, s.ramp(s.wsum((n_mid, 1.0), (n_fine, 0.35)), 0.28, 0.56)), s.inv(cavN))
    s.layer(wear, col=bare, metal=1.0, rough=bare_rough, amount=edge_amt)
    if dings:
        dg, rim = s.dings(density=dings)
        s.layer(s.mul(rim, opn), col=worn, metal=1.0, rough=worn_rough, amount=0.5)
        s.layer(s.mul(dg, opn), col=bare, metal=1.0, rough=0.3, h=-2.2)
    # rust: never metallic. A thin brown stain next to the recesses, crusted in them, freckles in a few blooms
    if rust:
        n_r = s.noise(260, 4, 0.6, shift=(0.3, 0.1, 0.2))
        rdrive = s.wsum((cavW, 0.95), (n_r, 0.6), -0.3)
        rcol = s.mixcol(s.ramp(s.noise(900, 3, 0.5), 0.35, 0.65), RUST_A, RUST_B)
        crust = s.add(0.55, s.mul(s.ramp(s.noise(1300, 3, 0.55, shift=(0.1, 0.3, 0.2)), 0.3, 0.7), 0.45))
        # a few broad brown washes over the flats (two or three on the whole pistol), soft-edged, thin
        wash = s.mul(s.ramp(s.wsum((s.noise(13, 2, 0.5, shift=(0.31, 0.12, 0.44)), 0.75), (n_soft, 0.25)), 0.50, 0.72), s.add(0.45, s.mul(s.ramp(n_mid, 0.3, 0.7), 0.55)))
        s.layer(s.mul(wash, opn), col=RUST_B, metal=0.1, rough=0.8, amount=0.42 * rust)
        s.layer(s.ramp(rdrive, 0.02, 0.40), col=RUST_B, metal=0.0, rough=0.82, amount=min(1.0, (stain + 0.1) * rust))
        s.layer(s.mul(s.ramp(rdrive, 0.24, 0.50), crust), col=rcol, metal=0.0, rough=0.94, h=0.45, amount=min(1.0, rust))
    if pits:
        bloom = s.ramp(s.wsum((s.noise(24, 2, 0.5, shift=(0.07, 0.19, 0.03)), 0.8), (n_soft, 0.2)), 0.54, 0.74)
        pm = s.mul(s.ramp(s.noise(2100, 2, 0.5), 0.61, 0.69), s.sat(s.wsum((bloom, 1.0), (cavW, 0.7), (edgeW, 0.12))))
        halo = s.mul(s.ramp(s.noise(700, 3, 0.55, shift=(0.2, 0.5, 0.1)), 0.50, 0.66), bloom)
        s.layer(s.mul(halo, opn), col=RUST_B, metal=0.0, rough=0.85, amount=0.55 * min(1.0, pits))
        s.layer(pm, col=RUST_B, metal=0.0, rough=0.92, h=-0.7, amount=min(1.0, pits) * 0.9)
        s.layer(s.mul(pm, s.ramp(n_mid, 0.5, 0.68)), col=RUST_A, metal=0.0, rough=0.92, amount=min(1.0, pits) * 0.7)
    # old oil and dirt packed into the tight corners
    if grime:
        gm = s.ramp(s.wsum((cavN, 1.0), (s.noise(700, 3, 0.5), 0.35), -0.175), 0.30, 0.72)
        s.layer(gm, col=OIL, metal=0.0, rough=0.52, amount=min(1.0, grime))
    # oily where handled, dry elsewhere
    smudge = s.ramp(s.noise(58, 3, 0.55, shift=(0.5, 0.2, 0.1)), 0.42, 0.75)
    s.rough = s.sub(s.rough, s.mul(s.mul(smudge, opn), oil))
    s.roughen(n_mid, 0.05)
    # height: grain, machining marks
    s.bump(n_fine, 0.12)
    s.bump(s.aniso(mach or dir1, 45, 2300, 2), mach_amt)
    s.bump(s.aniso(dir2, 30, 1700, 2, shift=0.2), mach_amt * 0.5)          # the file went across as well
    s.bump(s.noise(800, 4, 0.6), 0.15)
    return s.finish(bevel_r=bevel_r)


def turned_steel(name, origin, axis_yz, **kw):
    """Steel turned on a lathe about an X-parallel axis: rings for machining marks and scratches."""
    kw.setdefault('dir1', (0.02, 1, 0.3)); kw.setdefault('dir2', (1, 0.2, 0)); kw.setdefault('mach', (0, 1, 0.01))
    return steel(name, origin, **kw)


def rusty_steel(name, origin=(0, 0, 0), bare=(0.70, 0.68, 0.64)):
    """A fastener rusted in: mostly rust, dark steel between, bright only where a driver has slipped."""
    s = Stack(name, (0.21, 0.17, 0.15), 0.85, 0.6, origin)
    n_mid = s.noise(520, 4, 0.6); n_fine = s.noise(1700, 3, 0.5)
    cav = s.cavity(0.003, 0.08, 0.5)
    rcol = s.mixcol(s.ramp(s.noise(1100, 3, 0.5), 0.35, 0.65), RUST_A, RUST_B)
    s.layer(s.ramp(s.wsum((n_mid, 1.0), (cav, 0.6)), 0.36, 0.58), col=rcol, metal=0.0, rough=0.94, h=0.5)
    s.layer(s.ramp(n_fine, 0.58, 0.68), col=RUST_D, metal=0.0, rough=0.92, h=-0.6)
    s.layer(s.mul(s.edge(0.0005), s.ramp(n_mid, 0.42, 0.6)), col=bare, metal=1.0, rough=0.3, amount=0.8)
    s.layer(s.ramp(s.cavity(0.0014, 0.2, 0.7), 0.3, 0.8), col=RUST_D, metal=0.0, rough=0.9)
    s.bump(n_fine, 0.3); s.bump(n_mid, 0.5)
    return s.finish()


def bright_steel(name, origin=(0, 0, 0), base=(0.60, 0.59, 0.565), rough=0.30, dirname=(0, 1, 0)):
    """Pins, springs and studs: bright hard steel gone grey, brown in the corners."""
    s = Stack(name, base, 1.0, rough, origin)
    n_mid = s.noise(520, 4, 0.6)
    cav = s.cavity(0.003, 0.1, 0.55)
    s.layer(s.ramp(s.noise(60, 3, 0.5), 0.4, 0.7), col=(0.42, 0.40, 0.375), rough=rough + 0.12, amount=0.6)
    s.layer(s.ramp(s.wsum((cav, 1.0), (n_mid, 0.5), -0.25), 0.25, 0.6), col=RUST_B, metal=0.2, rough=0.85, amount=0.8)
    s.layer(s.mul(s.edge(0.0004), s.ramp(n_mid, 0.4, 0.6)), col=(0.82, 0.81, 0.78), metal=1.0, rough=0.2, amount=0.7)
    s.roughen(n_mid, 0.06)
    s.bump(s.aniso(dirname, 40, 2400, 2), 0.2)
    return s.finish()


def brass(name, origin=(0, 0, 0), base=(0.58, 0.435, 0.225), rough=0.46, tarnish=(0.24, 0.18, 0.10), bright=(0.90, 0.73, 0.41), green=0.35,
          edge_amt=1.0, fields=(), spots=0.6, dir1=(1, 0, 0.1), convex=0.0, tarn=0.75, tarn_lo=0.38):
    """Old brass: brown-gold, dark in the corners, bright only on knurls, edges and where a thumb rubs."""
    s = Stack(name, base, 1.0, rough, origin)
    n_big = s.noise(30, 2, 0.5); n_mid = s.noise(420, 5, 0.6); n_fine = s.noise(1500, 3, 0.5)
    cavW = s.cavity(0.0035, 0.10, 0.55); cavN = s.cavity(0.0014, 0.18, 0.7)
    opn = s.inv(cavW)
    # uneven tarnish: darker brown in broad areas, a little red
    s.layer(s.ramp(s.wsum((n_big, 0.6), (n_mid, 0.4)), tarn_lo, tarn_lo + 0.28), col=(0.36, 0.25, 0.13), rough=rough + 0.1, amount=tarn)
    s.layer(s.ramp(s.noise(140, 3, 0.5, shift=(0.2, 0.4, 0.1)), 0.55, 0.75), col=(0.50, 0.31, 0.19), amount=0.4)
    # rubbed bright
    terms = [(s.edge(0.0016, 0.002, 0.10), 0.55), (s.aniso(dir1, 30, 420, 3), 0.45), (n_mid, 0.3), (n_fine, 0.15)]
    if convex:
        terms.append((s.cavity(0.0012, 0.25, 0.8, inside=True), convex))
    if fields:
        terms.append((s.ramp(s.field(fields), 0.0, 0.6), 0.5))
    rub = s.mul(s.ramp(s.wsum(*terms), 0.62, 0.86), opn)
    s.layer(rub, col=tuple(0.5 * (a + c) for a, c in zip(base, bright)), rough=0.33, amount=0.9)
    wear = s.mul(s.mul(s.edge(0.0005), s.ramp(s.wsum((n_mid, 1.0), (n_fine, 0.35)), 0.34, 0.6)), s.inv(cavN))
    s.layer(wear, col=bright, rough=0.22, amount=edge_amt)
    sc = s.mul(s.ramp(s.aniso(dir1, 14, 1500, 2), 0.67, 0.71), opn)
    s.layer(sc, col=bright, rough=0.28, h=-0.4, amount=0.6)
    # dark spots and old fingerprints
    if spots:
        sp = s.ramp(s.noise(900, 3, 0.55, shift=(0.4, 0.3, 0.6)), 0.64, 0.72)
        s.layer(s.mul(sp, s.ramp(n_big, 0.3, 0.6)), col=(0.13, 0.10, 0.07), metal=0.4, rough=0.7, amount=spots)
    # tarnish and verdigris in the recesses
    td = s.wsum((cavW, 1.0), (n_mid, 0.5), -0.25)
    s.layer(s.ramp(td, 0.15, 0.5), col=tarnish, metal=0.3, rough=0.7, amount=0.7)
    s.layer(s.ramp(td, 0.42, 0.7), col=(0.10, 0.08, 0.05), metal=0.0, rough=0.8)
    if green:
        gr = s.mul(s.ramp(s.wsum((cavN, 1.0), (s.noise(600, 3, 0.5, shift=(0.1, 0.7, 0.2)), 0.6), -0.3), 0.42, 0.62), s.ramp(s.noise(90, 2, 0.5), 0.45, 0.6))
        s.layer(gr, col=(0.27, 0.42, 0.34), metal=0.0, rough=0.9, h=0.3, amount=green)
    s.roughen(n_mid, 0.06)
    s.bump(n_fine, 0.1); s.bump(s.aniso(dir1, 45, 2300, 2), 0.18)
    return s.finish()


def copper(name, origin=(0, 0, 0), base=(0.54, 0.31, 0.205), rough=0.48, bright=(0.84, 0.51, 0.35), green=0.6, st=False, dark=0.5):
    """Old copper wire and strip: dull brown-red, brighter where it rubs, green where two strands lie together.
    st: the part carries the strip attribute (u along the wire)."""
    s = Stack(name, base, 1.0, rough, origin)
    n_mid = s.noise(420, 5, 0.6); n_fine = s.noise(1500, 3, 0.5); n_big = s.noise(45, 2, 0.5)
    cavW = s.cavity(0.0022, 0.10, 0.5); cavN = s.cavity(0.0010, 0.15, 0.6)
    s.layer(s.ramp(s.wsum((n_big, 0.6), (n_mid, 0.4)), 0.36, 0.64), col=(0.37, 0.21, 0.14), rough=rough + 0.14, amount=dark + 0.25)
    s.layer(s.ramp(s.noise(170, 3, 0.5, shift=(0.3, 0.1, 0.5)), 0.52, 0.78), col=(0.17, 0.11, 0.085), metal=0.5, rough=0.7, amount=dark * 0.8)
    rub = s.mul(s.ramp(s.wsum((n_mid, 0.35), (n_fine, 0.2), (s.noise(60, 3, 0.5), 0.75)), 0.66, 0.90), s.inv(cavW))
    s.layer(rub, col=bright, rough=0.30, amount=0.5)
    gd = s.wsum((cavN, 1.0), (cavW, 0.35), (s.noise(520, 3, 0.55, shift=(0.6, 0.2, 0.9)), 0.6), -0.3)
    s.layer(s.ramp(gd, 0.35, 0.7), col=(0.13, 0.085, 0.06), metal=0.2, rough=0.8, amount=0.85)
    if green:
        s.layer(s.mul(s.ramp(gd, 0.72, 0.95), s.ramp(s.noise(130, 3, 0.5, shift=(0.2, 0.9, 0.4)), 0.42, 0.6)), col=(0.27, 0.44, 0.37), metal=0.0, rough=0.92, h=0.5, amount=green)
        s.layer(s.mul(s.ramp(s.noise(1300, 2, 0.5), 0.68, 0.73), s.ramp(n_big, 0.55, 0.72)), col=(0.29, 0.45, 0.38), metal=0.0, rough=0.9, amount=green * 0.35)
    s.roughen(n_mid, 0.07)
    s.bump(n_fine, 0.15)
    return s.finish(bevel_r=0.0)


def grip_us(s):
    """(u, s) of the grip frame (metres) and y, as sockets"""
    if 'us' not in s._c:
        s._c['us'] = (s.dot(PG.U_, PG.G0), s.dot(PG.S_, PG.G0), s.dot(Y))
    return s._c['us']


# the bands of the wrap as they lie on the grip: (s centre, width) in mm; the helical tapes cover a range
WRAP_BANDS = ((9.0, 13.0), (-7.5, 13.5), (-38.2, 12.0), (23.0, 21.0), (-23.5, 24.0))


def wood(name, origin=(0, 0, 0), base=(0.205, 0.118, 0.07), dark=(0.085, 0.05, 0.032), pale=(0.48, 0.345, 0.225), rough=0.50, cracks=(), holes=(), side=1):
    """An old oiled walnut scale: dark, close grain along the grip, black dirt in the pores, round the screws and
    along the crack, paler under the wrap where it was covered and along the lines where the wrap's edges lay, pale
    dry wood only on the worn high edges. cracks: [((u, s), (u, s))] mm in the grip frame; holes: [(u, s)]."""
    s = Stack(name, base, 0.0, rough, origin)
    b = s.b
    u, sv, y = grip_us(s)
    n_fine = s.noise(1500, 3, 0.5)
    # grain: long streaks along the grip axis, a slow figure across them
    g1 = s.aniso(PG.S_, 14, 620, 4, 0.6)
    g2 = s.aniso(PG.S_, 40, 1700, 3, 0.5, shift=0.3)
    fig = s.aniso(PG.S_, 9, 75, 3, 0.5, shift=0.7)
    gr = s.wsum((g1, 0.6), (g2, 0.4))
    s.layer(s.ramp(fig, 0.35, 0.7), col=(0.27, 0.155, 0.09), amount=0.5)
    s.layer(s.ramp(gr, 0.50, 0.68), col=dark, rough=0.62, h=-0.5, amount=0.6)
    pores = s.mul(s.ramp(s.aniso(PG.S_, 160, 2600, 2), 0.63, 0.70), s.ramp(g1, 0.35, 0.6))
    s.layer(pores, col=(0.035, 0.024, 0.018), rough=0.7, h=-0.8)
    # covered by the wrap: the oil finish is duller and a little paler there; dirt lines where the edges of the wrap lay
    cov = None
    line = None
    for (sc, w) in WRAP_BANDS:
        d = b.math('ABSOLUTE', s.sub(sv, sc * MM))
        c1 = s.inv(s.ramp(d, (w / 2 - 0.8) * MM, (w / 2 + 0.8) * MM))
        l1 = s.inv(s.ramp(b.math('ABSOLUTE', s.sub(d, w / 2 * MM)), 0.25 * MM, 1.3 * MM))
        cov = c1 if cov is None else s.mx(cov, c1)
        line = l1 if line is None else s.mx(line, l1)
    n_c = s.noise(300, 4, 0.6, shift=(0.2, 0.5, 0.1))
    s.layer(s.mul(cov, s.ramp(n_c, 0.25, 0.6)), col=(0.30, 0.19, 0.12), rough=0.62, amount=0.5)
    s.layer(s.mul(line, s.ramp(n_c, 0.3, 0.55)), col=(0.035, 0.026, 0.02), rough=0.66, amount=0.75)
    # handled, oiled and shiny where the hand is and the wrap is not
    opn_w = s.inv(cov)
    s.rough = s.sub(s.rough, s.mul(s.mul(opn_w, s.ramp(s.noise(70, 3, 0.5), 0.3, 0.7)), 0.16))
    s.darken(s.mul(opn_w, s.ramp(s.noise(55, 3, 0.5, shift=(0.3, 0.3, 0.3)), 0.35, 0.75)), 0.62, 0.8)
    # worn pale on the high edges only
    edgeW = s.edge(0.0026, 0.003, 0.09)
    cavW = s.cavity(0.0035, 0.10, 0.5); cavN = s.cavity(0.0014, 0.16, 0.6)
    wear = s.mul(s.mul(edgeW, s.ramp(s.wsum((s.noise(380, 4, 0.6), 1.0), (n_fine, 0.3)), 0.34, 0.60)), s.inv(cavW))
    s.layer(wear, col=pale, rough=0.74, h=-0.2, amount=0.85)
    # dents and bruises
    dg, rim = s.dings(scale=38.0, r=0.06, density=0.2)
    s.layer(dg, col=(0.05, 0.034, 0.025), rough=0.6, h=-2.5)
    # dirt: in the recesses, round the screw holes, down the crack
    dirt = s.ramp(s.wsum((cavW, 1.0), (n_c, 0.5), -0.25), 0.15, 0.55)
    for (hu, hs) in holes:
        dh = b.vmath('LENGTH', s.coords(s.sub(u, hu * MM), 1.0, s.sub(sv, hs * MM), 1.0))
        dirt = s.mx(dirt, s.mul(s.inv(s.ramp(s.add(dh, s.mul(s.sub(n_c, 0.5), 0.004)), 0.0042, 0.0085)), 0.9))
    s.layer(dirt, col=(0.040, 0.030, 0.024), rough=0.68, amount=0.9)
    for (a, c) in cracks:
        s.layer(s.inv(s.ramp(s.add(_plane_dist(s, a, c), s.mul(s.sub(n_c, 0.5), 0.0012)), 0.0003, 0.0022)), col=(0.022, 0.017, 0.014), rough=0.72, amount=0.85)
    s.layer(s.ramp(cavN, 0.35, 0.8), col=(0.016, 0.013, 0.011), rough=0.75)
    s.roughen(s.noise(420, 4, 0.6), 0.06)
    s.bump(g2, 0.35); s.bump(n_fine, 0.1)
    return s.finish(bevel_r=0.0004)


def _plane_dist(s, a, c):
    """distance (metres) in the grip's (u, s) plane from P to the segment a-c given in mm"""
    b = s.b
    u, sv, y = grip_us(s)
    ax, ay = a[0] * MM, a[1] * MM
    dx, dy = (c[0] - a[0]) * MM, (c[1] - a[1]) * MM
    L2 = dx * dx + dy * dy
    pu = s.sub(u, ax); ps = s.sub(sv, ay)
    t = s.sat(b.math('DIVIDE', s.add(s.mul(pu, dx), s.mul(ps, dy)), L2))
    ex = s.sub(pu, s.mul(t, dx)); ey = s.sub(ps, s.mul(t, dy))
    return b.math('SQRT', s.add(s.mul(ex, ex), s.mul(ey, ey)))


def leather(name, origin=(0, 0, 0), base=(0.36, 0.23, 0.135), dark=(0.15, 0.092, 0.058), rough=0.66, stitch=True, thread=(0.45, 0.39, 0.29), raw=(0.56, 0.43, 0.30)):
    """A leather strap cut by hand: creased across its width, edges darkened by sweat and dirt, a row of stitch
    holes along each edge with what is left of the thread, shiny where the palm lies. Needs the strip attribute
    px_st = (u along, v across from the middle, half width), metres."""
    s = Stack(name, base, 0.0, rough, origin)
    b = s.b
    st = s.attr('px_st')
    u, v, hw = st['X'], st['Y'], st['Z']
    e = s.sub(hw, b.math('ABSOLUTE', v))                   # distance from the nearer edge
    n_fine = s.noise(1500, 3, 0.5); n_mid = s.noise(380, 4, 0.6); n_big = s.noise(60, 3, 0.5)
    uv = s.coords(u, 1.0, v, 1.0)
    # tone: darker and lighter along the strap, sweat-dark toward the edges
    s.layer(s.ramp(s.wsum((n_big, 0.6), (n_mid, 0.4)), 0.33, 0.68), col=dark, amount=0.7)
    s.layer(s.ramp(s.noise(130, 3, 0.5, shift=(0.4, 0.1, 0.3)), 0.55, 0.78), col=tuple(min(1.0, c * 1.3) for c in base), rough=rough + 0.08, amount=0.45)
    # creases across the strap, and a few along it
    cr = b.noise(s.coords(u, 330.0, v, 28.0), 1.0, 3, 0.55)
    crease = s.ramp(cr, 0.57, 0.66)
    cr2 = b.noise(s.coords(u, 30.0, v, 520.0), 1.0, 2, 0.5)
    crease = s.mx(crease, s.mul(s.ramp(cr2, 0.66, 0.72), 0.7))
    s.layer(crease, col=tuple(c * 0.36 for c in base), rough=0.74, h=-1.8)
    s.layer(s.ramp(cr, 0.50, 0.60), col=tuple(min(1.0, c * 1.22) for c in base), amount=0.35)
    # grain
    vo = s.voronoi(2100, feature='DISTANCE_TO_EDGE')
    s.bump(s.ramp(vo['Distance'], 0.0, 0.12), 0.35)
    # polished and darkened where the hand lies
    palm = s.ramp(s.noise(85, 3, 0.5, shift=(0.2, 0.6, 0.4)), 0.38, 0.72)
    s.rough = s.sub(s.rough, s.mul(palm, 0.20))
    s.darken(palm, 0.72, 0.7)
    # scuffs: pale raw leather
    sc = s.mul(s.ramp(s.noise(520, 4, 0.6, shift=(0.3, 0.3, 0.1)), 0.63, 0.73), s.ramp(n_big, 0.4, 0.65))
    s.layer(sc, col=raw, rough=0.86, h=-0.3, amount=0.7)
    # edges: dark with dirt, the cut edge itself raw and fuzzy
    ed = s.inv(s.ramp(s.add(e, s.mul(s.sub(n_mid, 0.5), 0.0016)), 0.0004, 0.0032))
    s.layer(ed, col=tuple(c * 0.30 for c in base), rough=0.72, amount=0.9)
    s.layer(s.mul(s.inv(s.ramp(e, 0.00005, 0.00035)), s.ramp(n_fine, 0.35, 0.6)), col=raw, rough=0.9, amount=0.55)
    if stitch:
        row = s.inv(s.ramp(b.math('ABSOLUTE', s.sub(e, 0.0019)), 0.00016, 0.00034))
        f = b.math('FRACT', b.math('DIVIDE', u, 0.0034))
        along = b.math('ABSOLUTE', s.sub(f, 0.5))
        hole = s.mul(row, s.inv(s.ramp(along, 0.045, 0.095)))
        kept = s.ramp(b.noise(s.coords(u, 70.0, v, 0.0), 1.0, 2, 0.5), 0.50, 0.60)      # the thread is gone in places
        thr = s.mul(s.mul(s.inv(s.ramp(b.math('ABSOLUTE', s.sub(e, 0.0019)), 0.00010, 0.00024)), s.ramp(along, 0.08, 0.13)), kept)
        s.layer(thr, col=thread, rough=0.85, h=0.9, amount=0.85)
        s.layer(hole, col=(0.03, 0.022, 0.017), rough=0.8, h=-2.2)
        s.layer(s.mul(row, s.inv(s.ramp(along, 0.12, 0.30))), col=tuple(c * 0.5 for c in base), amount=0.4)
    cav = s.cavity(0.0012, 0.2, 0.7)
    s.layer(cav, col=(0.03, 0.022, 0.017), rough=0.75, amount=0.8)
    s.roughen(n_mid, 0.05)
    s.bump(n_fine, 0.25); s.bump(n_mid, 0.3)
    return s.finish(bevel_r=0.0)


def cloth(name, origin=(0, 0, 0), base=(0.45, 0.385, 0.28), dark=(0.17, 0.14, 0.10), rough=0.84, length=0.3, pitch=0.00062, pale=(0.66, 0.60, 0.48), gum=0.3):
    """Cloth friction tape wound by hand: a visible plain weave along the tape, dirt along both edges and in the
    laps, loose pale threads at the edges and a frayed end, a little old gum shining through. Needs px_st."""
    s = Stack(name, base, 0.0, rough, origin)
    b = s.b
    st = s.attr('px_st')
    u, v, hw = st['X'], st['Y'], st['Z']
    e = s.sub(hw, b.math('ABSOLUTE', v))
    n_fine = s.noise(1500, 3, 0.5); n_mid = s.noise(380, 4, 0.6); n_big = s.noise(55, 3, 0.5)
    k = 2 * math.pi / pitch
    wu = b.math('SINE', s.mul(u, k)); wv = b.math('SINE', s.mul(v, k))
    weave = s.mul(s.add(s.mul(s.mul(wu, wv), 0.5), 0.5), 1.0)      # checker of over and under
    ridge = s.mul(b.math('ABSOLUTE', wu), b.math('ABSOLUTE', wv))
    s.layer(s.ramp(weave, 0.25, 0.75), col=tuple(c * 0.74 for c in base), amount=0.55)
    s.bump(ridge, 1.1)
    s.layer(s.inv(s.ramp(ridge, 0.0, 0.22)), col=tuple(c * 0.45 for c in base), amount=0.7)
    # stains: sweat, oil, dirt in broad patches along the tape
    s.layer(s.ramp(s.wsum((n_big, 0.65), (n_mid, 0.35)), 0.36, 0.66), col=dark, rough=rough - 0.06, amount=0.72)
    s.layer(s.ramp(s.noise(120, 3, 0.5, shift=(0.1, 0.5, 0.2)), 0.58, 0.8), col=pale, amount=0.3)
    # worn smooth and dark where the palm lies
    palm = s.ramp(s.noise(80, 3, 0.5, shift=(0.7, 0.2, 0.4)), 0.42, 0.74)
    s.darken(palm, 0.7, 0.7)
    s.rough = s.sub(s.rough, s.mul(palm, 0.12))
    if gum:
        g = s.mul(s.ramp(s.noise(260, 3, 0.5, shift=(0.5, 0.5, 0.1)), 0.62, 0.74), s.inv(s.ramp(e, 0.0006, 0.003)))
        s.layer(g, col=(0.10, 0.075, 0.05), rough=0.42, amount=gum)
    # edges: dirt, then loose threads
    ed = s.inv(s.ramp(s.add(e, s.mul(s.sub(n_mid, 0.5), 0.001)), 0.0003, 0.0020))
    s.layer(ed, col=tuple(c * 0.4 for c in base), amount=0.75)
    fr = s.mul(s.inv(s.ramp(e, 0.0001, 0.0009)), s.ramp(b.noise(s.coords(u, 2600.0, v, 380.0), 1.0, 2, 0.5), 0.5, 0.62))
    s.layer(fr, col=pale, rough=0.92, h=0.8, amount=0.8)
    # the two ends: frayed and pale
    endm = s.mx(s.inv(s.ramp(u, 0.0005, 0.004)), s.ramp(u, length - 0.004, length - 0.0005))
    s.layer(s.mul(endm, s.ramp(b.noise(s.coords(u, 300.0, v, 2400.0), 1.0, 2, 0.5), 0.42, 0.6)), col=pale, rough=0.92, h=0.8, amount=0.85)
    cav = s.cavity(0.0012, 0.2, 0.7)
    s.layer(cav, col=(0.035, 0.028, 0.022), amount=0.8)
    s.roughen(n_mid, 0.04)
    s.bump(n_fine, 0.2)
    return s.finish(bevel_r=0.0)


def paint_chipped(name, origin, paint_lin, under_lin, rough=0.58, cover=0.40, under_rough=0.6):
    """Old Warden orange on steel (SEAM.md section 8, linear albedo): gone in large ragged patches, more at the
    edges, a thin dark rim of rust round each patch, scuffed and dirty in between."""
    base = MT.from_linear(paint_lin)
    under = MT.from_linear(under_lin)          # SEAM.md section 8: both come from the kit's constants, linear albedo
    s = Stack(name, base, 0.0, rough, origin)
    n_big = s.noise(34, 2, 0.5); n_coast = s.noise(310, 5, 0.7); n_fine = s.noise(1500, 3, 0.5); n_mid = s.noise(420, 4, 0.6)
    edgeW = s.edge(0.0020, 0.002, 0.10)
    cav = s.cavity(0.003, 0.1, 0.55)
    # faded and dirty paint
    s.layer(s.ramp(s.noise(80, 3, 0.5, shift=(0.3, 0.2, 0.5)), 0.4, 0.75), col=tuple(c * 0.66 for c in base), rough=rough + 0.08, amount=0.6)
    s.layer(s.ramp(s.noise(600, 3, 0.5), 0.6, 0.74), col=(0.16, 0.10, 0.07), amount=0.5)
    sc = s.ramp(s.aniso((1, 0.3, 0), 16, 1400, 2), 0.67, 0.71)
    src = s.wsum((n_big, 0.66), (n_coast, 0.26), (n_fine, 0.08), (edgeW, 0.30))
    thr = 0.5 + (0.5 - cover) * 0.42
    s.layer(s.ramp(src, thr - 0.022, thr - 0.008), col=RUST_B, rough=0.85, amount=0.85)        # the rim
    chip = s.mx(s.ramp(src, thr - 0.008, thr + 0.008), s.mul(sc, 0.9))
    s.layer(chip, col=under, metal=1.0, rough=under_rough, h=-1.3)
    # the bare steel is not clean: rust freckles and a brown stain
    s.layer(s.mul(chip, s.ramp(s.noise(240, 4, 0.6, shift=(0.2, 0.2, 0.2)), 0.48, 0.66)), col=RUST_B, metal=0.0, rough=0.85, amount=0.7)
    s.layer(s.mul(chip, s.ramp(s.noise(1900, 2, 0.5), 0.6, 0.68)), col=RUST_D, metal=0.0, rough=0.9, h=-0.5)
    s.layer(s.mul(chip, s.mul(s.edge(0.0006), s.ramp(n_mid, 0.4, 0.6))), col=(0.74, 0.72, 0.68), metal=1.0, rough=0.26)
    s.layer(s.ramp(s.wsum((cav, 1.0), (n_mid, 0.4), -0.2), 0.25, 0.65), col=OIL, metal=0.0, rough=0.6, amount=0.85)
    s.roughen(n_mid, 0.05)
    s.bump(n_fine, 0.15); s.bump(s.noise(700, 4, 0.6), 0.25)
    return s.finish()


def plastic(name, origin=(0, 0, 0), base=(0.60, 0.54, 0.40), rough=0.48):
    """Old cream plastic (the keyed plug and its socket): yellowed, brown in the corners, scuffed pale."""
    s = Stack(name, base, 0.0, rough, origin)
    n_mid = s.noise(420, 4, 0.6); n_fine = s.noise(1500, 3, 0.5)
    cav = s.cavity(0.003, 0.1, 0.55)
    s.layer(s.ramp(s.noise(70, 3, 0.5), 0.35, 0.7), col=(0.50, 0.40, 0.25), amount=0.6)
    s.layer(s.mul(s.edge(0.0006), s.ramp(n_mid, 0.4, 0.62)), col=(0.74, 0.70, 0.60), rough=0.6, amount=0.7)
    s.layer(s.ramp(s.aniso((1, 0, 0.3), 16, 1500, 2), 0.67, 0.71), col=(0.72, 0.68, 0.58), rough=0.62, h=-0.4, amount=0.5)
    s.layer(s.ramp(s.wsum((cav, 1.0), (n_mid, 0.5), -0.25), 0.2, 0.6), col=(0.15, 0.11, 0.075), rough=0.75, amount=0.9)
    s.roughen(n_mid, 0.05); s.bump(n_fine, 0.12)
    return s.finish()


def sleeve(name, origin=(0, 0, 0), base=(0.33, 0.055, 0.045), rough=0.55):
    """The red sleeve of the trigger lead: faded, cracked across where it bends, dark with oil."""
    s = Stack(name, base, 0.0, rough, origin)
    n_mid = s.noise(420, 4, 0.6); n_fine = s.noise(1500, 3, 0.5)
    s.layer(s.ramp(s.noise(60, 3, 0.5), 0.35, 0.7), col=(0.20, 0.045, 0.04), amount=0.7)
    s.layer(s.ramp(s.noise(140, 3, 0.5, shift=(0.2, 0.1, 0.4)), 0.58, 0.78), col=(0.47, 0.17, 0.13), rough=0.7, amount=0.5)
    s.layer(s.ramp(s.aniso(PG.S_, 900, 60, 2), 0.66, 0.72), col=(0.07, 0.03, 0.028), rough=0.7, h=-0.8, amount=0.7)
    s.layer(s.ramp(s.wsum((s.cavity(0.002, 0.1, 0.5), 1.0), (n_mid, 0.5), -0.25), 0.25, 0.6), col=OIL, rough=0.6, amount=0.8)
    s.roughen(n_mid, 0.05); s.bump(n_fine, 0.15)
    return s.finish(bevel_r=0.0)


def ceramic(name, origin=(0, 0, 0)):
    s = Stack(name, (0.70, 0.68, 0.61), 0.0, 0.30, origin)
    n_mid = s.noise(420, 4, 0.6)
    s.layer(s.ramp(s.noise(90, 3, 0.5), 0.4, 0.7), col=(0.56, 0.50, 0.40), rough=0.45, amount=0.6)
    s.layer(s.ramp(s.wsum((s.cavity(0.0025, 0.1, 0.5), 1.0), (n_mid, 0.5), -0.25), 0.2, 0.6), col=(0.12, 0.09, 0.06), rough=0.75, amount=0.9)
    s.layer(s.ramp(s.noise(1300, 2, 0.5), 0.66, 0.72), col=(0.25, 0.19, 0.13), amount=0.6)
    s.bump(n_mid, 0.15)
    return s.finish()


def fluid(name, origin, axis_yz, colour=(0.19, 0.81, 1.0), strength=1.0, x0=-79.2, x1=-42.8):
    """The charge in the cell: a cyan core with slow clouds in it and a darker band at each end where the caps shade
    it. The emission map holds colour x strength x mask (strength 1: the full colour is in the texture)."""
    s = Stack(name, (0.05, 0.30, 0.38), 0.0, 0.2, origin)
    sp = s.sepP()
    n1 = s.noise(260, 3, 0.55); n2 = s.noise(900, 2, 0.5)
    cloud = s.ramp(s.wsum((n1, 0.7), (n2, 0.3)), 0.25, 0.8)
    ends = s.mul(s.ramp(sp['X'], x0 * MM, (x0 + 5) * MM), s.inv(s.ramp(sp['X'], (x1 - 5) * MM, x1 * MM)))
    mask = s.mul(s.add(0.42, s.mul(cloud, 0.58)), s.add(0.5, s.mul(ends, 0.5)))
    s.layer(cloud, col=(0.10, 0.50, 0.60), amount=0.6)
    return s.finish(emit=(colour, strength, mask), bevel_r=0.0)


def cell_glass(name, origin, axis_yz, x0=-80.2, x1=-41.8, r_mid=5.95, band_x=-57.0, band_w=6.5):
    """The cell's glass tube, baked into the atlas with its alpha (px.bake_alpha): old glass under a film of dust and
    finger grease, caked where it meets the two caps, flecked, and one band rubbed clean by a thumb. The inner wall
    is clear. Pistol millimetres."""
    s = Stack(name, (0.40, 0.52, 0.52), 0.0, 0.07, origin)
    b = s.b
    sp = s.sepP()
    dy = s.sub(sp['Y'], axis_yz[0] * MM); dz = s.sub(sp['Z'], axis_yz[1] * MM)
    r = b.math('SQRT', s.add(s.mul(dy, dy), s.mul(dz, dz)))
    outer = s.ramp(r, (r_mid - 0.1) * MM, (r_mid + 0.1) * MM)
    n_mid = s.noise(300, 4, 0.6); n_fine = s.noise(1400, 3, 0.5); n_big = s.noise(70, 3, 0.5)
    xx = sp['X']
    ends = s.mx(s.inv(s.ramp(s.add(xx, s.mul(s.sub(n_mid, 0.5), 0.004)), x0 * MM, (x0 + 7.5) * MM)),
                s.ramp(s.add(xx, s.mul(s.sub(n_mid, 0.5), 0.004)), (x1 - 7.5) * MM, x1 * MM))
    film = s.ramp(s.wsum((n_big, 0.55), (n_mid, 0.45)), 0.25, 0.75)
    streak = s.ramp(s.aniso((0, 1, 0.2), 30, 900, 3), 0.5, 0.7)                 # wiped round the tube
    specks = s.ramp(n_fine, 0.66, 0.72)
    dirt = s.sat(s.wsum((film, 0.16), (ends, 0.80), (streak, 0.08), (specks, 0.22), 0.02))
    band = s.inv(s.ramp(s.add(b.math('ABSOLUTE', s.sub(xx, band_x * MM)), s.mul(s.sub(n_mid, 0.5), 0.0035)), (band_w - 1.2) * MM, (band_w + 0.6) * MM))
    dirt = s.mul(dirt, s.sub(1.0, s.mul(band, 0.88)))
    dirt = s.mul(dirt, outer)
    s.layer(dirt, col=(0.25, 0.215, 0.17), rough=0.72)
    s.layer(s.mul(s.mul(ends, outer), s.ramp(n_mid, 0.3, 0.6)), col=(0.16, 0.13, 0.10), rough=0.8, amount=0.8)
    alpha = s.wsum((dirt, 0.80), (outer, 0.045), 0.035)
    s.bump(s.mul(dirt, n_fine), 0.4)
    return s.finish(bevel_r=0.0, alpha=alpha)


def emitter_glass(name, origin=(0, 0, 0)):
    s = Stack(name, (0.02, 0.026, 0.03), 0.0, 0.10, origin)
    n_mid = s.noise(420, 4, 0.6)
    s.layer(s.ramp(s.noise(120, 3, 0.5), 0.45, 0.7), col=(0.16, 0.14, 0.11), rough=0.6, amount=0.5)
    s.layer(s.ramp(s.wsum((s.cavity(0.003, 0.1, 0.5), 1.0), (n_mid, 0.4), -0.2), 0.2, 0.6), col=(0.10, 0.07, 0.05), rough=0.8, amount=0.9)
    return s.finish(bevel_r=0.0)


# ====================================================================== geometry: strips, bands, the guard
def set_strip(o, n_rings, n_sec, lengths, sec_v, half_w, closed_path=False, closed_sec=True, chunk=0.085, sid=1, weight=None):
    """Write the strip attributes of a swept mesh whose vertex i * n_sec + k is ring i, section point k:
    corner attribute px_st = (u along, v across, half width) in metres for the materials, corner attribute px_uv =
    the unrolled strip in millimetres for the atlas, face attribute px_strip = island id (the atlas cuts the strip
    every `chunk` metres) and optionally px_w (texel weight).
    lengths: arc length at each ring; sec_v: v of each section point (cumulative across; for a closed section one
    more value than points, the last = the perimeter). Caps are left to the projector."""
    me = o.data
    if 'nostrip' in DIAG:
        return o
    if len(me.vertices) != n_rings * n_sec:
        raise RuntimeError('set_strip %s: %d vertices, expected %d x %d' % (o.name, len(me.vertices), n_rings, n_sec))
    for nm, ty, dom in (('px_st', 'FLOAT_VECTOR', 'CORNER'), ('px_uv', 'FLOAT_VECTOR', 'CORNER'), ('px_strip', 'INT', 'FACE')) + ((('px_w', 'FLOAT', 'FACE'),) if weight is not None else ()):
        me.attributes.new(nm, ty, dom)
    # fetch them only now: adding an attribute moves the ones made before it
    st, pu, fid = me.attributes['px_st'], me.attributes['px_uv'], me.attributes['px_strip']
    total = lengths[-1]
    for p in me.polygons:
        vs = [me.loops[li].vertex_index for li in p.loop_indices]
        rings = [v // n_sec for v in vs]; ks = [v % n_sec for v in vs]
        if len(vs) != 4 or len(set(rings)) != 2:
            continue                         # an end cap
        lo, hi = min(rings), max(rings)
        wrap_r = closed_path and hi - lo > 1
        wrap_k = closed_sec and max(ks) - min(ks) > 1
        for li, r, k in zip(p.loop_indices, rings, ks):
            uu = total if (wrap_r and r == lo) else lengths[r]
            vv = sec_v[n_sec] if (wrap_k and k == min(ks)) else sec_v[k]
            st.data[li].vector = (uu, vv, half_w)
            pu.data[li].vector = (uu * 1000.0, vv * 1000.0, 0.0)
        mid = (lengths[hi] + (total if wrap_r else lengths[lo])) / 2
        fid.data[p.index].value = sid * 1000 + int(mid / chunk) + 1
    if weight is not None:
        w = me.attributes['px_w']
        for p in me.polygons:
            w.data[p.index].value = weight
    return o


def _arc(pts, closed=False):
    L = [0.0]
    for a, c in zip(pts, pts[1:]):
        L.append(L[-1] + (Vector(c) - Vector(a)).length)
    if closed:
        L.append(L[-1] + (Vector(pts[0]) - Vector(pts[-1])).length)
    return L


def tube(name, pts, radius, segs=8, mat=None, closed=False, sid=1, chunk=0.085):
    """kit geo.tube_path with the strip attribute (u along the wire, v round it)."""
    o = G.tube_path(name, pts, radius, segs, mat, closed=closed)
    L = _arc(pts, closed)
    per = 2 * math.pi * radius
    set_strip(o, len(pts), segs, L, [per * k / segs for k in range(segs + 1)], per / 2, closed_path=closed, closed_sec=True, chunk=chunk, sid=sid)
    return o


def band(name, s, width, thick, n=48, mat=None, tilt=None, lift=0.1, seed=1, th0=0.0, turns=None, pitch=0.0, peel=0.0,
         wander=0.6, wvar=0.8, tvar=0.12, lap=0.0, cut=1.6, sid=1, across=5, ride=0.0):
    """A strap or a winding of tape laid on the grip by hand (after pgeom.band, same arguments for where it lies).
    turns=None: one turn that laps over its own start by `lap` mm (a strap); turns + pitch: a helical winding whose
    later turns ride on the earlier ones (`ride` = the tape's width less the pitch, mm). wander: the strap drifts
    off its line by up to this many mm; wvar: its width changes by up to this many mm (a hand-cut edge); tvar: the
    thickness changes by this fraction; cut: the ends are cut on the skew by up to this many mm. The section has
    `across` points on each face, with rolled edges. Returns the object."""
    rnd = random.Random(seed)
    strap = turns is None
    tot = (1.0 + lap / 190.0) if strap else turns
    m = int(round(n * tot)) + 1
    # slow random walks along the strap
    def walk(amp, step=7):
        keys = [rnd.uniform(-amp, amp) for _ in range(m // step + 3)]
        out = []
        for k in range(m):
            a = k / step; i = int(a); f = a - i
            f = f * f * (3 - 2 * f)
            out.append(keys[i] * (1 - f) + keys[i + 1] * f)
        return out
    wa = walk(wander); w0v = walk(wvar / 2, 5); w1v = walk(wvar / 2, 5); tv = walk(tvar, 6)
    skew0 = rnd.uniform(-cut, cut); skew1 = rnd.uniform(-cut, cut)
    verts, faces = [], []
    centre = []
    na = across
    er = min(0.12, 0.9 / width)                                # the rolled edge is about 0.9 mm wide
    fs = [0.0, er] + [er + (1 - 2 * er) * j / (na - 3) for j in range(1, na - 3)] + [1.0 - er, 1.0]
    for k in range(m):
        th = 2 * math.pi * k / n + th0
        sc = s + (tilt[0] * math.cos(th - tilt[1]) if tilt else 0.0) + (pitch * k / n if not strap else 0.0) + wa[k]
        lo = -width / 2 + w0v[k]; hi = width / 2 + w1v[k]
        t = thick * (1.0 + tv[k])
        lf = lift
        over = 0.0
        if strap and lap > 0:
            # the tail of the strap rides up over its own start
            start_over = (m - 1) - int(round(n * lap / 190.0))
            if k > start_over - 3:
                f = min(1.0, (k - (start_over - 3)) / 3.0)
                over = (thick + 0.15) * f * f * (3 - 2 * f)
        if peel and not strap and k > m - 7:
            lf = lift + peel * ((k - (m - 7)) / 6.0) ** 2
            lo *= 1.0 - 0.25 * (k - (m - 7)) / 6.0
        ring_top, ring_bot = [], []
        for j in range(na):
            f = fs[j]
            w = lo + (hi - lo) * f
            # rolled edges: the two outer points sit a little lower, the under side a little off the grip
            edge = 1.0 if j in (0, na - 1) else 0.0
            up = lf + over + t * (1.0 - 0.30 * edge)
            dn = lf + over + t * 0.14 * edge
            if not strap and ride > 0:
                # a later turn lies on the one before over the low side of its width
                on_prev = 1.0 if (k >= n) else max(0.0, (k - (n - 4)) / 4.0)
                r = max(0.0, min(1.0, (ride - (w - lo)) / 1.2 + 0.5))
                up += (thick + 0.05) * r * on_prev; dn += (thick + 0.05) * r * on_prev
            # the ends are cut on the skew
            dth = 0.0
            if k == 0:
                dth = skew0 * (f - 0.5) / 30.0
            elif k == m - 1:
                dth = skew1 * (f - 0.5) / 30.0
            a, _ = PG.surf(th + dth, sc + w, up)
            c, _ = PG.surf(th + dth, sc + w, dn)
            ring_top.append(a); ring_bot.append(c)
        verts += ring_top + ring_bot[::-1]
        centre.append(PG.surf(th, sc, lf + over + t)[0])
    ns = 2 * na
    for i in range(m - 1):
        for q in range(ns):
            q2 = (q + 1) % ns
            faces.append((i * ns + q, i * ns + q2, (i + 1) * ns + q2, (i + 1) * ns + q))
    faces.append(tuple(range(ns))[::-1]); faces.append(tuple((m - 1) * ns + q for q in range(ns)))
    o = G.mesh_obj(name, verts, faces, mat, recalc=True)
    # strip attributes. Materials: u along the centreline, v across from the middle (both faces), half width.
    # Atlas: the section unrolled (top, edge, under, edge), the under face its own island at a lower texel weight.
    L = _arc(centre)
    me = o.data
    if 'nostrip' in DIAG:
        return o
    if len(me.vertices) != m * ns:
        raise RuntimeError('band %s: vertices were merged (%d of %d)' % (name, len(me.vertices), m * ns))
    for nm, ty, dom in (('px_st', 'FLOAT_VECTOR', 'CORNER'), ('px_uv', 'FLOAT_VECTOR', 'CORNER'), ('px_strip', 'INT', 'FACE'), ('px_w', 'FLOAT', 'FACE')):
        me.attributes.new(nm, ty, dom)
    st, pu, fid, wt = me.attributes['px_st'], me.attributes['px_uv'], me.attributes['px_strip'], me.attributes['px_w']
    hw = width / 2 * MM
    secv = [(-width / 2 + width * f) * MM for f in fs]
    secv = secv + secv[::-1]                                   # the under face runs back
    roll = [width * f for f in fs]
    roll = roll + [width + thick + width * f for f in fs] + [2 * width + 2 * thick]      # mm
    chunk = 0.085
    for p in me.polygons:
        vs = [me.loops[li].vertex_index for li in p.loop_indices]
        rings = [v // ns for v in vs]; ks = [v % ns for v in vs]
        if len(vs) != 4 or len(set(rings)) != 2:
            continue
        kk = sorted(set(ks))
        closing = kk == [0, ns - 1]
        under = (not closing) and min(kk) >= na
        for li, r, k in zip(p.loop_indices, rings, ks):
            st.data[li].vector = (L[r], secv[k], hw)
            pu.data[li].vector = (L[r] * 1000.0, roll[ns] if (closing and k == 0) else roll[k], 0.0)
        mid = (L[min(rings)] + L[max(rings)]) / 2
        kind = 3 if closing else (2 if under else 1)
        fid.data[p.index].value = sid * 1000 + kind * 100 + int(mid / chunk) + 1
        wt.data[p.index].value = 0.55 if under else 1.0
    return o


def forged_strap(name, pts, width, thick, normal_fn, mat=None, r=1.3 * MM, seg=3, flare=None, sid=1, crown=0.25 * MM):
    """A strap of forged section swept along a polyline (the trigger guard): a rounded rectangle `width` across and
    `thick` deep whose outer face lies on the path (as kit geo.band_path with offset=-thick), slightly crowned.
    flare: fn(t 0..1) -> width factor (the roots of a guard widen into the frame)."""
    Pp = [Vector(p) for p in pts]
    n = len(Pp)
    L = _arc(Pp)
    rings = []
    for i in range(n):
        t = (Pp[min(i + 1, n - 1)] - Pp[max(i - 1, 0)]).normalized()
        nn = Vector(normal_fn(Pp[i], t)); nn = (nn - t * t.dot(nn)).normalized()
        side = t.cross(nn)
        w = width * (flare(L[i] / L[-1]) if flare else 1.0)
        rr = min(r, thick * 0.45, w * 0.45)
        ring = []
        for q, (cx, cy, a0) in enumerate(((w / 2 - rr, -rr, 0), (-w / 2 + rr, -rr, 90), (-w / 2 + rr, -thick + rr, 180), (w / 2 - rr, -thick + rr, 270))):
            for k in range(seg + 1):
                a = math.radians(a0 + 90 * k / seg)
                x = cx + rr * math.cos(a); yv = cy + rr * math.sin(a)
                if q < 2 and k == (seg if q == 0 else 0):  # the outer face is crowned across its width
                    yv -= crown * (2 * x / w) ** 2
                elif q >= 2 and k == (seg if q == 2 else 0):
                    yv += crown * (2 * x / w) ** 2
                ring.append(Pp[i] + side * x + nn * yv)
            if q == 0:
                ring.append(Pp[i])
            elif q == 2:
                ring.append(Pp[i] - nn * thick)
        rings.append(ring)
    o = G.loft(name, rings, mat, caps=(True, True), closed=True, smooth=True)
    return o


# ====================================================================== the atlas
def unwrap(objs, size, weights=None, angle=58.0, margin_px=5.0, shape='AABB', align=False, **kw):
    """kit bake.unwrap with three additions: faces that carry px_strip take their unrolled strip UVs (px_st) instead
    of a projection, cut into the islands px_strip names; faces with px_w get that texel weight (times the object's
    weight); passthrough faces whose material has 'px_alpha' keep full size (the cell glass is baked for its dirt).
    align: the kit's option (since 21:08), every island turned to its smallest bounding rectangle before packing.
    Same call and result as the kit's function, so it is patched in for Family.finish()."""
    import bake as BK
    objs = [o for o in objs if o.type == 'MESH' and len(o.data.polygons)]
    strips = {}
    for o in objs:
        me = o.data
        if me.users > 1:
            o.data = me = me.copy()
        a = me.attributes.get('px_uv'); f = me.attributes.get('px_strip'); w = me.attributes.get('px_w')
        info = {}
        if a is not None and f is not None:
            st = np.zeros(len(me.loops) * 3, np.float32); a.data.foreach_get('vector', st)
            fi = np.zeros(len(me.polygons), np.int32); f.data.foreach_get('value', fi)
            info['st'] = st.reshape(-1, 3); info['id'] = fi
        if w is not None:
            fw = np.zeros(len(me.polygons), np.float32); w.data.foreach_get('value', fw)
            info['w'] = fw
        strips[o.name] = info
        while len(me.uv_layers) > 0:
            me.uv_layers.remove(me.uv_layers[0])
        me.uv_layers.new(name='UVMap')
    def select(obs):
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
    select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    n_strip = 0
    for o in objs:
        info = strips[o.name]
        if 'id' not in info:
            continue
        me = o.data
        uv = me.uv_layers.active.data
        ids = info['id']; st = info['st']
        for p in me.polygons:
            i = int(ids[p.index])
            if i <= 0:
                continue
            # islands that are neighbours on the mesh must not share UVs: neighbours differ in chunk or in kind
            ox = (i % 7) * 450.0 + ((i // 100) % 10) * 3300.0
            for li in p.loop_indices:
                uv[li].uv = (float(st[li][0]) + ox, float(st[li][1]))
            n_strip += 1
    select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    for o in objs:
        f = (weights or {}).get(o.name, 1.0)
        me = o.data
        uv = me.uv_layers.active.data
        skip = [bool(m and m.get('passthrough', 0) and not m.get('px_alpha', 0)) for m in me.materials] or [False]
        fw = strips[o.name].get('w')
        for p in me.polygons:
            k = 0.02 if skip[min(p.material_index, len(skip) - 1)] else f
            if fw is not None and fw[p.index] > 0:
                k *= float(fw[p.index])
            if k != 1.0:
                for li in p.loop_indices:
                    uv[li].uv = uv[li].uv * k
        if align and hasattr(BK, '_align_islands'):
            BK._align_islands(me)
    select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    m = min(margin_px / size, 0.0025)
    try:
        bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=m, shape_method=shape)
    except TypeError:
        bpy.ops.uv.pack_islands(rotate=True, margin=m)
    bpy.ops.object.mode_set(mode='OBJECT')
    out = {}
    fill = 0.0
    for o in objs:
        me = o.data
        uv = me.uv_layers.active.data
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
    return {'size': size, 'fill': round(fill, 3), 'objects': out, 'strip_faces': n_strip}


# ====================================================================== kit patches for this family's bake
def bake_alpha(objs, res, size, spp):
    """After the kit's bake: bake the alpha of the glass materials (made with finish(alpha=...)) and put it in the
    alpha channel of the colour atlas. Every other texel gets the mean alpha of the glass, so no opaque fringe
    bleeds into the glass at any mip (the opaque material does not read alpha)."""
    import bake as BK
    gobjs = [o for o in objs if o.type == 'MESH' and any(sl.material and sl.material.get('px_glass') for sl in o.material_slots)]
    if not gobjs:
        return None
    img = BK._new_img('_b_alpha', size, True)
    black = bpy.data.materials.new('_px_black'); black.use_nodes = True
    nt = black.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0, 0, 0, 1); nt.links.new(em.outputs[0], out.inputs['Surface'])
    tg = nt.nodes.new('ShaderNodeTexImage'); tg.image = img; nt.nodes.active = tg
    saved = {}
    gm = []
    for o in gobjs:
        saved[o.name] = [sl.material for sl in o.material_slots]
        for sl in o.material_slots:
            if sl.material is not None and sl.material.get('px_glass'):
                if sl.material not in gm:
                    gm.append(sl.material)
            else:
                sl.material = black
    BK._bake_pass(gobjs, gm, 'EMIT', 'alpha', img, max(spp, 16))
    for o in gobjs:
        for sl, m in zip(o.material_slots, saved[o.name]):
            sl.material = m
    a = BK._arr(img, size)
    glass = (a[..., 1] > 0.5) & (a[..., 3] > 0.5)
    if not glass.any():
        BK.log('bake_alpha: no glass texels'); return None
    al = a[..., 0].copy()
    mean = float(al[glass].mean())
    full = np.full((size, size), mean, np.float32)
    full[glass] = al[glass]
    filled = glass.copy()
    for _ in range(12):                        # grow the glass alpha into its gutter
        acc = np.zeros_like(full); cnt = np.zeros(full.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            sf = np.roll(np.roll(filled, dy, 0), dx, 1)
            acc += np.roll(np.roll(np.where(filled, full, 0.0), dy, 0), dx, 1) * sf; cnt += sf
        new = (~filled) & (cnt > 0)
        full[new] = acc[new] / cnt[new]
        filled |= new
    col = res['color']
    c = BK._arr(col, size)
    c[..., 3] = np.clip(full, 0.0, 1.0)
    col.pixels.foreach_set(c.ravel())
    col.save()
    bpy.data.images.remove(img)
    bpy.data.materials.remove(black)
    st = {'glass_texels': int(glass.sum()), 'alpha_min': round(float(al[glass].min()), 3), 'alpha_max': round(float(al[glass].max()), 3), 'alpha_mean': round(mean, 3)}
    BK.log('glass alpha baked', st)
    return st


def install(F):
    """Patch the kit's unwrap, bake and assign_runtime for this build (the kit's files are not edited):
    strip UVs and face weights in the atlas; the glass alpha in the colour atlas; a blended runtime material for the
    glass faces on the same atlas; emission strength 1 on the runtime emissive material."""
    import bake as BK
    kit_bake, kit_assign = BK.bake, BK.assign_runtime
    BK.unwrap = unwrap
    state = {}

    def bake(objs, family, outdir, size=2048, spp=24, **kw):
        res = kit_bake(objs, family, outdir, size, spp, **kw)
        st = bake_alpha(objs, res, size, spp)
        if st:
            res['stats']['glass_alpha'] = st
        return res

    def assign_runtime(objs, family, tex):
        glass = {}
        for o in objs:
            if o.type != 'MESH':
                continue
            flags = [bool(m and m.get('px_glass')) for m in o.data.materials]
            idx = [p.index for p in o.data.polygons if flags and flags[min(p.material_index, len(flags) - 1)]]
            if idx:
                glass[o.name] = idx
        count = kit_assign(objs, family, tex)
        em = bpy.data.materials.get('M_%s_emissive' % family)
        if em:
            em.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.0
        if glass:
            g = BK._runtime_mat('glass_cell', tex, False)
            nt = g.node_tree
            bs = nt.nodes['Principled BSDF']
            tb = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image == tex['color'])
            nt.links.new(tb.outputs['Alpha'], bs.inputs['Alpha'])
            try:
                g.surface_render_method = 'BLENDED'
            except Exception:
                pass
            try:
                g.blend_method = 'BLEND'
            except Exception:
                pass
            g.use_backface_culling = True
            g['px_glass'] = 1
            moved = 0
            for o in objs:
                if o.name not in glass:
                    continue
                me = o.data
                me.materials.append(g)
                gi = len(me.materials) - 1
                for i in glass[o.name]:
                    p = me.polygons[i]
                    old = me.materials[p.material_index].name
                    count[old] = count.get(old, 0) - (len(p.vertices) - 2)
                    p.material_index = gi
                    moved += len(p.vertices) - 2
            count['glass_cell'] = moved
        return count

    kit_export = BK.export_glb

    def export_glb(path, objs, animations=False):
        # A --nobake export carries the authoring materials. The glTF exporter walks their node trees and keeps what
        # it finds in its own caches; with the px trees that ended in a crash when Blender quit (20 Nov, exit code
        # 139 after every file was written). Flat stand-ins go on for the export and come off again.
        swapped, stand = [], {}
        for o in objs:
            if o.type != 'MESH':
                continue
            for sl in o.material_slots:
                m = sl.material
                if m is not None and m.get('px') and not m.get('passthrough'):
                    if m.name not in stand:
                        sm = bpy.data.materials.new(m.name + '_flat'); sm.use_nodes = True
                        pb = sm.node_tree.nodes['Principled BSDF']
                        f = list(m.get('px_flat', (0.4, 0.4, 0.4, 0.0, 0.5)))
                        pb.inputs['Base Color'].default_value = (f[0], f[1], f[2], 1.0)
                        pb.inputs['Metallic'].default_value = f[3]; pb.inputs['Roughness'].default_value = f[4]
                        stand[m.name] = sm
                    swapped.append((o.name, sl.slot_index, m.name)); sl.material = stand[m.name]
        try:
            return kit_export(path, objs, animations)
        finally:
            for on, si, mn in swapped:
                bpy.data.objects[on].material_slots[si].material = bpy.data.materials[mn]
            for sm in stand.values():
                bpy.data.materials.remove(sm)

    BK.bake = bake
    BK.assign_runtime = assign_runtime
    if 'kitexport' not in DIAG:
        BK.export_glb = export_glb
    return state


def hand_textures(tex, outdir, family, size_to=2048):
    """The in-hand copy's own texture set: the baked atlas reduced to size_to (box filter in linear light, normals
    renormalised). Returns {'color': image, ...} or None when the bake is already that small. The caller points the
    runtime materials at these images for the merged export and back afterwards."""
    import bake as BK
    out = {}
    for k in ('color', 'normal', 'orm', 'emit'):
        im = tex.get(k)
        if im is None:
            continue
        w = im.size[0]
        if w <= size_to:
            return None
        f = w // size_to
        a = np.empty(w * w * 4, np.float32); im.pixels.foreach_get(a)
        a = a.reshape(w, w, 4)
        srgb_img = k in ('color', 'emit')
        rgb = a[..., :3]
        if srgb_img:
            rgb = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        elif k == 'normal':
            rgb = rgb * 2.0 - 1.0
        small = rgb.reshape(size_to, f, size_to, f, 3).mean(axis=(1, 3))
        al = a[..., 3].reshape(size_to, f, size_to, f).mean(axis=(1, 3))
        if srgb_img:
            small = np.where(small <= 0.0031308, small * 12.92, 1.055 * np.power(np.maximum(small, 1e-8), 1 / 2.4) - 0.055)
        elif k == 'normal':
            ln = np.maximum(np.sqrt((small ** 2).sum(-1, keepdims=True)), 1e-6)
            small = small / ln * 0.5 + 0.5
        del a, rgb
        path = os.path.join(outdir, 'tex', '%s_hand_%s.png' % (family, k))
        out[k] = BK._save('%s_hand_%s' % (family, k), small.astype(np.float32), path, size_to, not srgb_img, alpha=al.astype(np.float32))
    return out


# ====================================================================== bisecting (work/diag.sh): PX_DIAG=only,yes:steel ...
def _diagwrap(fn):
    def w(name, *a, **k):
        if ('no:' + fn.__name__) in DIAG or ('only' in DIAG and ('yes:' + fn.__name__) not in DIAG):
            if fn.__name__ == 'cell_glass':
                return MT.passthrough(name, (0.55, 0.82, 0.86), alpha=0.16, rough=0.05)
            return MT.make(name + '_diag', (0.5, 0.5, 0.5), 0.0, 0.5)
        return fn(name, *a, **k)
    return w


if DIAG:
    for _f in (steel, rusty_steel, bright_steel, brass, copper, wood, leather, cloth, paint_chipped, plastic, sleeve, ceramic, fluid, emitter_glass, cell_glass):
        globals()[_f.__name__] = _diagwrap(_f)
