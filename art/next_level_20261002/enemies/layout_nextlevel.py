#!/usr/bin/env python3
"""Next-level enemy POIs for the Outer Berms expanse (2 Oct 2026) -> sites.json, layout-check.json, work/layout.png.

Four points of interest in the outer third of the ~495 x 425 m bowl, away from the twelve expansion sites and the Warden
trail routes, each with kit dressing (the street-dressing / West Gate / depot / training-range / rooftop kits used by the
expansion), an encounter of the three new higher-level droids, loot crates (strongbox salvage nodes on military crates), a
QA landmark and `cam_nextlevel_*` review cameras at player height. Validated like art/berms_expanse_20261002/layout.py:
inside the playable floor with a margin, slope under each footprint, droid spawns on walkable ground, >= 60 m from every
expansion site centre, >= 25 m from the trail cairns, and props clear of the expansion's rock/scrub scatter (scatter items
inside a prop footprint are listed so the installer parks them).
Run: uv run --offline --with numpy --with matplotlib python layout_nextlevel.py"""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BX = HERE.parent.parent / 'berms_expanse_20261002'
FP = json.loads((BX / 'footprint.json').read_text())
PRE = json.loads((BX / 'prefabs.json').read_text())
SITES_BX = json.loads((BX / 'sites.json').read_text())
SCATTER = json.loads((BX / 'scatter.json').read_text())['items']

K = dict(
    heapA='OuterBermsDepot/MX_ScrapHeapA', heapB='OuterBermsDepot/MX_ScrapHeapB', crashed='OuterBermsDepot/DP_CrashedDrone',
    deadworker='OuterBermsDepot/DP_DeadWorker', shell='TrainingRange/TR_WorkerDroidShell', rack='OuterBermsDepot/DP_DroneRack',
    cradle='OuterBermsDepot/DP_Cradle', cradleB='OuterBermsDepot/DP_CradleBroken', cables='OuterBermsDepot/DP_Cables', lpg='OuterBermsDepot/PHD_LpgTank',
    chest='OuterBermsDepot/PHD_ToolChest', rimA='OuterBermsDepot/PHD_WheelRimA', wallA='OuterBermsDepot/DP_WallA', wallB='OuterBermsDepot/DP_WallB',
    fenceP='OuterBermsDepot/PHD_FencePanel', fencePost='OuterBermsDepot/PHD_FencePost', voltage='OuterBermsDepot/DP_SignVoltagePost',
    barricade='TrainingRange/TR_CoverBarricade', blast='TrainingRange/TR_BlastWall', shelter='TrainingRange/TR_ServiceShelter', lantern='TrainingRange/TR_Lantern',
    timber='TrainingRange/TR_TimberStack', bench='TrainingRange/TR_RepairBench', cells1='TrainingRange/TR_SpentCells_1', cells2='TrainingRange/TR_SpentCells_2',
    frame='TrainingRange/TR_DroidFrame', floodpole='TrainingRange/TR_FloodPole', dock='TrainingRange/TR_DroneDock',
    tower='WestGate/WG_GuardPost', flag='WestGate/WG_RangeFlag', shadenet='WestGate/WG_ShadeNet', sandH='WestGate/WG_SandbagWall2mHigh', sandL='WestGate/WG_SandbagWall2mLow',
    sandC='WestGate/WG_SandbagCurveHigh', sandP='WestGate/WG_SandbagPile', jersey='WestGate/PH_JerseyBarrierA', jerseyB='WestGate/PH_JerseyBarrierB',
    mcrateA='WestGate/PH_MilitaryCrateA', mcrateB='WestGate/PH_MilitaryCrateB', wcrate='WestGate/PH_WoodenMilitaryCrate', ammo='WestGate/PH_AmmoBox',
    radio='WestGate/PH_RadioSet', gen='WestGate/PH_Generator', jerry='WestGate/PH_Jerrycan', barrelB='WestGate/PH_BarrelBlue', barrelR='WestGate/PH_BarrelRed',
    tyre='WestGate/PH_OldTyre', searchlight='WestGate/PH_Searchlight', powerbox='WestGate/PH_PowerBox', utilbox='WestGate/PH_UtilityBox', notice='WestGate/WG_NoticeBoard',
    handtruck='WestGate/PH_HandTruck', propane='WestGate/PH_PropaneTank', chair='WestGate/PH_MonoblocChair',
    sackA='StreetDressing/SD_sack_tied_a', sackB='StreetDressing/SD_sack_tied_b', crate='StreetDressing/SD_crate_wood', crateD='StreetDressing/SD_crate_wood_deep',
    crateL='StreetDressing/SD_crate_long', drumR='StreetDressing/SD_drum_red', drumB='StreetDressing/SD_drum_blue', drumS='StreetDressing/SD_drum_steel_blue',
    tarp='StreetDressing/SD_tarp_stack', handcart='StreetDressing/SD_handcart', skip='StreetDressing/SD_scrap_skip', firebarrel='StreetDressing/SD_fire_barrel',
    table='StreetDressing/SD_picnic_table', stool='StreetDressing/SD_stool_folding', sdtyre='StreetDressing/SD_tyre', toolbox='StreetDressing/SD_toolbox',
    gas='StreetDressing/SD_gas_bottle', fieldgen='StreetDressing/SD_field_generator', ammoA='StreetDressing/SD_ammo_crate_a', ammoB='StreetDressing/SD_ammo_crate_b',
    relay='Salvage/relay', whip='Rooftops/RT_Whip', dish='Rooftops/RT_Dish', mast='Rooftops/RT_CableMast', solar='Rooftops/RT_SolarFrame', junction='Rooftops/RT_JunctionBox',
    tankL='Rooftops/RT_TankLow', pwNS='PerimeterWalls/PW_NS_intact_b_7p00', pwNSi='PerimeterWalls/PW_NS_impact_7p00', pwNSc='PerimeterWalls/PW_NS_collapse_7p00',
    pwBWb='PerimeterWalls/PW_BW_breach_5p00', pwBWc='PerimeterWalls/PW_BW_collapse_5p00',
)
LOOT = dict(crate='loot_nextlevel_crate', strongbox='loot_nextlevel_strongbox', near='loot_scrap_heap', outer='loot_berms_outer')


