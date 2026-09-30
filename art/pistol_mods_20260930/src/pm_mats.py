# Procedural authoring materials for the pistol mods (Cycles). They are baked into one atlas later; every material
# exposes its channels through named nodes so the baker can route them to an Emission shader:
#   'CH_base' (colour), 'CH_metal', 'CH_rough', 'CH_emit' (colour, black when not emissive); normal comes from 'BUMP'.
import bpy, math

AXIS_Y0, AXIS_Z0 = 0.00075, 0.05885  # barrel bore axis in the metric frame


def srgb(c):
    def f(x):
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return tuple(f(x) for x in c)


class NB:
    def __init__(self, mat):
        self.nt = mat.node_tree
        self.x = -1600

    def n(self, t, **kw):
        node = self.nt.nodes.new(t)
        node.location = (self.x, 0)
        self.x += 30
        for k, v in kw.items():
            setattr(node, k, v)
        return node

    def l(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        m = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.l(v, m.inputs[i])
        return m.outputs[0]

    def vmath(self, op, a, b=None):
        m = self.n('ShaderNodeVectorMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                m.inputs[i].default_value = v
            else:
                self.l(v, m.inputs[i])
        return m.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else m.outputs['Vector']

    def mixc(self, fac, a, b):
        m = self.n('ShaderNodeMix', data_type='RGBA', blend_type='MIX')
        m.clamp_factor = True
        for sock, v in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(v, (tuple, list)):
                sock.default_value = tuple(v) + ((1.0,) if len(v) == 3 else ())
            elif isinstance(v, (int, float)):
                sock.default_value = v
            else:
                self.l(v, sock)
        return m.outputs[2]

    def mixf(self, fac, a, b):
        m = self.n('ShaderNodeMix', data_type='FLOAT')
        m.clamp_factor = True
        for sock, v in ((m.inputs[0], fac), (m.inputs[2], a), (m.inputs[3], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            else:
                self.l(v, sock)
        return m.outputs[0]

    def ramp(self, v, a, b):
        """smooth remap of v from [a,b] to [0,1]"""
        m = self.n('ShaderNodeMapRange', clamp=True, interpolation_type='SMOOTHSTEP')
        self.l(v, m.inputs['Value']) if not isinstance(v, (int, float)) else None
        m.inputs['From Min'].default_value = a
        m.inputs['From Max'].default_value = b
        return m.outputs['Result']

    def noise(self, vec, scale, detail=4, rough=0.55, dim='3D'):
        t = self.n('ShaderNodeTexNoise', noise_dimensions=dim)
        t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = detail
        t.inputs['Roughness'].default_value = rough
        self.l(vec, t.inputs['Vector'])
        return t.outputs['Fac']

    def value(self, v):
        n = self.n('ShaderNodeValue'); n.outputs[0].default_value = v
        return n.outputs[0]

    def rgb(self, c):
        n = self.n('ShaderNodeRGB'); n.outputs[0].default_value = tuple(c) + (1,)
        return n.outputs[0]


def make(name, base, metal, rough, var=0.08, edge=None, dirt=None, rust=None, bumps=(), emit=None, edge_width=0.0007,
         rough_var=0.08, grime=0.35, heat=None, bevel_r=0.00045, stripe=None):
    """Layered hard-surface material.
    edge: (colour, metal, rough, amount) worn/bare edges; dirt: (colour, rough, amount) cavity grime;
    rust: (colour, amount); bumps: list of (kind, params...); emit: (colour, strength, mask) mask in {'all', 'crystal'}"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    b = NB(m)
    out = b.n('ShaderNodeOutputMaterial'); out.name = 'OUT'
    bsdf = b.n('ShaderNodeBsdfPrincipled'); bsdf.name = 'BSDF'
    tc = b.n('ShaderNodeTexCoord')
    P = tc.outputs['Object']
    geo = b.n('ShaderNodeNewGeometry')
    # --- masks
    n_big = b.noise(P, 90, 5, 0.6)
    n_mid = b.noise(P, 420, 6, 0.6)
    n_fine = b.noise(P, 1500, 3, 0.5)
    bev = b.n('ShaderNodeBevel', samples=8); bev.inputs['Radius'].default_value = edge_width
    edge_raw = b.math('SUBTRACT', 1.0, b.vmath('DOT_PRODUCT', bev.outputs['Normal'], geo.outputs['Normal']))
    edgem = b.ramp(edge_raw, 0.004, 0.05)
    ao = b.n('ShaderNodeAmbientOcclusion', only_local=True, samples=8)
    ao.inputs['Distance'].default_value = 0.004
    cav = b.ramp(b.math('SUBTRACT', 1.0, ao.outputs['AO']), 0.12, 0.6)
    # wear = edge broken up by noise
    wear = b.math("MULTIPLY", edgem, b.ramp(b.math('ADD', n_mid, b.math('MULTIPLY', n_fine, 0.35)), 0.38, 0.62), clamp=True)
    # --- base colour
    col = b.rgb(srgb(base))
    varf = b.math('MULTIPLY', b.math('SUBTRACT', n_big, 0.5), var * 2)
    col = b.mixc(b.math('ADD', 0.5, varf), (0, 0, 0), (1, 1, 1))  # 0.5 +- var
    bright = b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); bright.clamp_factor = True
    bright.inputs[0].default_value = 1.0
    bright.inputs[6].default_value = srgb(base) + (1,)
    b.l(b.mixc(b.math('ADD', 0.5, varf), (0.8, 0.8, 0.8, 1), (1.2, 1.2, 1.2, 1)), bright.inputs[7])
    col = bright.outputs[2]
    metal_s = b.value(metal)
    rough_s = b.math('ADD', rough, b.math('MULTIPLY', b.math('SUBTRACT', n_mid, 0.5), rough_var * 2))
    if heat:  # temper colours toward the muzzle (x runs negative toward the crown)
        sepx = b.n('ShaderNodeSeparateXYZ'); b.l(P, sepx.inputs[0])
        mr = b.n('ShaderNodeMapRange', clamp=True)
        b.l(sepx.outputs['X'], mr.inputs['Value'])
        mr.inputs['From Min'].default_value = heat[0]; mr.inputs['From Max'].default_value = heat[1]
        f = b.math('ADD', mr.outputs['Result'], b.math('MULTIPLY', b.math('SUBTRACT', n_mid, 0.5), 0.35))
        cr = b.n('ShaderNodeValToRGB')
        els = cr.color_ramp.elements
        stops = [(0.0, (0.58, 0.57, 0.54)), (0.3, (0.80, 0.66, 0.40)), (0.55, (0.62, 0.36, 0.22)), (0.78, (0.34, 0.28, 0.52)), (1.0, (0.36, 0.52, 0.70))]
        els[0].position = stops[0][0]; els[0].color = srgb(stops[0][1]) + (1,)
        els[1].position = stops[-1][0]; els[1].color = srgb(stops[-1][1]) + (1,)
        for pos, c in stops[1:-1]:
            e = els.new(pos); e.color = srgb(c) + (1,)
        b.l(f, cr.inputs['Fac'])
        col = b.mixc(b.math('MULTIPLY', b.ramp(f, 0.05, 0.3), 0.8), col, cr.outputs['Color'])
    if stripe:  # printed polarity stripe with dashes along a cylinder (axis X): (yc, zc, angle, half_width, colour, dash colour)
        sp = b.n('ShaderNodeSeparateXYZ'); b.l(P, sp.inputs[0])
        ang = b.math('ARCTAN2', b.math('SUBTRACT', sp.outputs['Z'], stripe[1]), b.math('SUBTRACT', sp.outputs['Y'], stripe[0]))
        da = b.math('ABSOLUTE', b.math('SUBTRACT', ang, stripe[2]))
        smask = b.math('SUBTRACT', 1.0, b.ramp(da, stripe[3] - 0.03, stripe[3]))
        col = b.mixc(b.math('MULTIPLY', smask, 0.9), col, srgb(stripe[4]))
        dash = b.math('MULTIPLY', b.ramp(b.math('SINE', b.math('MULTIPLY', sp.outputs['X'], 900.0)), 0.55, 0.65),
                      b.math('SUBTRACT', 1.0, b.ramp(da, 0.05, 0.08)))
        col = b.mixc(b.math('MULTIPLY', dash, smask), col, srgb(stripe[5]))
    if rust:
        rmask = b.ramp(b.math('ADD', b.math('MULTIPLY', n_big, 0.8), b.math('MULTIPLY', cav, 0.35)), 0.62 - rust[1] * 0.25, 0.72 - rust[1] * 0.25)
        rmask = b.math('MULTIPLY', rmask, b.ramp(n_fine, 0.3, 0.7), clamp=True)
        col = b.mixc(rmask, col, srgb(rust[0]))
        metal_s = b.mixf(rmask, metal_s, 0.0)
        rough_s = b.mixf(rmask, rough_s, 0.88)
    if edge:
        wf = b.math('MULTIPLY', wear, edge[3], clamp=True)
        col = b.mixc(wf, col, srgb(edge[0]))
        metal_s = b.mixf(wf, metal_s, edge[1])
        rough_s = b.mixf(wf, rough_s, edge[2])
    if dirt:
        dmask = b.math('MULTIPLY', b.math('ADD', cav, b.math('MULTIPLY', b.ramp(n_big, 0.55, 0.8), grime)), dirt[2], clamp=True)
        col = b.mixc(dmask, col, srgb(dirt[0]))
        metal_s = b.mixf(dmask, metal_s, 0.0)
        rough_s = b.mixf(dmask, rough_s, dirt[1])
    # --- height / bump
    h = b.math('MULTIPLY', n_fine, 0.15)
    for spec in bumps:
        kind = spec[0]
        if kind == 'noise':
            h = b.math('ADD', h, b.math('MULTIPLY', b.noise(P, spec[1], 6, 0.6), spec[2]))
        elif kind == 'lathe':  # circumferential tool marks along an axis vector
            w = b.n('ShaderNodeTexWave', wave_type='BANDS', bands_direction=spec[1])
            w.inputs['Scale'].default_value = spec[2]
            w.inputs['Distortion'].default_value = 1.5
            w.inputs['Detail'].default_value = 2
            b.l(P, w.inputs['Vector'])
            h = b.math('ADD', h, b.math('MULTIPLY', w.outputs['Fac'], spec[3]))
        elif kind == 'stipple':
            v = b.n('ShaderNodeTexVoronoi', feature='F1')
            v.inputs['Scale'].default_value = spec[1]
            b.l(P, v.inputs['Vector'])
            h = b.math('ADD', h, b.math('MULTIPLY', b.ramp(v.outputs['Distance'], 0.0, 0.5), spec[2]))
        elif kind == 'knurl':  # diamond knurl around the barrel axis (x along axis)
            sep = b.n('ShaderNodeSeparateXYZ'); b.l(P, sep.inputs[0])
            th = b.math('ARCTAN2', b.math('SUBTRACT', sep.outputs['Z'], AXIS_Z0), b.math('SUBTRACT', sep.outputs['Y'], AXIS_Y0))
            k1 = spec[1]; k2 = spec[2]
            a1 = b.math('SINE', b.math('ADD', b.math('MULTIPLY', th, k1), b.math('MULTIPLY', sep.outputs['X'], k2)))
            a2 = b.math('SINE', b.math('SUBTRACT', b.math('MULTIPLY', th, k1), b.math('MULTIPLY', sep.outputs['X'], k2)))
            kn = b.math('MULTIPLY', b.math('ABSOLUTE', a1), b.math('ABSOLUTE', a2))
            h = b.math('ADD', h, b.math('MULTIPLY', kn, spec[3]))
        elif kind == 'clampslots':  # worm-drive band perforations: spec = (N around, x centre, half length)
            sep = b.n('ShaderNodeSeparateXYZ'); b.l(P, sep.inputs[0])
            th = b.math('ARCTAN2', b.math('SUBTRACT', sep.outputs['Z'], AXIS_Z0), b.math('SUBTRACT', sep.outputs['Y'], AXIS_Y0))
            f = b.math('FRACT', b.math('MULTIPLY', th, spec[1] / (2 * math.pi)))
            slot_a = b.math('MULTIPLY', b.ramp(f, 0.1, 0.16), b.math('SUBTRACT', 1.0, b.ramp(f, 0.5, 0.56)))
            dx = b.math('ABSOLUTE', b.math('SUBTRACT', sep.outputs['X'], spec[2]))
            slot_b = b.math('SUBTRACT', 1.0, b.ramp(dx, spec[3] - 0.0003, spec[3]))
            h = b.math('SUBTRACT', h, b.math('MULTIPLY', b.math('MULTIPLY', slot_a, slot_b), spec[4]))
        elif kind == 'helix':  # overlapping strip wrap around an axis: (origin, axis, e1, pitch, strength)
            o_, ax, e1, pitch, st = spec[1:]
            e2 = (ax[1] * e1[2] - ax[2] * e1[1], ax[2] * e1[0] - ax[0] * e1[2], ax[0] * e1[1] - ax[1] * e1[0])
            d = b.vmath('SUBTRACT', P, o_)
            al = b.vmath('DOT_PRODUCT', d, ax)
            th = b.math('ARCTAN2', b.vmath('DOT_PRODUCT', d, e2), b.vmath('DOT_PRODUCT', d, e1))
            ph = b.math('FRACT', b.math('ADD', b.math('DIVIDE', al, pitch), b.math('DIVIDE', th, 2 * math.pi)))
            saw = b.math('MULTIPLY', b.ramp(ph, 0.0, 0.92), b.math('SUBTRACT', 1.0, b.ramp(ph, 0.94, 1.0)))
            h = b.math('ADD', h, b.math('MULTIPLY', saw, st))
            # darker seam line at the overlap edge
            seam = b.math('SUBTRACT', 1.0, b.ramp(ph, 0.9, 0.99))
            col = b.mixc(b.math('MULTIPLY', b.math('SUBTRACT', 1.0, seam), 0.5), col, (0.012, 0.011, 0.01))
        elif kind == 'brushed':
            mp = b.n('ShaderNodeMapping'); mp.inputs['Scale'].default_value = spec[1]
            b.l(P, mp.inputs['Vector'])
            h = b.math('ADD', h, b.math('MULTIPLY', b.noise(mp.outputs['Vector'], 60, 4, 0.6), spec[2]))
    bump = b.n('ShaderNodeBump'); bump.name = 'BUMP'
    if bevel_r > 0:
        bvn = b.n('ShaderNodeBevel', samples=16); bvn.inputs['Radius'].default_value = bevel_r
        b.l(bvn.outputs['Normal'], bump.inputs['Normal'])
    bump.inputs['Strength'].default_value = 1.0
    bump.inputs['Distance'].default_value = 0.00015
    b.l(h, bump.inputs['Height'])
    # --- emission
    if emit:
        ecol = b.rgb(srgb(emit[0]))
        if emit[2] == 'crystal':  # facet brightness variation, brighter toward centre-lines
            f = b.ramp(b.noise(P, 700, 2, 0.5), 0.3, 0.8)
            ecol = b.mixc(b.math('ADD', 0.35, b.math('MULTIPLY', f, 0.65)), (0, 0, 0), ecol)
        elif emit[2] == 'radial':  # optic: bright centre falling off toward the rim
            sep = b.n('ShaderNodeSeparateXYZ'); b.l(P, sep.inputs[0])
            dy = b.math('SUBTRACT', sep.outputs['Y'], AXIS_Y0); dz = b.math('SUBTRACT', sep.outputs['Z'], AXIS_Z0)
            rr = b.math('SQRT', b.math('ADD', b.math('MULTIPLY', dy, dy), b.math('MULTIPLY', dz, dz)))
            f = b.math('SUBTRACT', 1.0, b.ramp(rr, 0.0015, 0.0074))
            ecol = b.mixc(b.math('ADD', 0.08, b.math('MULTIPLY', f, 0.92)), (0, 0, 0), ecol)
        elif emit[2] == 'cavity':  # glowing deeper inside vents
            ecol = b.mixc(b.math('ADD', 0.25, b.math('MULTIPLY', cav, 0.75)), (0, 0, 0), ecol)
        # the tap carries colour x (strength / 8) so one normalised emission map keeps the relative intensities
        sc8 = b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); sc8.clamp_factor = True
        sc8.inputs[0].default_value = 1.0
        b.l(ecol, sc8.inputs[6]); sc8.inputs[7].default_value = (emit[1] / 8.0,) * 3 + (1,)
        emit_s = sc8.outputs[2]
        emit_str = 8.0
    else:
        emit_s = b.rgb((0, 0, 0))
        emit_str = 0.0
    # channel taps
    for nm, sock in (('CH_base', col), ('CH_metal', metal_s), ('CH_rough', rough_s), ('CH_emit', emit_s)):
        r = b.n('NodeReroute'); r.name = nm; b.l(sock, r.inputs[0])
    b.l(nt.nodes['CH_base'].outputs[0], bsdf.inputs['Base Color'])
    b.l(nt.nodes['CH_metal'].outputs[0], bsdf.inputs['Metallic'])
    b.l(nt.nodes['CH_rough'].outputs[0], bsdf.inputs['Roughness'])
    b.l(nt.nodes['CH_emit'].outputs[0], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = emit_str
    b.l(bump.outputs['Normal'], bsdf.inputs['Normal'])
    b.l(bsdf.outputs[0], out.inputs['Surface'])
    m['emissive'] = 1 if emit else 0
    return m


def library():
    L = {}
    DIRT = ((0.16, 0.12, 0.09), 0.85, 0.75)
    DUST = ((0.42, 0.35, 0.27), 0.9, 0.55)
    L['steel'] = make('steel', (0.40, 0.38, 0.35), 1.0, 0.42, edge=((0.66, 0.63, 0.58), 1.0, 0.24, 1.0), dirt=DIRT,
                      rust=((0.42, 0.21, 0.09), 0.35), bumps=[('noise', 900, 0.25)])
    L['steel_dark'] = make('steel_dark', (0.17, 0.16, 0.155), 0.85, 0.46, edge=((0.55, 0.53, 0.5), 1.0, 0.26, 1.0), dirt=DIRT,
                           bumps=[('noise', 900, 0.2)])
    L['alloy'] = make('alloy', (0.60, 0.59, 0.56), 1.0, 0.30, var=0.05, edge=((0.78, 0.77, 0.74), 1.0, 0.18, 0.8), dirt=DIRT,
                      bumps=[('lathe', 'X', 800, 0.12), ('noise', 1200, 0.15)])
    L['alloy_heat'] = make('alloy_heat', (0.58, 0.57, 0.54), 1.0, 0.32, var=0.07, edge=((0.78, 0.77, 0.74), 1.0, 0.18, 0.9), dirt=DIRT,
                           bumps=[('lathe', 'X', 800, 0.12), ('noise', 1200, 0.15)], heat=(-0.160, -0.1755), grime=0.5)
    L['alloy_grip'] = make('alloy_grip', (0.58, 0.57, 0.545), 1.0, 0.33, var=0.05, edge=((0.78, 0.77, 0.74), 1.0, 0.18, 0.8),
                           dirt=DIRT, bumps=[('brushed', (1, 1, 12), 0.18)])
    L['anodized'] = make('anodized', (0.13, 0.135, 0.14), 1.0, 0.38, var=0.06, edge=((0.62, 0.61, 0.58), 1.0, 0.22, 1.0),
                         dirt=DUST, bumps=[('noise', 1400, 0.12)])
    L['paint_orange'] = make('paint_orange', (0.58, 0.29, 0.11), 0.0, 0.58, var=0.1, edge=((0.52, 0.50, 0.46), 1.0, 0.3, 1.0),
                             dirt=DIRT, rust=((0.36, 0.17, 0.07), 0.25), bumps=[('noise', 700, 0.3)], edge_width=0.0009)
    L['paint_olive'] = make('paint_olive', (0.25, 0.25, 0.19), 0.0, 0.62, var=0.1, edge=((0.52, 0.50, 0.46), 1.0, 0.3, 1.0),
                            dirt=DIRT, bumps=[('noise', 700, 0.3)], edge_width=0.0009)
    L['brass'] = make('brass', (0.80, 0.63, 0.38), 1.0, 0.34, var=0.08, edge=((0.93, 0.80, 0.55), 1.0, 0.2, 0.8),
                      dirt=((0.20, 0.15, 0.08), 0.7, 0.8))
    L['stainless_plain'] = make('stainless_plain', (0.66, 0.65, 0.63), 1.0, 0.26, var=0.04, edge=((0.8, 0.8, 0.78), 1.0, 0.15, 0.6),
                                dirt=DIRT, bumps=[('noise', 1500, 0.12)])
    L['brass_knurl'] = make('brass_knurl', (0.78, 0.61, 0.37), 1.0, 0.36, var=0.08, edge=((0.93, 0.80, 0.55), 1.0, 0.2, 0.8),
                            dirt=((0.20, 0.15, 0.08), 0.7, 0.9), bumps=[('knurl', 36, 3900, 0.9)])
    L['lens_glow'] = make('lens_glow', (0.03, 0.06, 0.07), 0.0, 0.03, var=0.02, emit=((0.32, 0.88, 1.0), 5.0, 'radial'))
    L['paint_bone'] = make('paint_bone', (0.66, 0.62, 0.52), 0.0, 0.64, var=0.16, edge=((0.46, 0.44, 0.41), 1.0, 0.3, 1.0),
                           dirt=((0.30, 0.24, 0.17), 0.85, 0.95), rust=((0.40, 0.20, 0.08), 0.45), bumps=[('noise', 600, 0.35)],
                           edge_width=0.0012, grime=0.9)
    L['rubber_wrap'] = helix_rubber((0.080, 0.0, -0.030), (-0.4204, 0.0, 0.9073), (0.0, 1.0, 0.0))
    L['copper'] = make('copper', (0.85, 0.47, 0.30), 1.0, 0.32, var=0.1, edge=((0.95, 0.62, 0.45), 1.0, 0.2, 0.6),
                       dirt=((0.18, 0.11, 0.07), 0.7, 0.8), bumps=[('noise', 1800, 0.15)])
    L['stainless'] = make('stainless', (0.66, 0.65, 0.63), 1.0, 0.24, var=0.04, edge=((0.8, 0.8, 0.78), 1.0, 0.15, 0.6),
                          dirt=DIRT, bumps=[('clampslots', 34, -0.1255, 0.0017, 0.6)])
    L['rubber'] = make('rubber', (0.052, 0.048, 0.045), 0.0, 0.8, var=0.12, edge=((0.14, 0.13, 0.12), 0.0, 0.7, 0.6),
                       dirt=DUST, bumps=[('stipple', 1500, 0.35)], grime=0.6)
    L['polymer'] = make('polymer', (0.045, 0.045, 0.047), 0.0, 0.55, var=0.08, edge=((0.2, 0.2, 0.2), 0.0, 0.45, 0.5),
                        dirt=DUST, bumps=[('noise', 1500, 0.15)])
    L['wire_orange'] = make('wire_orange', (0.55, 0.23, 0.08), 0.0, 0.5, var=0.1, dirt=DUST)
    L['sleeve_teal'] = make('sleeve_teal', (0.12, 0.24, 0.25), 0.0, 0.42, var=0.12, edge=((0.30, 0.38, 0.37), 0.0, 0.6, 0.9),
                            dirt=DUST, bumps=[('noise', 500, 0.35)], grime=0.5,
                            stripe=(-0.0213, 0.0262, math.radians(150), 0.42, (0.62, 0.66, 0.62), (0.08, 0.12, 0.12)))
    L['glass'] = make('glass', (0.015, 0.02, 0.024), 0.0, 0.04, var=0.02, dirt=((0.3, 0.27, 0.22), 0.6, 0.35))
    L['crystal'] = make('crystal', (0.70, 0.95, 1.0), 0.0, 0.08, var=0.05, emit=((0.55, 0.95, 1.0), 6.0, 'crystal'), bevel_r=0.00012)
    L['led'] = make('led', (0.45, 0.9, 1.0), 0.0, 0.15, var=0.0, emit=((0.10, 0.80, 1.0), 8.0, 'all'))
    L['vent_glow'] = make('vent_glow', (0.2, 0.5, 0.6), 0.0, 0.5, var=0.05, emit=((0.12, 0.72, 1.0), 5.0, 'cavity'))
    L['core_fluid'] = make('core_fluid', (0.3, 0.75, 0.9), 0.0, 0.1, var=0.1, emit=((0.14, 0.78, 1.0), 4.5, 'crystal'))
    return L


def helix_rubber(origin, axis, e1, pitch=0.011):
    return make('rubber_wrap', (0.05, 0.046, 0.043), 0.0, 0.78, var=0.12, edge=((0.14, 0.13, 0.12), 0.0, 0.7, 0.5),
                dirt=((0.42, 0.35, 0.27), 0.9, 0.5), bumps=[('stipple', 1600, 0.25), ('helix', origin, axis, e1, pitch, 0.9)], grime=0.6)
