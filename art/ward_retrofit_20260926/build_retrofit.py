"""Ward district retrofit v1 (26 Sep 2026): make the shells read as salvaged corporate/industrial architecture
patched through years of war, and fill the empty quadrants with lore-grounded infrastructure.

Run headless:  blender -b --factory-startup -P build_retrofit.py
Writes WardRetrofit.glb (Unity Assets/AthenHill/Art/WardRetrofit/) and ward-retrofit-v1.blend.
Everything is authored in Ward world space (Unity x/z metres); see kit.U(). Each group exports as
'<Group>' root with '<Group> Structure' / 'Detail' (distance culled) / 'Glow' / 'Decals' meshes, COL_* boxes
and LIGHT_<colour>_* markers consumed by AthenHill.Editor.WardRetrofitPass.
"""
import sys, json, math
sys.path.insert(0, '/home/teknetik/code/ao2/art/ward_retrofit_20260926')
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
import importlib, kit
importlib.reload(kit)
from kit import *   # noqa

OUT_GLB = Path('/home/teknetik/code/ao2/unity/AthenHill/Assets/AthenHill/Art/WardRetrofit/WardRetrofit.glb')
OUT_BLEND = ROOT / 'ward-retrofit-v1.blend'
ONLY = [a for a in sys.argv[sys.argv.index('--') + 1:]] if '--' in sys.argv else []
RETRO = new_collection('WardRetrofit')
WARN = []

# CC0 library parts (decimated where heavy)
lib('exterior_aircon_unit', 'exterior_aircon_unit_rusted', 4000, key='aircon')
lib('utility_box_01', target=1500, key='ubox1'); lib('utility_box_02', target=1800, key='ubox2')
lib('power_box_01', target=2500, key='pbox')
lib('security_light', target=1500, key='seclight'); lib('security_camera_01', target=2500, key='cam')
lib('Barrel_01', key='barrel1'); lib('Barrel_02', key='barrel2'); lib('barrel_03', key='barrel3')
lib('old_tyre', key='tyre'); lib('concrete_road_barrier_02', target=3000, key='jersey')
lib('portable_generator', target=3000, key='gen'); lib('small_lpg_tank', target=1500, key='lpg')
lib('wooden_military_crate', target=2500, key='crate'); lib('plastic_crate_03', target=1500, key='pcrate')
lib('metal_trash_can', 'metal_trash_can_rust', 2500, key='bin')
lib('planter_box_02', target=2500, key='planter'); lib('cheiridopsis_succulent', 'cheiridopsis_succulent_a', 700, key='succ')
lib('crystalline_iceplant', 'crystalline_iceplant_a', 500, key='ice')
lib('industrial_wall_lamp', target=1500, key='walllamp'); lib('cement_bag', key='bag')
lib('portable_welding_cart', target=4000, key='welder'); lib('hand_truck', target=2500, key='handtruck')
lib('rollershutter_door', 'rollershutter_door', key='shutterdoor')
DROID_WALKS = True   # animated droid installed separately by AthenHill.Editor.WardMiningDroidPass
MESHY_DROID = Path('/home/teknetik/code/ao2/meshy/mining-droid-20260926/model.glb')
DROID_H, DROID_YAW = 3.4, math.pi / 2   # uniform scale to 3.4 m tall; lens (source -Y) turned to face the wellhead (+X)
if MESHY_DROID.exists() and not DROID_WALKS:
    d = lib('droid', target=None, key='droid', path=MESHY_DROID)
    dm = dims('droid'); sc = DROID_H / dm.z
    d.data.transform(Matrix.Scale(sc, 4)); d['dims'] = list(dm * sc)


def group(name, fn, *a):
    if ONLY and not any(o in name for o in ONLY): return None
    coll = new_collection(name, RETRO)
    CUR['coll'] = coll; CUR['kind'] = 'structure'
    fn(*a)
    root = bpy.data.objects.new(name, None); coll.objects.link(root)
    merge_group(coll, root, name)
    return root


def merge_group(coll, root, name):
    for kd in ('structure', 'detail', 'glow', 'decal'):
        obs = [o for o in coll.objects if o.get('kind') == kd and o.type == 'MESH']
        if not obs: continue
        bpy.ops.object.select_all(action='DESELECT')
        for o in obs:
            if o.data.users > 1: o.data = o.data.copy()
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        j.name = f'{name} {dict(structure="Structure", detail="Detail", glow="Glow", decal="Decals")[kd]}'; j.data.name = j.name
        j.parent = root
    for o in list(coll.objects):
        if o.get('kind') in ('collision', 'marker') and o.parent is None:
            mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw


def at(M, fn, *a, **kw):
    """Build a component in local space and move it by M."""
    with record() as obs:
        fn(*a, **kw)
    place(obs, M)
    return obs


def check_free(tag, x0, x1, z0, z1):
    if blocked(x0, x1, z0, z1): WARN.append(f'{tag}: footprint x{x0:.1f}..{x1:.1f} z{z0:.1f}..{z1:.1f} overlaps an existing collider')


# ================================================================ shop retrofits
SHOPS = [  # id, zc, side (-1 west row, +1 east row)
    ('relay_works', -18, -1), ('air_water', -9, -1), ('tool_exchange', 9, -1), ('salvage', 18, -1),
    ('finery', -18, 1), ('field_supply', -9, 1), ('repairs', 9, 1), ('thread_hide', 18, 1)]
FRONT_X, REAR_X, HALF = 17.6, 25.1, 3.8
ROOF_TAKEN = []
# Per-shop retrofit character: what each building became after years of repair (silhouette + material identity)
CHAR = {
    'relay_works': dict(blade='relay', module=(3.4, 1.3, 2.3, 'plate_teal'), clad={'s': 'plate_teal'}),
    'air_water': dict(blade='water', condenser=True, clad={'n': 'plate_bone'}),
    'tool_exchange': dict(blade='tools', module=(2.6, 2.6, 2.5, 'panel'), jib=True),
    'salvage': dict(blade='salvage', nest=True, scaffold='n'),
    'finery': dict(blade='finery', module=(2.6, 2.2, 2.2, 'plate_bone'), clad={'s': 'plate_bone'}),
    'field_supply': dict(blade='supply', clad={'n': 'plate_teal'}),
    'repairs': dict(blade='repairs', module=(3.6, 1.6, 2.4, 'container_rust'), clad={'s': 'plate_olive'}),
    'thread_hide': dict(blade='thread', balcony=4.6, clad={'n': 'plate_olive'}),
}


def roof_level(xc, zc):
    r = region(xc - 3, xc + 3, zc - 3, zc + 3)
    vals = r[r > 3].ravel()
    return float(np.median(vals)) if len(vals) else 6.


def roof_spot(side, zc, w, d, prefer=0., tol=.12):
    """Flat free rectangle on a shop roof for a piece oriented to face the avenue: w runs along the row (Unity z),
    d across it (Unity x). prefer<0 favours the rear deck. Returns Unity (x, z, height) or None."""
    fx, rx = side * FRONT_X, side * REAR_X
    xs = np.linspace(min(fx, rx) + d / 2 + .35, max(fx, rx) - d / 2 - .35, 22)
    zs = np.linspace(zc - HALF + w / 2 + .35, zc + HALF - w / 2 - .35, 16)
    best = None
    for x in xs:
        for z in zs:
            r = region(x - d / 2 - .1, x + d / 2 + .1, z - w / 2 - .1, z + w / 2 + .1)
            if r.max() - r.min() > tol or r.min() < 3: continue
            if any(abs(x - a) < (d + ad) / 2 + .25 and abs(z - b) < (w + aw) / 2 + .25 for a, b, ad, aw in ROOF_TAKEN): continue
            rearness = abs(x) - abs(fx)   # 0 front .. 7.5 rear
            score = (rearness if prefer < 0 else -rearness) * abs(prefer) + rng.random() * .5
            if best is None or score > best[0]: best = (score, x, z, float(r.max()))
    if best is None: return None
    ROOF_TAKEN.append((best[1], best[2], d, w))
    return best[1:]