def P(kit, dx, dz, yaw=0, **kw): d = dict(prefab=K[kit], at=[dx, dz], yaw=yaw); d.update(kw); return d
def S(kind, dx, dz, yaw=0): return dict(kind=kind, at=[dx, dz], yaw=yaw)
def C(name, kit, dx, dz, yaw, table, prompt='E · Force the strongbox', progress='Forcing the strongbox…', rng=2.4):
    """A loot crate: a kit crate prop with a salvage-node search on top of it."""
    return dict(name=name, prefab=K[kit], at=[dx, dz], yaw=yaw, loot=LOOT[table], prompt=prompt, progress=progress, range=rng)


# Difficulty: all four sit at or beyond the expansion's tier-4/5 sites. The sentinel pair roams; the Reaper pack rushes;
# the camp pairs a Reaper with a sentinel on the wall; the southern cache has two Reapers and a sentinel with the best crates.
SITES = [
    dict(id='post_relay', name='Post relay', centre=[-432, 22], yaw=15, tier=6, landmark='nextlevel_post_relay',
         brief='A courier relay the Post sentinels still keep: a toppled relay mast, a dead-letter cache and a pair of rolling sentinels on patrol.',
         props=[P('mast', 0, 0, 20, main=True), P('junction', 2.5, 1.5, 110), P('solar', -5, 3, 200), P('dish', 4.5, -3.5, 160), P('sandL', -4, -5, 20),
                P('sandP', 5, 4, 0), P('powerbox', -3, 6, 190), P('cables', 1, -3, 70), P('handcart', -8, 7, 140), P('sackA', -6.6, 6.2, 0), P('sackB', -7.4, 5.6, 60),
                P('cells1', -6, -2, 0), P('barricade', -9, -6, 110), P('notice', -1.5, 4.8, 200)],   # east side kept open for the approach (nl2: the QA walk got stuck on the cart/sack line)
         encounter=dict(name='Post sentinels · relay', spawns=[S('sentinel', -9, -9, 40), S('sentinel', 10, 7, 220)]),
         crates=[C('Dead-letter strongbox', 'mcrateA', -1.2, 2.2, 25, 'strongbox', 'E · Force the dead-letter strongbox', 'Forcing the strongbox…'), C('Courier cache', 'mcrateB', 0.9, 3.4, 110, 'crate', 'E · Search the courier cache', 'Searching the courier cache…')],
         salvage=[]),
    dict(id='reaper_den', name='Reaper den', centre=[-242, 142], yaw=-35, tier=6, landmark='nextlevel_reaper_den',
         brief='A drone rack dragged into the lee of the north wash where the Scrap Reapers strip what the caravans drop.',
         props=[P('rack', 0, 0, 0, main=True), P('cradleB', -4, 3, 30), P('heapA', 5, 4, 60), P('heapB', -6, -4, 200), P('shell', 7, -3, 300), P('deadworker', -2, -7, 120),
                P('crashed', 9, 3, 220), P('tarp', 3, -6, 20), P('drumR', -7, 1, 0), P('drumS', -7.8, 1.6, 40), P('rimA', 2, 7, 0), P('cells2', -1, 5, 30),
                P('frame', 11, -1, 90), P('fenceP', -10, -3, 80), P('fencePost', -10, -4.2, 0)],
         encounter=dict(name='Scrap Reaper pack', spawns=[S('reaper', -5, 8, 160), S('reaper', 8, -7, 300), S('reaper', 10, 6, 230)]),
         crates=[C('Stripped cargo strongbox', 'wcrate', -2.5, -2.8, 70, 'strongbox', 'E · Force the cargo strongbox', 'Forcing the strongbox…'),
                 C('Reaper cache', 'crateD', 4.2, 1.0, 120, 'crate', 'E · Search the stripped crate', 'Searching the crate…')],
         salvage=[dict(name='Den scrap heap', at=[5, 4.4], loot=LOOT['outer'], prompt='E · Search the scrap heap', progress='Searching the scrap heap…', range=2.4)]),
    dict(id='ironclad_camp', name='Fans camp', centre=[-492, -108], yaw=60, tier=7, landmark='nextlevel_ironclad_camp', approach_dir=[-0.83, 0.55],   # the camp's long wall faces the gate; approach from the open north-west side
         brief='A walled camp under the western fans, picked over by a Reaper with a Post sentinel on the wall (the delivered "Ironclad Warden" model turned out to be Brann; the id, landmark and camera names were kept).',
         props=[P('pwNS', 0, 8, 0, main=True), P('pwNSc', -7.6, 8, 0), P('pwNSi', 7.6, 8, 0), P('pwBWb', 11.5, 3, 90), P('pwBWc', -11.5, 3.5, 90),
                P('shadenet', 0, 0, 10), P('table', 1.2, 0.6, 100), P('stool', -0.6, 1.8, 30), P('chair', 2.6, -0.9, 200), P('firebarrel', 3.4, 3.0, 0),
                P('gen', -5, 4.5, 45), P('jerry', -5.8, 4, 0), P('tower', -8, -5, 30), P('sandH', 3, -7, 0), P('sandC', 6.5, -7.5, 30), P('sandH', -2, -8, 0),
                P('jersey', 9, -8, 20), P('searchlight', -7, -2, 200), P('barrelR', 7.5, 2, 0), P('barrelB', 8.3, 2.6, 0), P('timber', -8, 2, 100), P('lantern', 1.8, 2.2, 0),
                P('flag', -4, 6.5, 0)],
         encounter=dict(name='Camp holdouts', spawns=[S('reaper', 4, -3, 190), S('sentinel', -8, -9, 150)]),
         crates=[C('Caravan strongbox', 'wcrate', -1.5, 4.8, 95, 'strongbox', 'E · Force the caravan strongbox', 'Forcing the strongbox…'),
                 C('Camp arms crate', 'mcrateA', 4.6, 5.2, 10, 'crate', 'E · Search the arms crate', 'Searching the arms crate…')],
         salvage=[]),
    dict(id='southern_cache', name='Southern cache', centre=[-252, -152], yaw=-10, tier=7, landmark='nextlevel_southern_cache',
         brief='A collapsed pump house at the south wash: two Reapers and a Post sentinel guard the richest cache in the Berms.',
         props=[P('wallA', 0, 6, 0, main=True), P('wallB', 6.5, 6, 0), P('wallC' if 'wallC' in K else 'wallA', -6.5, 6, 0), P('blast', 9, 1, 90), P('tankL', -4, 3.5, 20),
                P('voltage', 5, -2, 180), P('utilbox', 3.5, 3.8, 180), P('lpg', -8, -1, 90), P('chest', 1, 2.8, 160), P('cables', -2, -2, 150),
                P('skip', -9, -6, 75), P('heapB', 9, -6, 20), P('dock', -3, -7, 60), P('sandL', 6, -9, 10), P('barricade', -8, 4, 120), P('cells1', 2, -5, 0)],
         encounter=dict(name='Cache guard', spawns=[S('reaper', 0, -2, 180), S('reaper', 8, -3, 250), S('sentinel', -9, -10, 20)]),
         crates=[C('Pump-house strongbox', 'wcrate', -1.2, 3.6, 10, 'strongbox', 'E · Force the pump-house strongbox', 'Forcing the strongbox…'),
                 C('Buried arms crate', 'mcrateB', 1.8, 3.2, 95, 'crate', 'E · Search the arms crate', 'Searching the arms crate…'),
                 C('Spare-parts crate', 'ammoB', 3.0, -0.6, 40, 'crate', 'E · Search the parts crate', 'Searching the parts crate…')],
         salvage=[dict(name='Pump-house heap', at=[9, -5.6], loot=LOOT['outer'], prompt='E · Search the scrap heap', progress='Searching the scrap heap…', range=2.4)]),
]
CAMERAS = [  # name, position offset from the centre (metres, world axes), height, target offset, fov
    ('cam_nextlevel_post_relay', [-432, 22], [26, -14], 1.7, [0, 0], 2.0, 58),
    ('cam_nextlevel_reaper_den', [-242, 142], [22, -18], 1.7, [0, 0], 1.8, 58),
    ('cam_nextlevel_ironclad_camp', [-492, -108], [24, 12], 1.7, [0, 0], 2.2, 58),
    ('cam_nextlevel_southern_cache', [-252, -152], [20, 16], 1.7, [0, 0], 2.0, 58),
    ('cam_nextlevel_sentinel_close', [-432, 22], [-12, -12], 1.6, [-9, -9], 1.2, 45),
    ('cam_nextlevel_ironclad_close', [-492, -108], [7, -6], 1.6, [4, -3], 1.3, 45),
]