def shop_retrofit(sid, zc, side, idx):
    R = roof_level(side * 21.4, zc)
    front = frame(side * FRONT_X - side * .02, zc, 0, -side, 0)     # outward toward avenue
    rear = frame(side * REAR_X + side * .02, zc, 0, side, 0)        # outward toward back lane
    s_n = frame(side * 21.35, zc + HALF + .01, 0, 0, 1)             # north side wall
    s_s = frame(side * 21.35, zc - HALF - .01, 0, 0, -1)            # south side wall
    rh = float(np.median(region(side * 24.6, side * 24.9, zc - 3, zc + 3)))   # rear parapet height
    rh = rh if rh > 3 else R
    paint = [M['plate_teal'], M['plate_bone'], M['plate_olive'], M['rust_paint'], M['panel']]
    p1, p2 = paint[idx % 5], paint[(idx + 2) % 5]

    # --- front: corner armour guards, camera, parapet light strip (the avenue read)
    def front_kit():
        for u in (-HALF + .22, HALF - .22):
            armor_panel(.34, 2.2, p1, loc=(u, 0, 1.25))
            box('Corner guard cap', (.4, .1, .08), M['steel'], (u, .1, 2.4), bevel=.01)
        light_strip(5.6, loc=(0, 0, R - .45))
        put('cam', (HALF - .35, .25, R - .9), rz=math.pi + (.5 if side > 0 else -.5), k='detail')
        box('Cable tray', (6.8, .16, .06), M['steel'], (0, .1, R - .75), bevel=.005)
        conduit_bundle([(-HALF + .45, .3), (-HALF + .45, R - .75)], .08, n=2)
        # projecting lit blade sign on the corner, above awning height
        bh = min(2.6, R - 4.4) if R > 6.4 else 1.8
        with record() as obs:
            blade_sign(ch['blade'], h=bh)
        bpy.context.view_layer.update()
        for o in obs:
            if o.parent is None: o.matrix_world = Matrix.Translation((HALF - .12, 0, 3.95)) @ o.matrix_world
        if ch.get('balcony'):
            with record() as obs:
                balcony(5.2, 1.15)
            bpy.context.view_layer.update()
            for o in obs:
                if o.parent is None: o.matrix_world = Matrix.Translation((-.6, 0, ch['balcony'])) @ o.matrix_world
            col_box(f'{sid}_balcony', (-.6, .6, ch['balcony'] + .5), (5.2, 1.2, 1.1))
        if ch.get('jib'):
            with record() as obs:
                jib_crane(2.4, 2.4)
            bpy.context.view_layer.update()
            for o in obs:
                if o.parent is None: o.matrix_world = Matrix.Translation((-1.9, -.45, R)) @ o.matrix_world
    ch = CHAR[sid]
    at(front, front_kit)

    # --- rear: service spine (pipes, conduits, AC, electrical), bolted patches over war damage
    def rear_kit():
        wall_pipe([(-2.6, .3), (-2.6, rh - .2), (-2.6, rh + .5)], .11, .25, M['rust'])
        wall_pipe([(1.2, 1.0), (1.2, rh - .7), (3.2, rh - .7)], .07, .2, M['steel'])
        conduit_bundle([(-3.3, .2), (-3.3, rh - .1)], .08, n=3)
        for i, (u, z) in enumerate([(-.6, 2.6), (2.3, 3.8)][:1 + idx % 2]):
            put('aircon', (u, .25, z - .45), rz=0, k='detail')
            box('AC bracket', (1.7, .45, .06), M['steel'], (u, .22, z - .47), bevel=.005)
            decal('streaks', .9, 1.8, (u + .2, .02, z - 1.5), (math.pi / 2, 0, 0))
        put(['ubox1', 'ubox2', 'pbox'][idx % 3], (-1.2, .25, 0), rz=math.pi, k='detail')
        armor_panel(1.4, 1.1, p2, loc=(1.6 - idx % 3, 0, 1.6 + (idx % 2) * 1.8))
        armor_panel(.9, 1.6, M['rust_sheet'], loc=(-1.9, 0, rh - 1.6))
        decal('scorch', 2.6, 2.6, (.3 + (idx % 3) - 1, .015, 2.8 + (idx % 2)), (math.pi / 2, 0, rng.uniform(0, 6)))
        decal('pocks', 2.2, 1.6, (-.8, .018, 1.7), (math.pi / 2, 0, 0))
        put('walllamp', (.2, .1, 3.0), rz=math.pi, k='detail'); light_marker(f'{sid}_rear', Vector((.2, .45, 3.0)), 'amber')
    at(rear, rear_kit)

    # --- side walls: bolted breach repairs, conduit, grime; banner on the cross-street faces
    ch = CHAR[sid]
    for nm, fr in (('n', s_n), ('s', s_s)):
        cross = (nm == 'n' and zc < 0 and abs(zc) < 12) or (nm == 's' and zc > 0 and abs(zc) < 12)
        def side_kit(cross=cross, nm=nm):
            u0 = side * (-1 if nm == 'n' else 1)   # local X runs along wall; keep features toward the rear half
            clad = ch.get('clad', {}).get(nm)
            if clad:
                with record() as obs:
                    cladding(6.4, R - 3.0, M[clad])
                bpy.context.view_layer.update()
                for o in obs:
                    if o.parent is None: o.matrix_world = Matrix.Translation((0, 0, 2.5)) @ o.matrix_world
                light_strip(6.2, loc=(0, .12, 2.35))
            else:
                armor_panel(1.8, 1.3, p2 if cross else M['rust_sheet'], loc=(u0 * 1.6, 0, 3.3))
                decal('scorch', 3.0, 2.2, (u0 * 1.6, .012, 3.4), (math.pi / 2, 0, 0))
            if ch.get('scaffold') == nm:
                scaffold(6.6, R - 1.2)
            conduit_bundle([(u0 * 3.55, .2), (u0 * 3.55, R - .4)], .07, n=2)
            if cross:
                put('seclight', (u0 * -.5, .05, R - 1.2), rz=math.pi, k='detail')
                light_marker(f'{sid}_{nm}', Vector((u0 * -.5, .6, R - 1.3)), 'amber')
                if idx in (1, 6): banner(1.0, 2.6, (u0 * -2.1, 0, R - .8))
                put('bin', (u0 * .8, .5, 0), rz=0, k='detail')
                put(['barrel1', 'barrel2', 'barrel3'][idx % 3], (u0 * -1.6, .45, 0), rz=idx, k='detail')
                col_box(f'{sid}_{nm}_bin', (u0 * .3, .5, .45), (3.4, .9, .9))
        at(fr, side_kit)

    # --- character pieces on the roof first (they need the largest flat areas)
    if ch.get('module'):
        w, d, h, mat = ch['module']
        spot = roof_spot(side, zc, w + .3, d + .2, prefer=-1, tol=.15)
        if spot: at(frame(spot[0], spot[1], spot[2], -side, 0), roof_module, w, d, h, M[mat])
        else: WARN.append(f'{sid}: no roof spot for module')
    if ch.get('condenser'):
        spot = roof_spot(side, zc, 1.9, 1.9, prefer=.5, tol=.2) or roof_spot(side, zc, 1.8, 1.8, prefer=-1, tol=.5)
        if spot: at(frame(spot[0], spot[1], spot[2], -side, 0), condenser_tower, 5.2, .75)
        else: WARN.append(f'{sid}: no roof spot for condenser')
    if ch.get('nest'):
        spot = roof_spot(side, zc, 2.8, 2.6, prefer=-1, tol=.45)
        if spot: at(frame(spot[0], spot[1], spot[2], -side, 0), lookout_nest, 2.6, 2.4)
        else: WARN.append(f'{sid}: no roof spot for lookout')
    # --- roof machinery (seated on the surveyed roof surface)
    plan = [('hvac', 2.0, 1.4), ('vent', .6, .6), ('vent', .6, .6)]
    plan += [('mast', .7, .7)] if idx in (0, 3, 6) else [('panels', 2.5, 1.4)] if idx in (2, 5, 7) else [('tank', 2.2, 2.2)]
    if idx % 2 == 0: plan.append(('hvac', 1.6, 1.1))
    for i, (what, w, d) in enumerate(plan):
        spot = roof_spot(side, zc, w, d, prefer=-1 if what in ('tank', 'mast') else .3) or roof_spot(side, zc, w * .8, d * .8, tol=.35 if what in ('mast', 'vent') else .2)
        if not spot: WARN.append(f'{sid}: no roof spot for {what}'); continue
        x, z, h = spot
        M4 = frame(x, z, h, -side, 0)
        if what == 'hvac': at(M4, hvac_unit, w - .2, d - .2, 1.0)
        elif what == 'vent': at(M4, vent_stack, .15, rng.uniform(1.0, 1.8))
        elif what == 'mast': at(M4, lattice_mast, 7.5 + idx * .4, .55, True, True, f'mast_{sid}')
        elif what == 'panels': at(M4, radiator_bank, 2, 1.0, 1.3, 30)
        elif what == 'tank': at(M4, water_tank, .95, 1.8, [M['plate_bone'], M['rust_paint'], M['plate_teal']][idx % 3], .7)
    return R