def main():
    hf = np.load(BX / 'work/heightfield.npz')
    Hh = hf['H']; N, CELL, OX, OZ = hf['grid']; inF = hf['playable']; din = hf['d_in']
    gz, gx = np.gradient(Hh.astype(float), CELL); slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    def idx(x, z): return int(round((z - OZ) / CELL)), int(round((x - OX) / CELL))
    def h(x, z): j, i = idx(x, z); return float(Hh[j, i])
    def sl(x, z, r):
        j, i = idx(x, z); rr = max(1, int(math.ceil(r))); return float(slope[j - rr:j + rr + 1, i - rr:i + rr + 1].max())
    def inside(x, z, margin=0):
        j, i = idx(x, z); return bool(inF[j, i]) and float(din[j, i]) >= margin
    def nudge(w, r):
        for rad in np.arange(1.0, 9.5, 0.75):
            for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
                q = [round(w[0] + rad * math.cos(a), 2), round(w[1] + rad * math.sin(a), 2)]
                if inside(*q, 6) and sl(q[0], q[1], r) < 22: return q
        return w
    cairns = [p for r in SITES_BX['routes'] for p in r]
    out = dict(version=1, note='Generated by layout_nextlevel.py; offsets in metres rotated by the site yaw (Unity: +yaw turns +Z toward +X).', sites=[], cameras=[])
    problems = []; report = []; parked = []
    for s in SITES:
        cx, cz = s['centre']; c, sn = math.cos(math.radians(s['yaw'])), math.sin(math.radians(s['yaw']))
        def world(d): dx, dz = d; return [round(cx + dx * c + dz * sn, 2), round(cz - dx * sn + dz * c, 2)]
        site = dict(s); site['props'] = []; site['crates'] = []
        if not inside(cx, cz, 14): problems.append(f"{s['id']}: centre too near the edge")
        for other in SITES_BX['sites']:
            d = math.hypot(cx - other['centre'][0], cz - other['centre'][1])
            if d < 60: problems.append(f"{s['id']}: only {d:.0f} m from expansion site {other['id']}")
        dc = min(math.hypot(cx - p[0], cz - p[1]) for p in cairns)
        if dc < 25: problems.append(f"{s['id']}: {dc:.0f} m from a trail cairn")
        for p in s['props'] + s['crates']:
            w = world(p['at']); pre = PRE.get(p['prefab'] + '.prefab'); fp = max(pre['size'][0], pre['size'][2]) / 2 if pre else 3.0
            q = dict(p, world=w, yaw=(p['yaw'] + s['yaw']) % 360, ground=round(h(*w), 2), slope=round(sl(w[0], w[1], fp), 1), missing=pre is None, footprint=round(fp, 2))
            if not inside(*w, 4): problems.append(f"{s['id']}: {p['prefab']} outside the floor at {w}")
            if pre is None: problems.append(f"{s['id']}: unknown prefab {p['prefab']}")
            if q['slope'] > 24 and p.get('main'): problems.append(f"{s['id']}: main prop on {q['slope']} deg")
            for it in SCATTER:
                if math.hypot(it['x'] - w[0], it['z'] - w[1]) < fp + 1.2 * it['scale'] + 0.3:
                    parked.append(dict(site=s['id'], prefab=it['prefab'], x=it['x'], z=it['z'], kind=it['kind']))
            (site['crates'] if 'loot' in p else site['props']).append(q)
        enc = dict(s['encounter']); enc['spawns'] = []
        for sp in s['encounter']['spawns']:
            w = world(sp['at'])
            if sl(w[0], w[1], 1.0) > 24: w = nudge(w, 1.0); site.setdefault('nudged', []).append(sp['kind'])
            e = dict(sp, world=w, yaw=(sp['yaw'] + s['yaw']) % 360, ground=round(h(*w), 2), slope=round(sl(w[0], w[1], 1.0), 1))
            if not inside(*w, 6): problems.append(f"{s['id']}: spawn outside/near the edge at {w}")
            if e['slope'] > 30: problems.append(f"{s['id']}: spawn on {e['slope']} deg at {w}")
            enc['spawns'].append(e)
        site['encounter'] = enc
        site['salvage'] = [dict(n, world=world(n['at']), ground=round(h(*world(n['at'])), 2)) for n in s['salvage']]
        site['centre_ground'] = round(h(cx, cz), 2); site['gate_distance'] = round(math.hypot(cx + 58, cz), 1)
        toGate = np.array(s.get('approach_dir') or [-58 - cx, 0 - cz], float); toGate /= np.linalg.norm(toGate)
        ap = [round(float(cx + toGate[0] * 22), 2), round(float(cz + toGate[1] * 22), 2)]
        if sl(ap[0], ap[1], 1.0) > 24: ap = nudge(ap, 1.0)
        site['approach'] = ap
        out['sites'].append(site); report.append((s['id'], site['gate_distance'], s['tier'], len(enc['spawns']), len(site['crates'])))
    for a in SITES:
        for b in SITES:
            if a['id'] < b['id'] and math.hypot(a['centre'][0] - b['centre'][0], a['centre'][1] - b['centre'][1]) < 60: problems.append(f"{a['id']} and {b['id']} too close")
    for name, centre, off, height, toff, theight, fov in CAMERAS:
        pos = [centre[0] + off[0], centre[1] + off[1]]; tgt = [centre[0] + toff[0], centre[1] + toff[1]]
        if not inside(pos[0], pos[1], 2): problems.append(f'{name}: camera outside the floor')
        out['cameras'].append(dict(name=name, pos=[pos[0], height, pos[1]], target=[tgt[0], theight, tgt[1]], fov=fov, note='above ground height'))
    # parked scatter: unique
    seen = set(); uniq = []
    for p in parked:
        k = (p['x'], p['z'])
        if k not in seen: seen.add(k); uniq.append(p)
    for st in out['sites']:
        pr = [c['prompt'] for c in st['crates']]
        if len(set(pr)) != len(pr): problems.append(f"{st['id']}: duplicate crate prompts {pr}")
    out['parked_scatter'] = uniq
    (HERE / 'sites.json').write_text(json.dumps(out, indent=1) + '\n')
    (HERE / 'layout-check.json').write_text(json.dumps(dict(problems=problems, parked_scatter=len(uniq), sites=[dict(id=i, gate_m=g, tier=t, droids=n, crates=cr) for i, g, t, n, cr in report]), indent=1) + '\n')
    for i, g, t, n, cr in report: print(f'{i:18s} {g:6.1f} m  tier {t}  droids {n}  crates {cr}')
    print('parked scatter:', len(uniq)); print('problems:', len(problems)); [print('  ', p) for p in problems]
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        x0, x1, z0, z1 = -580, -50, -240, 230
        j0, j1 = idx(x0, z0)[0], idx(x1, z1)[0]; i0, i1 = idx(x0, z0)[1], idx(x1, z1)[1]
        sub = Hh[j0:j1, i0:i1].astype(float); gz2, gx2 = np.gradient(sub); hs = np.clip(0.6 - 0.45 * gx2 - 0.65 * gz2, 0, 1)
        fig, ax = plt.subplots(figsize=(14, 12)); ax.imshow(hs, cmap='gray', origin='lower', extent=(x0, x1, z0, z1))
        poly = np.array(FP['playable'] + [FP['playable'][0]]); ax.plot(poly[:, 0], poly[:, 1], '-', color='orange', lw=1.2)
        for s in SITES_BX['sites']: ax.plot(*s['centre'], 'x', color='navy'); ax.text(s['centre'][0], s['centre'][1] + 6, s['id'], fontsize=7, ha='center', color='navy')
        col = dict(reaper='magenta', sentinel='cyan')
        for s in out['sites']:
            ax.text(s['centre'][0], s['centre'][1] + 10, s['name'], fontsize=9, ha='center', color='darkred', weight='bold')
            for p in s['props']: ax.plot(*p['world'], 's', ms=3, color='saddlebrown')
            for e in s['encounter']['spawns']: ax.plot(*e['world'], 'o', ms=7, color=col[e['kind']])
            for cr in s['crates']: ax.plot(*cr['world'], '*', ms=10, color='gold')
            ax.plot(*s['approach'], '^', ms=7, color='green')
        for c in out['cameras']: ax.plot(c['pos'][0], c['pos'][2], 'v', ms=6, color='purple')
        ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.grid(alpha=.25); (HERE / 'work').mkdir(exist_ok=True)
        fig.savefig(HERE / 'work/layout.png', dpi=70, bbox_inches='tight')
    except ImportError: print('matplotlib unavailable: no plot')


if __name__ == '__main__': main()