ROOFS = {}


def all_shops():
    for i, (sid, zc, side) in enumerate(SHOPS):
        ROOFS[sid] = shop_retrofit(sid, zc, side, i)
    # cross-street pipe bridges between the two middle buildings of each row, and alley cable swags
    for side in (-1, 1):
        x = side * 24.2
        hb = min(ROOFS[[s for s, z, sd in SHOPS if sd == side and z == -9][0]], ROOFS[[s for s, z, sd in SHOPS if sd == side and z == 9][0]]) - .6
        for dx, r in ((0, .16), (side * -.5, .1)):
            tube('Pipe bridge', [U(x + dx, -5.3, hb), U(x + dx, 5.3, hb)], r, M['rust'] if r > .12 else M['steel'], sides=12, caps=True)
        for zz in (-4.2, -1.4, 1.4, 4.2):
            with kind('detail'):
                cyl_between('Bridge hanger', U(x - side * .25, zz, hb + .2), U(x - side * .25, zz, hb - .25), .02, M['steel'], sides=6)
        span('Bridge spine', U(x - side * .25, -5.3, hb - .25), U(x - side * .25, 5.3, hb - .25), .12, .12, M['steel'])
        for zc in (-13.5, 13.5):
            for k in range(3):
                a = U(side * rng.uniform(18.5, 24.5), zc - 1.2, rng.uniform(4.4, 5.6))
                b = U(side * rng.uniform(18.5, 24.5), zc + 1.2, rng.uniform(4.4, 5.6))
                cable(a, b, sag=rng.uniform(.15, .45))


# ================================================================ lanes: utility poles and overhead lines
def utility_pole(h=8.5):
    ibeam('Pole', (0, 0, 0), (0, 0, h), .26, .2, mat=M['rust'])
    span('Crossarm', (-1.1, 0, h - .5), (1.1, 0, h - .5), .1, .12, M['rust'])
    span('Crossarm', (-.8, 0, h - 1.3), (.8, 0, h - 1.3), .1, .12, M['rust'])
    with kind('detail'):
        for x in (-1.0, -.35, .35, 1.0):
            cyl('Insulator', .05, .18, M['plate_bone'], loc=(x, 0, h - .44), sides=8)
        cyl('Transformer', .32, .9, M['plate_olive'], loc=(0, .38, h - 2.8), sides=16)
        box('Transformer bracket', (.3, .3, .1), M['steel'], (0, .18, h - 2.85), bevel=.005)
        box('Junction box', (.4, .22, .6), M['panel'], (0, -.22, 2.2), bevel=.01)
    box('Pole base', (.7, .7, .3), M['concrete'], (0, 0, .15), bevel=.02)


def lanes():
    for side in (-1, 1):
        x = side * 28.4
        zs = [-22.5, -13.5, -4.5, 4.5, 13.5, 22.5]
        tops = []
        for z in zs:
            f = find_free(x, z, .4, .4, 2.0)
            if not f: WARN.append(f'pole {side},{z}: no free spot'); continue
            px, z = f
            h = 8.2 + rng.uniform(-.3, .5)
            at(frame(px, z, 0, 0, 1), utility_pole, h)   # crossarm across the lane (local X = Unity +x)
            col_box(f'pole_{side}_{z}', U(px, z, 1.5), (.7, .7, 3.))
            tops.append((z, h, px))
        for (z0, h0, x0), (z1, h1, x1) in zip(tops, tops[1:]):
            for dx in (-1.0, -.35, .35, 1.0):   # one line per insulator
                cable(U(x0 + dx, z0, h0 - .38), U(x1 + dx, z1, h1 - .38), sag=.35 + abs(dx) * .1, r=.012)
        # service drops from poles to the rear roofs of the shops
        for sid, zc, sd in SHOPS:
            if sd != side: continue
            z, h, px = min(tops, key=lambda q: abs(q[0] - zc))
            cable(U(px, z, h - 1.25), U(side * 25.0, zc + rng.uniform(-2, 2), ROOFS.get(sid, 6.) - .3), sag=.6, r=.016)


# ================================================================ NE: collapsed processing hall (pre-Fall industry)
def processing_hall():
    """Local frame at (36, 34), local +Y faces the city (south). Local +X = Unity -x."""
    cols = [(x, y) for x in (-7.5, -2.5, 2.5, 7.5) for y in (-5.5, 0., 5.5)]
    broken = {(7.5, -5.5): 4.5, (2.5, -5.5): 2.2, (7.5, 0.): 7.0, (2.5, 5.5): 3.0}
    gone = {(7.5, 5.5)}
    H = 10.5
    for (x, y) in cols:
        if (x, y) in gone: continue
        b = broken.get((x, y), 0.)
        o = precast_column(H - b, .6, broken=.8 if b else 0.)
        o.location = (x, y, 0)
        box('Column footing', (1.0, 1.0, .35), M['concrete_cracked'], (x, y, .17), bevel=.03, uv=.5)
        col_box(f'hall_col_{x}_{y}', (x, y, 1.5), (.7, .7, 3.))
    # ring beams across intact column tops
    for y in (-5.5, 0., 5.5):
        for x0, x1 in ((-7.5, -2.5), (-2.5, 2.5)):
            if (x1, y) in broken or (x0, y) in broken: continue
            box('Ring beam', (5.6, .5, .75), M['concrete'], ((x0 + x1) / 2, y, H - .37), bevel=.02, uv=.45)
    for x in (-7.5, -2.5):
        box('Tie beam', (.45, 11.6, .6), M['concrete'], (x, 0, H - .3), bevel=.02, uv=.45)
    # roof trusses over the two surviving bays, corrugated sheets with gaps, one sagging broken truss
    for x in (-7.5, -5.0, -2.5):
        with record() as obs:
            pratt_truss(11.0, 1.8)
        place(obs, Matrix.Translation((x, -5.5, H)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
    with record() as obs:
        pratt_truss(11.0, 1.8, broken_at=.55)
    place(obs, Matrix.Translation((0.2, -5.5, H - .3)) @ Matrix.Rotation(math.pi / 2, 4, 'Z') @ Matrix.Rotation(math.radians(-14), 4, 'Y'))
    for i in range(10):
        y0 = -5.4 + i * 1.1
        if i in (3, 7): continue
        for x0 in (-7.8, -5.0):
            w = 2.8 if rng.random() > .15 else 1.6
            box('Roof sheet', (w, 1.15, .03), M['corrugated_worn'], (x0 + w / 2, y0 + .55, H + 1.0 + .75 * (1 - abs(y0) / 6)),
                (math.radians(8 if y0 < 0 else -8), rng.uniform(-.03, .03), 0), bevel=0, uv=.4)
    # fallen truss section and roof sheets in the collapsed bay
    with record() as obs:
        pratt_truss(8.0, 1.6)
    place(obs, Matrix.Translation((6.0, -4.5, .4)) @ Matrix.Rotation(math.radians(80), 4, 'Z') @ Matrix.Rotation(math.radians(-22), 4, 'Y'))
    for i in range(6):
        box('Fallen sheet', (2.4, 1.1, .03), M['corrugated_worn'], (rng.uniform(3, 8), rng.uniform(-4, 4), rng.uniform(.3, 1.2)),
            (rng.uniform(-.7, .7), rng.uniform(-.5, .5), rng.uniform(0, 3)), bevel=0, uv=.4)
    for (x, y, r, h) in ((5.5, -2.0, 2.6, 1.3), (7.2, 4.2, 2.2, 1.6), (3.2, 3.6, 1.4, .8)):
        with record() as obs:
            rubble(r, h, 16)
        place(obs, Matrix.Translation((x, y, 0)))
        col_box(f'rubble_{x}', (x, y, h * .4), (r * 1.3, r * 1.3, h * .8))
    # surviving wall panels: rear (north) and west side, jagged tops, window gaps, company sigil
    for x0, x1 in ((-8, -2.8), (-2.2, 3.0)):
        w = x1 - x0
        o = box('Wall panel', (w, .3, 4.2), M['concrete_cracked'], ((x0 + x1) / 2, 5.8, 2.1), bevel=.02, uv=.35)
        col_box(f'hall_wall_{x0}', ((x0 + x1) / 2, 5.8, 1.5), (w, .4, 3.))
    box('Wall panel high', (5.0, .3, 3.2), M['concrete_ribbed'], (-5.2, 5.8, 5.8), bevel=.02, uv=.35)
    for y0, y1 in ((-6, -1.2), (.6, 6)):
        w = y1 - y0
        box('Side wall', (.3, w, 3.6 if y0 < 0 else 6.5), M['concrete_ribbed'], (-8.1, (y0 + y1) / 2, (3.6 if y0 < 0 else 6.5) / 2), bevel=.02, uv=.35)
        col_box(f'hall_side_{y0}', (-8.1, (y0 + y1) / 2, 1.5), (.4, w, 3.))
    decal('sigil', 2.6, 2.6, (-5.2, 5.965, 6.3), (math.pi / 2, 0, 0))
    decal('stencil_proc', 4.0, .8, (-5.2, 5.965, 4.4), (math.pi / 2, 0, 0))
    decal('scorch', 4.5, 3.5, (0.4, 5.97, 2.5), (math.pi / 2, 0, 0))
    decal('streaks', 3, 5, (-5.2, 5.96, 5.0), (math.pi / 2, 0, 0))
    # overhead crane rails on corbels, with the stranded crane bridge
    for y in (-5.0, 5.0):
        ibeam('Crane rail', (-7.8, y, 7.6), (2.8, y, 7.6), .36, .22)
    ibeam('Crane bridge', (-4.2, -5.2, 7.95), (-4.2, 5.2, 7.95), .6, .3, mat=M['rust_paint'])
    box('Crane trolley', (1.1, 1.2, .7), M['rust_paint'], (-4.2, 1.2, 7.6), bevel=.03)
    tube('Crane cable', [Vector((-4.2, 1.2, 7.3)), Vector((-4.1, 1.25, 3.2))], .02, M['steel'], sides=5)
    box('Crane hook block', (.3, .2, .45), M['hazard'], (-4.1, 1.25, 3.0), bevel=.02)
    # rusted conveyor spine running out of the hall toward the east wall
    for x in (9, 13, 17):
        span('Conveyor A-frame', (-x, -1.2, 0), (-x, -.3, 4.2), .12, .12, M['rust'])
        span('Conveyor A-frame', (-x, .6, 0), (-x, -.3, 4.2), .12, .12, M['rust'])
        col_box(f'conveyor_{x}', (-x, -.3, 1.5), (.3, 2.0, 3.0))
    for yy in (-.7, .1):
        ibeam('Conveyor stringer', (-6, yy, 4.3), (-19, yy, 3.4), .3, .14)
    box('Conveyor belt', (13.1, .7, .06), M['rubber'], (-12.5, -.3, 4.02), (0, math.radians(-3.95), 0), bevel=0)
    for i in range(8):
        box('Belt cover', (1.2, 1.0, .03), M['rust_sheet'], (-7.5 - i * 1.6, -.3, 4.45 - i * .11), (0, math.radians(-4) + rng.uniform(-.06, .06), rng.uniform(-.05, .05)), bevel=0)


# ================================================================ NW: hydroponics bays (food supply)
def quonset(L=15., W=6.2, H=4.2, tag='A'):
    n = int(L / 1.5)
    prof = lambda t: Vector((0, -W / 2 * math.cos(t * math.pi), H * math.sin(t * math.pi) ** .85))
    for i in range(n + 1):
        x = -L / 2 + L * i / n
        tube('Rib', [prof(t / 16) + Vector((x, 0, 0)) for t in range(17)], .05, M['steel'], sides=6)
    for t in (.12, .3, .5, .7, .88):
        span('Purlin', prof(t) + Vector((-L / 2, 0, 0)), prof(t) + Vector((L / 2, 0, 0)), .06, .06, M['steel'], bevel=0)
    # polycarbonate skin with missing panels patched by tarp
    def skin(u, v):
        return prof(v) + Vector((-L / 2 + u * L, 0, 0)) + prof(v).normalized() * 0
    sheet('Poly skin', lambda u, v: Vector((-L / 2 + u * L, prof(v).y * 1.012, prof(v).z * 1.012)), (n, 12), M['poly'], (L / 1.5, 3), holes=.05)
    def tarp(u, v):
        p = prof(.62 + v * .2); return Vector((-L / 2 + L * (.55 + u * .2), p.y * 1.03, p.z * 1.03 - .05 * math.sin(u * math.pi)))
    sheet('Tarp patch', tarp, (6, 5), M['tarp'], (1.5, 1.))
    # end walls with door, stencil and grow-lit interior
    for s in (-1, 1):
        x = s * L / 2
        box('End frame', (.12, W * .9, .14), M['steel'], (x, 0, H * .78), bevel=.005)
        for yy in (-W * .42, -1.0, 1.0, W * .42):
            box('End post', (.12, .12, H * .85 if abs(yy) < 2 else H * .5), M['steel'], (x, yy, (H * .85 if abs(yy) < 2 else H * .5) / 2), bevel=.005)
        box('End panels', (.04, W * .82, H * .7), M['poly'], (x, 0, H * .35), bevel=0)
        box('Door', (.06, 1.8, 2.2), M['panel'], (x + s * .03, 0, 1.1), bevel=.01)
        decal(f'stencil_hydro{tag}', 2.6, .5, (x + s * .07, 0, 2.6), (math.pi / 2, 0, -s * math.pi / 2))
    # interior: tiered grow racks under LED bars, visible through the skin
    for yy in (-1.6, 1.6):
        for tier in (.7, 1.45):
            box('Grow tray', (L - 1.2, 1.1, .12), M['panel'], (0, yy, tier), bevel=.01)
            with kind('detail'):
                for i in range(int((L - 1.6) / .7)):
                    o = put(rng.choice(['succ', 'ice']), (-L / 2 + 1.0 + i * .7, yy + rng.uniform(-.3, .3), tier + .06), rz=rng.uniform(0, 6), s=rng.uniform(.28, .42), k='detail')
            box('Grow LED', (L - 1.4, .5, .04), M['grow'], (0, yy, tier + .6), bevel=0, k='glow')
        for x in (-L / 2 + .8, L / 2 - .8):
            span('Rack post', (x, yy, 0), (x, yy, 2.1), .05, .05, M['steel'], bevel=0)
    col_box(f'quonset_{tag}', (0, 0, 1.5), (L + .3, W + .2, 3.0))


def hydroponics():
    """Local frame at (-34, 32.5) facing south; local +X = Unity -x."""
    for tag, y in (('A', -4.2), ('B', 4.2)):
        with record() as obs:
            quonset(15., 6.2, 4.2, tag)
        place(obs, Matrix.Translation((0, y, 0)))
    for i, x in enumerate((9.3, 9.6)):
        with record() as obs:
            water_tank(1.3, 3.4, M['plate_teal'] if i == 0 else M['rust_paint'], .8)
        place(obs, Matrix.Translation((x, -4.0 + i * 5.6, 0)))
        col_box(f'hydro_tank_{i}', (x, -4.0 + i * 5.6, 1.5), (2.8, 2.8, 3.0))
    # manifold: filtered water from the tanks into both bays
    for y in (-4.2, 4.2):
        tube('Feed pipe', fillet([Vector((8.2, y * .95, .4)), Vector((8.2, y * .95, 2.6)), Vector((7.4, y * .95, 2.6))], .3), .08, M['plate_teal'], sides=10, caps=True)
    box('Pump skid', (1.4, 2.2, .2), M['tread'], (7.9, 0, .1), bevel=.01)
    cyl('Pump motor', .32, .8, M['plate_olive'], loc=(7.9, -.4, .55), rot=(math.pi / 2, 0, 0), sides=14)
    cyl('Filter canister', .26, 1.3, M['plate_bone'], loc=(7.9, .6, .2), sides=14)
    decal('stencil_potable', 1.4, .18, (7.9, .87, .95), (math.pi / 2, 0, 0))
    col_box('hydro_pump', (7.9, 0, .7), (1.6, 2.4, 1.4))
    for x in (-5, 0, 5):
        put('planter', (x, 0, 0), rz=0, k='detail'); put('succ', (x, 0, .42), rz=rng.uniform(0, 6), s=.3, k='detail')


# ================================================================ SE: Nanofab 2 workshop (working fab annex)
def chamfer_block(W, D, H, c, mat, z0=0.):
    bm = bmesh.new()
    pts = [(-W / 2 + c, -D / 2), (W / 2 - c, -D / 2), (W / 2, -D / 2 + c), (W / 2, D / 2 - c), (W / 2 - c, D / 2), (-W / 2 + c, D / 2), (-W / 2, D / 2 - c), (-W / 2, -D / 2 + c)]
    b = [bm.verts.new((x, y, z0)) for x, y in pts]; t = [bm.verts.new((x, y, z0 + H)) for x, y in pts]
    bm.faces.new(t); bm.faces.new(b[::-1])
    for i in range(8):
        j = (i + 1) % 8; bm.faces.new((b[i], b[j], t[j], t[i]))
    bm.normal_update()
    o = mesh_obj('Block', bm, mat); box_uv(o, .35)
    return o


def nanofab():
    """Local frame at (36, -33), facing north (+z). Local +X = Unity +x."""
    W, D, H = 14., 10., 7.4
    chamfer_block(W, D, 1.3, 1.6, M['concrete'])
    chamfer_block(W - .1, D - .1, H - 1.3, 1.6, M['plate_teal'], 1.3)
    chamfer_block(W + .3, D + .3, .35, 1.7, M['steel'], H - .1)
    col_box('fab', (0, 0, 1.5), (W, D, 3.0))
    # vertical composite ribs and horizontal cyan band on the frontage
    for x in (-5.2, -2.6, 0, 2.6, 5.2):
        box('Facade rib', (.22, .25, H - 1.5), M['panel'], (x, D / 2 + .1, 1.3 + (H - 1.5) / 2), bevel=.02)
    light_strip(W - 3.4, loc=(0, D / 2 + .22, 5.2))
    box('Loading door', (4.6, .12, 4.2), M['shutter'], (-2.2, D / 2 + .02, 2.1), bevel=.02, uv=.4)
    for s in (-1, 1):
        box('Door jamb', (.35, .4, 4.5), M['hazard'], (-2.2 + s * 2.45, D / 2 + .15, 2.25), bevel=.02, uv=.6)
    box('Door header', (5.3, .45, .4), M['hazard'], (-2.2, D / 2 + .17, 4.45), bevel=.02, uv=.6)
    box('Personnel door', (1.1, .1, 2.2), M['panel'], (3.6, D / 2 + .02, 1.1 + 1.3 - 1.3), bevel=.01)
    box('Door canopy', (1.8, 1.0, .08), M['steel'], (3.6, D / 2 + .5, 2.55), bevel=.01)
    box('Access panel', (.35, .08, .5), M['dark'], (4.5, D / 2 + .06, 1.4), bevel=.01)
    box('Access screen', (.25, .02, .18), M['cyan'], (4.5, D / 2 + .1, 1.5), bevel=0, k='glow')
    light_marker('fab_door', Vector((3.6, D / 2 + .9, 2.4)), 'cyan')
    decal('stencil_fab2', 5.0, 1.25, (-1.5, D / 2 + .26, 6.3), (math.pi / 2, 0, 0))
    decal('stencil_fab2b', 2.6, .33, (3.6, D / 2 + .08, 2.9), (math.pi / 2, 0, 0))
    decal('sigil', 1.6, 1.6, (5.4, D / 2 + .26, 6.1), (math.pi / 2, 0, 0))
    decal('scorch', 3.4, 2.8, (-5.8, D / 2 + .27, 3.0), (math.pi / 2, 0, 1.0))
    decal('pocks', 3.0, 2.0, (-5.5, D / 2 + .275, 2.4), (math.pi / 2, 0, 0))
    armor_panel(1.6, 2.2, M['rust_sheet'], loc=(-5.6, D / 2 + .2, 3.0))
    # roof: three cooling fans, ducts, tall exhaust stack with platform
    for x in (-4.5, -1.0, 2.5):
        with record() as obs:
            hvac_unit(2.4, 2.0, 1.1)
        place(obs, Matrix.Translation((x, -1.5, H + .25)))
    cyl('Exhaust stack', .55, 7.5, M['steel'], loc=(5.0, -2.5, H), sides=20)
    for zz in (2.0, 4.5, 7.0):
        cyl('Stack band', .6, .12, M['rust'], loc=(5.0, -2.5, H + zz), sides=20)
    cyl('Stack platform', 1.1, .08, M['grate'], loc=(5.0, -2.5, H + 5.0), sides=20)
    cyl('Stack glow ring', .58, .08, M['cyan'], loc=(5.0, -2.5, H + 7.35), sides=20, k='glow')
    tube('Roof duct', fillet([Vector((-6, 2.5, H + .6)), Vector((3.5, 2.5, H + .6)), Vector((3.5, -1.6, H + .6)), Vector((4.5, -2.5, H + 1.2))], .5), .28, M['steel'], sides=14, caps=True)
    # east side: process gas cylinders feeding the fab
    for i, y in enumerate((-2.5, 0, 2.5)):
        cyl('Process cylinder', .55, 5.2, [M['plate_bone'], M['plate_bone'], M['rust_paint']][i], loc=(W / 2 + 1.4, y, .3), sides=18)
        cyl('Cylinder cap', .56, .35, M['steel'], loc=(W / 2 + 1.4, y, 5.5), sides=18, r2=.2)
        tube('Gas line', fillet([Vector((W / 2 + 1.4, y, 5.7)), Vector((W / 2 + 1.4, y, 6.3)), Vector((W / 2 - .1, y, 6.3))], .3), .05, M['steel'], sides=8)
    box('Cylinder plinth', (1.6, 8, .3), M['concrete'], (W / 2 + 1.4, 0, .15), bevel=.02)
    col_box('fab_cyl', (W / 2 + 1.4, 0, 1.5), (1.6, 8, 3.0))
    # west side: corrugated lean-to over a scrap-sorting bay
    for y in (-3.5, 0, 3.5):
        span('Lean-to post', (-W / 2 - 3.2, y, 0), (-W / 2 - 3.2, y, 3.2), .12, .12, M['rust'])
    box('Lean-to roof', (3.6, 8.2, .04), M['corrugated_worn'], (-W / 2 - 1.7, 0, 3.55), (0, math.radians(-12), 0), bevel=0, uv=.4)
    with kind('detail'):
        put('welder', (-W / 2 - 1.5, -2.2, 0), rz=.5); put('handtruck', (-W / 2 - 2.4, 1.0, 0), rz=2.0)
        for i in range(4): put('crate', (-W / 2 - 1.3, 1.5 + i * .0, .46 * i if i < 2 else 0), rz=1.57)
        put('gen', (-W / 2 - 2.5, -3.0, 0), rz=.3)
    col_box('leanto', (-W / 2 - 1.7, 0, 1.2), (3.2, 7.4, 2.4))
    # yard: container stack facing the mechanic's loop
    with record() as obs:
        container(mat=M['container_blue'])
    place(obs, Matrix.Translation((-4.0, 8.4, 0)) @ Matrix.Rotation(.05, 4, 'Z'))
    with record() as obs:
        container(mat=M['container_rust'], window=False)
    place(obs, Matrix.Translation((-4.2, 8.4, 2.6)) @ Matrix.Rotation(-.06, 4, 'Z'))
    col_box('fab_containers', (-4.0, 8.4, 1.5), (6.2, 2.6, 3.0), .05)


# ================================================================ SW: aquifer pump station + repurposed mining droid
def mining_droid():
    """Old corporate mining droid, knelt and jury-rigged as the station's extraction pump."""
    # hull: armoured, chamfered body with plate seams, missing panels and exposed frame
    chamfer_block(3.2, 2.2, 1.6, .5, M['plate_bone'], 1.3)
    chamfer_block(2.6, 1.8, .5, .4, M['rust_paint'], 2.9)
    box('Hull ridge', (2.4, .5, .25), M['steel'], (0, 0, 3.5), bevel=.03)
    for s in (-1, 1):
        box('Flank plate', (2.6, .06, 1.1), M['rust_paint'], (0, s * 1.12, 2.1), (s * .12, 0, 0), bevel=.02)
    box('Exposed frame', (.9, .04, .9), M['dark'], (-.8, -1.13, 2.0), bevel=0)
    # sensor head: dead lenses, one flickering cyan (still loyal code)
    box('Head', (.9, 1.0, .7), M['plate_bone'], (1.9, 0, 2.6), (0, math.radians(18), 0), bevel=.08)
    cyl('Lens', .16, .1, M['dark'], loc=(2.37, -.22, 2.45), rot=(0, math.pi / 2, 0), sides=16)
    cyl('Lens live', .12, .12, M['cyan'], loc=(2.37, .22, 2.45), rot=(0, math.pi / 2, 0), sides=16, k='glow')
    light_marker('droid_eye', Vector((2.7, .22, 2.45)), 'cyan')
    # four jointed legs folded under the body
    for sx in (-1, 1):
        for sy in (-1, 1):
            hip = Vector((sx * 1.3, sy * 1.1, 1.9)); knee = Vector((sx * 2.2, sy * 1.9, 1.3)); foot = Vector((sx * 2.0, sy * 1.8, 0))
            span('Thigh', hip, knee, .34, .42, M['rust'])
            span('Shin', knee, foot, .3, .36, M['plate_bone'])
            cyl('Knee joint', .28, .5, M['steel'], loc=knee - Vector((0, sy * .25, 0)), rot=(math.pi / 2, 0, 0), sides=14)
            cyl_between('Piston', hip + Vector((0, 0, -.3)), knee + Vector((0, 0, .25)), .07, M['steel'], sides=8)
            box('Foot pad', (.8, .7, .18), M['rust'], foot + Vector((0, 0, .09)), bevel=.03)
    # drill boom lowered into the well casing (now the pump rod)
    span('Boom', (1.5, 0, 2.2), (3.4, 0, 1.4), .45, .5, M['plate_bone'])
    cyl_between('Drill rod', (3.4, 0, 1.6), (3.5, 0, -.2), .16, M['steel'], sides=12)
    # scavenged additions: cable looms, battery cells, patch plates
    for i in range(3):
        box('Salvage cell', (.5, .35, .4), M['plate_olive'], (-1.0 + i * .55, -.2, 3.45), bevel=.02)
    for i in range(4):
        cable(Vector((-1.2 + i * .4, -.9, 3.3)), Vector((-2.6 - i * .3, -1.5 - i * .2, 0.02)), sag=-.2 - i * .05, r=.025)
    armor_panel(1.0, .8, M['rust_sheet'], loc=(0, 1.15, 2.2))


def aquifer():
    """Local frame at (-35, -33), facing north (+z). Local +X = Unity +x."""
    # pump house
    box('Pump house', (8.0, 6.0, 4.6), M['concrete_cracked'], (0, 0, 2.3), bevel=.04, uv=.35)
    box('Pump house roof', (8.6, 6.6, .25), M['steel'], (0, 0, 4.72), bevel=.02)
    box('Roof sheet', (8.4, 6.4, .04), M['corrugated_worn'], (0, 0, 4.95), (math.radians(4), 0, 0), bevel=0, uv=.4)
    col_box('pumphouse', (0, 0, 1.5), (8.0, 6.0, 3.0))
    box('Pump door', (2.4, .1, 2.8), M['shutter'], (-1.6, 3.02, 1.4), bevel=.02)
    for i in range(4):
        box('Louvre bank', (1.0, .08, .7), M['grate'], (1.4 + i * 1.1 - 1.1, 3.03, 3.3), bevel=.01)
    decal('stencil_aquifer', 5.2, .8, (.4, 3.08, 4.05), (math.pi / 2, 0, 0))
    decal('scorch', 3.0, 2.4, (2.6, 3.07, 1.4), (math.pi / 2, 0, .5))
    armor_panel(2.0, 1.4, M['plate_olive'], loc=(2.4, 3.0, 1.3))
    decal('streaks', 2.6, 3.2, (-1.0, 3.065, 3.2), (math.pi / 2, 0, 0))
    put('walllamp', (-1.6, 3.1, 3.2), rz=0); light_marker('pump_door', Vector((-1.6, 3.6, 3.1)), 'amber')
    # three storage tanks behind (south)
    for i, x in enumerate((-5.5, -1.5, 2.5)):
        with record() as obs:
            water_tank(1.45, 4.6, [M['plate_bone'], M['plate_teal'], M['rust_paint']][i], .6)
        place(obs, Matrix.Translation((x, -6.0, 0)))
        col_box(f'aq_tank_{i}', (x, -6.0, 1.5), (3.0, 3.0, 3.0))
        tube('Tank header', fillet([Vector((x, -4.4, 1.2)), Vector((x, -3.4, 1.2)), Vector((x, -3.4, 3.9)), Vector((x, -3.1, 3.9))], .35), .14, M['rust'], sides=12)
    tube('Header main', [Vector((-6.4, -3.6, 4.2)), Vector((3.6, -3.6, 4.2))], .2, M['plate_teal'], sides=14, caps=True)
    # well head: flanged casing, valve wheel, the repurposed droid driving the pump
    WX, WY = 7.8, 2.2
    cyl('Well casing', .55, 1.0, M['rust'], loc=(WX, WY, 0), sides=20)
    cyl('Casing flange', .75, .12, M['steel'], loc=(WX, WY, 1.0), sides=20)
    tube('Rising main', fillet([Vector((WX, WY, 1.0)), Vector((WX, WY, 2.4)), Vector((4.0, WY, 2.4)), Vector((4.0, 1.0, 2.4))], .4), .22, M['plate_teal'], sides=14, caps=True)
    tube('Valve wheel', [Vector((WX + .45 * math.cos(a), WY + .7, 1.7 + .45 * math.sin(a))) for a in np.linspace(0, 2 * math.pi, 17)], .03, M['red'] if False else M['rust_paint'], sides=6)
    if DROID_WALKS:
        pass   # the rigged Meshy droid patrols this yard (rig_droid.py + WardMiningDroidPass); no static copy
    elif MESHY_DROID.exists():   # Meshy hero asset (meshy/mining-droid-20260926); hand-built droid is the fallback
        o = put('droid', (0, 0, 0), k='structure')
        o.location = (WX - 2.3, WY - 1.6, 0); o.rotation_euler = (0, 0, DROID_YAW)
        dd = dims('droid'); col_box('droid', (WX - 2.3, WY - 1.6, 1.5), (dd.y * .9, dd.x * 1.1, 3.0))
        for i in range(3):   # jury-rig: power leads from the pump house to the droid
            cable(Vector((4.02, 1.2 - i * .3, 2.8 - i * .2)), Vector((WX - 3.7, WY - 1.9 + i * .2, 2.2)), sag=.4, r=.025)
    else:
        with record() as obs:
            mining_droid()
        place(obs, Matrix.Translation((WX - 3.5, WY - .1, 0)) @ Matrix.Rotation(.08, 4, 'Z'))
    if not MESHY_DROID.exists() and not DROID_WALKS: col_box('droid', (WX - 3.5, WY, 1.5), (6.0, 4.4, 3.0), .08)
    # guard post: HESCO arc, turret facing the berm
    with record() as obs:
        hesco_run(5.3)
    place(obs, Matrix.Translation((WX + 2.4, -1.2, 0)) @ Matrix.Rotation(math.pi / 2, 4, 'Z'))
    col_box('aq_hesco', (WX + 2.4, -1.2, .7), (1.1, 5.3, 1.4))
    with record() as obs:
        scrap_turret()
    place(obs, Matrix.Translation((WX + 2.4, -3.4, 1.35)) @ Matrix.Rotation(math.radians(200), 4, 'Z'))


# ================================================================ Warden watchtowers at the wall corners
def watchtower(n):
    H = 8.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            ibeam('Tower leg', (sx * 1.6, sy * 1.6, 0), (sx * 1.2, sy * 1.2, H), .3, .22, mat=M['rust'])
            box('Leg footing', (.8, .8, .4), M['concrete'], (sx * 1.6, sy * 1.6, .2), bevel=.02)
    for z0, z1 in ((0.4, 3.0), (3.0, 5.8), (5.8, H)):
        f0 = 1.6 - .4 * z0 / H; f1 = 1.6 - .4 * z1 / H
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            with kind('detail'):
                span('X brace', (ax * f0, ay * f0, z0), (bx * f1, by * f1, z1), .06, .06, M['steel'], bevel=0)
                span('X brace', (bx * f0, by * f0, z0), (ax * f1, ay * f1, z1), .06, .06, M['steel'], bevel=0)
    box('Platform', (4.0, 4.0, .25), M['tread'], (0, 0, H + .12), bevel=.02)
    # armoured cabin with slit windows and a sandbagged parapet
    for (x, y, w, d) in ((0, 1.85, 3.9, .12), (0, -1.85, 3.9, .12), (1.85, 0, .12, 3.9), (-1.85, 0, .12, 3.9)):
        box('Cabin lower', (w, d, 1.1), M['plate_olive'], (x, y, H + .8), bevel=.015, uv=.5)
        box('Cabin upper', (w, d, .55), M['plate_olive'], (x, y, H + 2.25), bevel=.015, uv=.5)
        box('Slit glass', (max(w - .3, .06), max(d - .04, .06), .5), M['glass'], (x, y, H + 1.65), bevel=0)
    for (x, y) in ((1.85, 1.85), (-1.85, 1.85), (1.85, -1.85), (-1.85, -1.85)):
        box('Cabin post', (.18, .18, 2.3), M['steel'], (x, y, H + 1.4), bevel=.01)
    box('Cabin roof', (4.6, 4.6, .16), M['rust_sheet'], (0, 0, H + 2.62), (math.radians(4), 0, 0), bevel=.02)
    box('Roof trim', (4.7, .2, .2), M['hazard'], (0, 2.3, H + 2.55), bevel=.01)
    # searchlight, antenna, ladder, banner, stencil
    cyl('Searchlight', .3, .5, M['steel'], loc=(1.4, 1.4, H + 2.95), rot=(math.radians(-70), 0, math.radians(30)), sides=14)
    cyl('Search lens', .26, .04, M['amber'], loc=(1.55, 1.62, H + 3.1), rot=(math.radians(-70), 0, math.radians(30)), sides=14, k='glow')
    light_marker(f'watch_{n}', Vector((1.6, 1.9, H + 3.1)), 'amber')
    with record() as obs:
        lattice_mast(3.5, .3, True, False, f'watch_ant_{n}')
    place(obs, Matrix.Translation((-1.5, -1.5, H + 2.7)))
    for s in (-.22, .22):
        span('Ladder rail', (s, 2.1, 0), (s, 2.1, H + 1.0), .04, .04, M['steel'], bevel=0)
    for i in range(int(H / .32)):
        with kind('detail'):
            span('Rung', (-.22, 2.1, .3 + i * .32), (.22, 2.1, .3 + i * .32), .025, .025, M['steel'], bevel=0)
    banner(1.1, 3.0, (0, 1.95, H - .1))
    decal(f'stencil_watch{n}', 1.6, .5, (0, 1.92, H + .75), (math.pi / 2, 0, 0))
    with record() as obs:
        hesco_run(4.2)
    place(obs, Matrix.Translation((0, 2.9, 0)))
    col_box(f'tower_{n}', (0, 0, 1.5), (3.6, 3.6, 3.0))
    col_box(f'tower_hesco_{n}', (0, 2.9, .7), (4.2, 1.1, 1.4))


# ================================================================ Quantum Tube goods conduit along the north wall
def tube_conduit():
    Z, Hc = 42.4, 4.3
    runs = [(-47.0, -10.5), (10.5, 41.0)]
    for x0, x1 in runs:
        pts = [U(x0, Z, Hc), U(x1, Z, Hc)]
        tube('Q-conduit', pts, .5, M['dark'], sides=20, uv_len=.4, caps=True)
        L = abs(x1 - x0)
        for i in range(int(L / 1.6) + 1):
            x = x0 + (x1 - x0) * i / int(L / 1.6)
            with kind('detail'):
                cyl('Conduit rib', .56, .18, M['steel'], loc=U(x, Z, Hc), rot=(0, math.pi / 2, 0), sides=20)
            if i % 4 == 2:
                cyl('Conduit glow ring', .52, .06, M['cyan_dim'], loc=U(x + .15, Z, Hc), rot=(0, math.pi / 2, 0), sides=20, k='glow')
        for i in range(int(L / 7.5) + 1):
            x = x0 + 1.0 + (L - 2) * i / int(L / 7.5) * (1 if x1 > x0 else -1)
            box('Pylon', (.5, .5, Hc - .4), M['concrete'], U(x, Z, (Hc - .4) / 2), bevel=.03)
            box('Saddle', (.4, 1.3, .35), M['steel'], U(x, Z, Hc - .55), bevel=.02)
            col_box(f'pylon_{x:.0f}', U(x, Z, 1.5), (.6, .6, 3.0))
    # node housings where the conduit terminates either side of the Ring Gate axis
    for s in (-1, 1):
        x = s * 9.0
        box('Node housing', (2.8, 2.6, 5.4), M['plate_bone'], U(x, Z - .2, 2.7), bevel=.06, uv=.45)
        box('Node cap', (3.1, 2.9, .35), M['steel'], U(x, Z - .2, 5.55), bevel=.03)
        box('Node aperture', (.12, 1.6, 2.2), M['dark'], U(x - s * 1.42, Z - .2, 3.2), bevel=.01)
        box('Node glow', (.04, 1.3, 1.9), M['cyan'], U(x - s * 1.5, Z - .2, 3.2), bevel=0, k='glow')
        light_marker(f'node_{s}', U(x - s * 2.0, Z - .2, 3.2), 'cyan')
        box('Node plinth', (3.4, 3.2, .4), M['concrete'], U(x, Z - .2, .2), bevel=.02)
        col_box(f'node_{s}', U(x, Z - .2, 1.5), (3.0, 2.8, 3.0))
        with kind('decal'):
            o = decal('stencil_node', 2.4, .38, (0, 0, 0), (math.pi / 2, 0, 0))
            o.matrix_world = frame(x, Z - 1.52, 1.9, 0, -1) @ o.matrix_world


# ================================================================ perimeter container homes
def dwelling(mat, stacked=None, awning=True):
    container(mat=mat)
    with kind('detail'):
        put('aircon', (-1.6, -1.45, 1.2), rz=0)
        put('planter', (1.6, -1.6, 0), rz=0); put('succ', (1.6, -1.6, .42), s=.3)
        put(rng.choice(['barrel1', 'barrel2']), (-2.6, -1.7, 0), rz=1.)
    if awning:
        box('Awning', (3.0, 1.6, .04), M['tarp_rust'] if rng.random() > .5 else M['tarp'], (.6, -2.0, 2.45), (math.radians(-10), 0, 0), bevel=0)
        for x in (-.8, 2.0):
            span('Awning pole', (x, -2.7, 0), (x, -2.7, 2.35), .05, .05, M['steel'], bevel=0)
    box('Solar panel', (2.0, 1.2, .05), M['solar'], (-1.0, .2, 2.75), (math.radians(-15), 0, 0), bevel=.01)
    if stacked:
        with record() as obs:
            container(mat=stacked, door_end=False)
        place(obs, Matrix.Translation((.4, .1, 2.6)))
        for i in range(8):   # external stair
            box('Stair tread', (.9, .28, .05), M['grate'], (3.5, -1.0 + i * .3, .33 * (i + 1)), bevel=0)
        span('Stair stringer', (3.95, -1.2, 0), (3.95, 1.4, 2.7), .05, .2, M['steel'], bevel=0)


def perimeter():
    homes = [  # unity x, z, yaw (local -Y front faces the city), material, stacked
        (19.0, -41.6, 180, M['container_rust'], M['container_blue']),
        (26.5, -41.4, 180, M['container_sand'], None),
        (-27.0, 41.2, 0, M['container_olive'], None),
        (-20.0, 41.4, 0, M['container_blue'], None),
        (-56.3, -24.0, 90, M['container_sand'], M['container_rust']),
    ]
    for i, (x, z, yaw, mat, st) in enumerate(homes):
        hw, hd = (3.2, 1.5) if yaw in (0, 180) else (1.5, 3.2)
        f = find_free(x, z, hw, hd, 4.0, .1)
        if not f: WARN.append(f'home {i}: no free spot'); continue
        x, z = f
        M4 = yaw_frame(x, z, 0, yaw + 180)
        at(M4, dwelling, mat, st)
        o = col_box(f'home_{i}', (0, 0, 1.5), (6.1, 2.5, 3.0)); o.matrix_world = M4 @ o.matrix_world


# ================================================================ gate defences and street clusters
def gate_defences():
    for (x, z0, z1, n) in ((44.6, -13.5, -7.5, 1), (44.6, 19.5, 25.5, 2)):
        check_free(f'gate hesco {n}', x - .6, x + .6, z0, z1)
        M4 = frame(x, (z0 + z1) / 2, 0, -1, 0)
        at(M4, hesco_run, abs(z1 - z0))
        o = col_box(f'gate_hesco_{n}', (0, 0, .7), (abs(z1 - z0), 1.1, 1.4)); o.matrix_world = M4 @ o.matrix_world
        tz = z0 + .8 if n == 2 else z1 - .8
        at(frame(x, tz, 1.35, -1, 0), scrap_turret)
        at(frame(x - 1.5, (z0 + z1) / 2, 0, -1, 0), lambda: [put('jersey', (i * 1.7 - 1.7, 0, 0), rz=0) for i in range(3)])


def street_clusters():
    spots = [  # unity x, z, yaw, recipe
        (-19.5, -4.4, 0, 'boxes'), (-22.0, 4.4, 180, 'bins'), (19.5, 4.4, 180, 'boxes'), (22.6, 4.5, 180, 'drums'),
        (-29.5, -20.5, 0, 'gen'), (29.5, 21.0, 180, 'gen'), (-29.5, 20.5, 180, 'drums'), (29.0, -21.5, 0, 'drums'),
    ]
    for i, (x, z, yaw, recipe) in enumerate(spots):
        f = find_free(x, z, .9, .9, 3.0, .15)
        if not f: WARN.append(f'cluster {i}: no free spot'); continue
        x, z = f
        M4 = yaw_frame(x, z, 0, yaw)
        def build(recipe=recipe):
            if recipe == 'boxes':
                put('ubox2', (0, 0, 0)); put('pbox', (.75, .05, 0), rz=.2); put('pcrate', (-.7, .1, 0), rz=.4); put('pcrate', (-.7, .1, .27), rz=.2)
            elif recipe == 'bins':
                put('bin', (0, 0, 0)); put('tyre', (1.2, .1, 0), rx=math.pi / 2, rz=.3); put('tyre', (1.2, .1, .16), rx=math.pi / 2, rz=.9)
            elif recipe == 'gen':
                put('gen', (0, 0, 0)); put('lpg', (.7, .2, 0)); put('lpg', (.95, -.1, 0)); cable(Vector((0, .3, .3)), Vector((0, 2.6, 0.02)), sag=-.1)
            elif recipe == 'drums':
                for k, (dx, dy) in enumerate(((0, 0), (.62, .05), (.3, .55))): put(['barrel1', 'barrel2', 'barrel3'][k], (dx, dy, 0), rz=k)
                put('bag', (-.6, .2, 0), rz=.3); put('bag', (-.6, .25, .18), rz=.1)
        at(M4, build)
        o = col_box(f'cluster_{i}', (0, 0, .5), (1.8, 1.2, 1.0)); o.matrix_world = M4 @ o.matrix_world


def hall_banners():
    for x in (-13.6, -6.4):
        at(frame(x, -26.45, 0, 0, 1), banner, 1.1, 3.2, (0, 0, 8.4))


# ================================================================ build
group('Shop retrofits', all_shops)
group('Service lanes', lanes)
for name, fn, (x, z, yaw) in [('Processing hall ruin', processing_hall, (36.0, 34.0, 180)),
                              ('Hydroponics bays', hydroponics, (-34.0, 32.5, 180)),
                              ('Nanofab workshop', nanofab, (36.0, -33.0, 0)),
                              ('Aquifer pump station', aquifer, (-35.0, -33.0, 0))]:
    def zone(fn=fn, x=x, z=z, yaw=yaw):
        at(yaw_frame(x, z, 0, yaw), fn)
    group(name, zone)
for n, (x, z, yaw) in enumerate([(-54.5, 40.0, 180 - 45), (-54.5, -40.0, 45), (43.2, 40.0, 180 + 45), (43.2, -40.0, -45)], 1):
    group(f'Watchtower {n}', lambda n=n, x=x, z=z, yaw=yaw: at(yaw_frame(x, z, 0, yaw), watchtower, n))
group('Quantum Tube conduit', tube_conduit)
group('Perimeter dwellings', perimeter)
group('Gate defences', gate_defences)
group('Street clusters', street_clusters)
group('Hall banners', hall_banners)

# ---------------------------------------------------------------- report + export
report = {'groups': {}, 'warnings': WARN}
for root in [o for o in RETRO.all_objects if o.parent is None and o.type == 'EMPTY']:
    rows = {c.name: sum(len(p.vertices) - 2 for p in c.data.polygons) for c in root.children if c.type == 'MESH' and not c.name.startswith('COL_')}
    report['groups'][root.name] = dict(tris=rows, total=sum(rows.values()),
                                       colliders=sum(1 for c in root.children if c.name.startswith('COL_')),
                                       lights=sum(1 for c in root.children if c.name.startswith('LIGHT_')))
report['total_tris'] = sum(g['total'] for g in report['groups'].values())
(ROOT / ('geometry-report.json' if not ONLY else 'geometry-report-partial.json')).write_text(json.dumps(report, indent=1))
print('WARNINGS', *WARN, sep='\n  ')
if LIBC: bpy.context.view_layer.layer_collection.children['LIB'].exclude = True
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children['WardRetrofit']
if not ONLY:
    OUT_GLB.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(OUT_GLB), export_format='GLB', use_active_collection=True, use_active_collection_with_nested=True,
                              export_apply=True, export_yup=True, export_lights=False, export_cameras=False, export_image_format='AUTO', export_jpeg_quality=88)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND if not ONLY else ROOT / 'partial.blend'), compress=True)
print('RETROFIT_DONE', report['total_tris'])
