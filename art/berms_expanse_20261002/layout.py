#!/usr/bin/env python3
"""Site layout for the Outer Berms expansion (2 Oct 2026) -> sites.json (+ work/layout.png, layout-check.json).

Each site is a short brief written as data: centre, props (kit prefab, offset from the centre in metres, yaw, flags),
an encounter (spawns: worker / drone / gunner / lancer), salvage nodes (prompt wording, loot table, the prop they sit
on) and a landmark id. Offsets are rotated by the site's yaw, so a vignette can be turned to face the approach.
Everything is checked against the generated terrain (work/heightfield.npz): inside the playable floor with a margin,
slope under each footprint, spawns on walkable ground, distance between sites and from the old Berms content.
The Unity installer (BermsExpansePass install) places the props on the ground collider and wires the encounters.

Difficulty rises with distance from the West Gate: melee packs within ~200 m, single ranged droids at the mid sites,
ranged groups (gunners + lancers) at 400 m and beyond. Lancers roost near high ground; gunners hold cover lines.
Run: uv run --with numpy --with scipy --with matplotlib python layout.py
"""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
FP = json.loads((HERE / 'footprint.json').read_text())
PRE = json.loads((HERE / 'prefabs.json').read_text())

# kit shortcuts (Prefabs/ relative)
K = dict(
    heapA='OuterBermsDepot/MX_ScrapHeapA', heapB='OuterBermsDepot/MX_ScrapHeapB', crashed='OuterBermsDepot/DP_CrashedDrone',
    deadworker='OuterBermsDepot/DP_DeadWorker', shell='TrainingRange/TR_WorkerDroidShell', mining='WardMiningDroid',
    crane='OuterBermsDepot/PHD_Crane', cradle='OuterBermsDepot/DP_Cradle', cradleB='OuterBermsDepot/DP_CradleBroken',
    rack='OuterBermsDepot/DP_DroneRack', cables='OuterBermsDepot/DP_Cables', lpg='OuterBermsDepot/PHD_LpgTank',
    cart='OuterBermsDepot/PHD_StorageCart', chest='OuterBermsDepot/PHD_ToolChest', rimA='OuterBermsDepot/PHD_WheelRimA', rimB='OuterBermsDepot/PHD_WheelRimB',
    wallA='OuterBermsDepot/DP_WallA', wallB='OuterBermsDepot/DP_WallB', wallC='OuterBermsDepot/DP_WallC', wallD='OuterBermsDepot/DP_WallD',
    fenceP='OuterBermsDepot/PHD_FencePanel', fencePost='OuterBermsDepot/PHD_FencePost', voltage='OuterBermsDepot/DP_SignVoltagePost',
    tdrone='TrainingRange/TR_TrainingDrone', dock='TrainingRange/TR_DroneDock', gantry='TrainingRange/TR_TetherGantry',
    barricade='TrainingRange/TR_CoverBarricade', blast='TrainingRange/TR_BlastWall', shelter='TrainingRange/TR_ServiceShelter',
    lantern='TrainingRange/TR_Lantern', timber='TrainingRange/TR_TimberStack', bench='TrainingRange/TR_RepairBench',
    cells1='TrainingRange/TR_SpentCells_1', cells2='TrainingRange/TR_SpentCells_2', compressor='TrainingRange/TRP_compressor',
    welder='TrainingRange/TRP_welding_cart', floodpole='TrainingRange/TR_FloodPole', frame='TrainingRange/TR_DroidFrame',
    tower='WestGate/WG_GuardPost', lighttower='WestGate/WG_LightTower', flag='WestGate/WG_RangeFlag', shadenet='WestGate/WG_ShadeNet',
    sandH='WestGate/WG_SandbagWall2mHigh', sandL='WestGate/WG_SandbagWall2mLow', sandC='WestGate/WG_SandbagCurveHigh', sandP='WestGate/WG_SandbagPile',
    jersey='WestGate/PH_JerseyBarrierA', jerseyB='WestGate/PH_JerseyBarrierB', mcrateA='WestGate/PH_MilitaryCrateA', mcrateB='WestGate/PH_MilitaryCrateB',
    wcrate='WestGate/PH_WoodenMilitaryCrate', ammo='WestGate/PH_AmmoBox', radio='WestGate/PH_RadioSet', gen='WestGate/PH_Generator',
    jerry='WestGate/PH_Jerrycan', barrelB='WestGate/PH_BarrelBlue', barrelR='WestGate/PH_BarrelRed', tyre='WestGate/PH_OldTyre',
    searchlight='WestGate/PH_Searchlight', powerbox='WestGate/PH_PowerBox', utilbox='WestGate/PH_UtilityBox', notice='WestGate/WG_NoticeBoard',
    toolcart='WestGate/PH_ToolCart', handtruck='WestGate/PH_HandTruck', propane='WestGate/PH_PropaneTank', chair='WestGate/PH_MonoblocChair',
    sackA='StreetDressing/SD_sack_tied_a', sackB='StreetDressing/SD_sack_tied_b', sackC='StreetDressing/SD_sack_tied_c',
    crate='StreetDressing/SD_crate_wood', crateD='StreetDressing/SD_crate_wood_deep', crateL='StreetDressing/SD_crate_long',
    crateR='StreetDressing/SD_crate_red', crateY='StreetDressing/SD_crate_yellow', drumR='StreetDressing/SD_drum_red', drumB='StreetDressing/SD_drum_blue',
    drumS='StreetDressing/SD_drum_steel_blue', tarp='StreetDressing/SD_tarp_stack', handcart='StreetDressing/SD_handcart', skip='StreetDressing/SD_scrap_skip',
    firebarrel='StreetDressing/SD_fire_barrel', table='StreetDressing/SD_picnic_table', stool='StreetDressing/SD_stool_folding', tub='StreetDressing/SD_tub_wood',
    basket='StreetDressing/SD_basket_lidded', waterpt='StreetDressing/SD_water_point', sdtyre='StreetDressing/SD_tyre', rim='StreetDressing/SD_rim_a',
    toolbox='StreetDressing/SD_toolbox', gas='StreetDressing/SD_gas_bottle', fieldgen='StreetDressing/SD_field_generator',
    relay='Salvage/relay', whip='Rooftops/RT_Whip', dish='Rooftops/RT_Dish', mast='Rooftops/RT_CableMast', solar='Rooftops/RT_SolarFrame',
    tankT='Rooftops/RT_TankTall', tankL='Rooftops/RT_TankLow', junction='Rooftops/RT_JunctionBox', dew='Rooftops/RT_DewNet',
    pwNS='PerimeterWalls/PW_NS_intact_b_7p00', pwNSi='PerimeterWalls/PW_NS_impact_7p00', pwNSc='PerimeterWalls/PW_NS_collapse_7p00',
    pwBW='PerimeterWalls/PW_BW_intact_a_5p00', pwBWb='PerimeterWalls/PW_BW_breach_5p00', pwBWc='PerimeterWalls/PW_BW_collapse_5p00',
    pwBWr='PerimeterWalls/PW_BW_repair_5p00',
    # Meshy hero landmarks (meshy/berms-landmarks-20261002); the installer skips any prefab that is missing
    hauler='BermsExpanse/Landmarks/CaravanHaulerWreck', derrick='BermsExpanse/Landmarks/AquiferDerrick', pylon='BermsExpanse/Landmarks/TubePylonFall',
)

LOOT = dict(near='loot_scrap_heap', wreck='loot_wreck_carcass', drone='loot_drone_wreck', outer='loot_berms_outer', outpost='loot_berms_outpost')


def P(kit, dx, dz, yaw=0, **kw):
    d = dict(prefab=K[kit], at=[dx, dz], yaw=yaw); d.update(kw); return d


def S(kind, dx, dz, yaw=0):
    return dict(kind=kind, at=[dx, dz], yaw=yaw)


def H(name, dx, dz, table, prompt, progress, rng=2.4, prop=None):
    return dict(name=name, at=[dx, dz], loot=LOOT[table], prompt=prompt, progress=progress, range=rng, prop=prop)


SITES = [
    dict(id='northgate_scrap', name='Northgate scrap', centre=[-132, 64], yaw=10, tier=1,
         props=[P('heapA', 0, 0, 30), P('heapB', 6, -3, -40), P('crashed', -5, 4, 120), P('tyre', 3, 4, 0), P('rimA', -3, -4, 60), P('cells2', 8, 2, 15)],
         encounter=dict(name='Scrap drones · northgate', spawns=[S('drone', 4, 8), S('drone', -7, -6)]),
         salvage=[H('Northgate scrap heap', 1.8, 1.6, 'near', 'E · Search the scrap heap', 'Searching the scrap heap…')]),
    dict(id='caravan_ambush', name='Caravan ambush', centre=[-205, 74], yaw=-20, tier=1, landmark='berms_caravan',
         props=[P('hauler', 0, 0, 0, main=True), P('crateD', -6.5, 2.5, 15), P('crate', -7.5, 4, 70), P('crateL', -5, 5.5, -10),
                P('sackA', 6.5, -3.0, 0), P('sackB', 7.2, -2.0, 40), P('sackC', 5.8, -1.6, 80), P('tarp', 4, 4.5, 20), P('drumR', -2, -4.5, 0),
                P('drumB', -1, -5.2, 0), P('rimB', 9, 2, 90), P('sdtyre', 10, 1, 0), P('handcart', -11, -2, 140), P('deadworker', 12, -5, 200),
                P('shadenet', -13, 5, -35), P('basket', -9.5, 6.5, 0)],
         encounter=dict(name='Caravan scavengers', spawns=[S('worker', -4, -7, 180), S('worker', 7, 6, 200), S('worker', 13, -1, 260), S('drone', -10, 7)]),
         salvage=[H('Hauler cargo bed', -2.5, 2.8, 'outer', 'E · Search the hauler cargo', 'Searching the cargo bed…', 2.6),
                  H('Spilled caravan crates', -7, 3.8, 'near', 'E · Search the spilled crates', 'Searching the crates…'),
                  H('Ripped grain sacks', 6.5, -2.4, 'near', 'E · Search the torn sacks', 'Searching the sacks…')]),
    dict(id='scrapper_camp', name='Scrapper camp', centre=[-208, -40], yaw=20, tier=2, landmark='berms_scrapper_camp',
         props=[P('shadenet', 0, 0, 10), P('table', 1, 0.5, 100), P('stool', -0.8, 1.6, 30), P('stool', 2.4, -0.8, 200), P('firebarrel', 3.2, 2.8, 0),
                P('skip', -6, -3, 75), P('handcart', -4, 4.5, 160), P('tarp', 5, -3, 0), P('crateR', 6, -1.5, 25), P('crateY', 6.8, -0.4, 60),
                P('bench', -2, -4.8, 180), P('toolbox', -1.2, -4.6, 0), P('gen', 4.5, 4.5, 45), P('jerry', 5.2, 4, 0), P('heapB', -9, 1, 110),
                P('barricade', 8, 6, 120), P('barricade', 11, 1, 80), P('sandL', -10, -6, 30)],
         encounter=dict(name='Scrapper camp squatters', spawns=[S('worker', -6, 7, 160), S('worker', 9, -6, 220), S('gunner', -14, -10, 60)]),
         salvage=[H('Scrapper skip', -6, -1.2, 'outer', 'E · Search the scrap skip', 'Searching the skip…', 2.6),
                  H('Scrappers’ workbench', -2, -3.6, 'near', 'E · Search the workbench', 'Searching the bench…')]),
    dict(id='waystation', name='Warden waystation', centre=[-266, 52], yaw=-10, tier=0, landmark='berms_waystation', waystation=True,
         props=[P('shelter', 0, 0, 0, main=True), P('sandH', -4.2, -2.6, 90), P('sandH', -4.2, 1.2, 90), P('sandC', -3.4, 4, 45), P('sandH', 4.4, -2.4, 90),
                P('sandP', 4.6, 2.6, 0), P('flag', -1, 6.5, 0), P('radio', 0.8, -0.6, 0), P('gen', 2.6, 3.8, 0), P('jerry', 3.2, 3, 30),
                P('mcrateA', -2, 2.4, 10), P('mcrateB', -2, 1.2, -5), P('waterpt', 2.4, -3.6, 180), P('notice', 0, -4.2, 180), P('lantern', 1.6, 1.8, 0),
                P('chair', -0.6, 1.4, 160), P('floodpole', 6, 6, 225), P('ammo', -1.4, -1.6, 30)],
         encounter=None, salvage=[]),
    dict(id='relay_knoll', name='Relay knoll', centre=[-330, 8], yaw=20, tier=3, landmark='berms_relay_knoll',
         props=[P('relay', 0, 2, 200, main=True), P('whip', 6, -4, 0), P('dish', -6, -5, 160), P('mast', 9, 4, 0), P('solar', -9, 3, 20),
                P('sandH', 7, -9, 0), P('sandC', 3, -11, 20), P('sandH', -4, -11, 10), P('barricade', -11, -7, 30), P('ammo', 2, -9.5, 0),
                P('mcrateA', 5, -10, 15), P('junction', -3, 7, 0), P('cables', 0, -2, 90), P('cells1', -7, -9, 0), P('heapA', 12, 8, 60)],
         encounter=dict(name='Gunner nest · relay knoll', spawns=[S('gunner', 3, -8, 200), S('gunner', -6, -8, 170), S('worker', 12, 3, 220)]),
         salvage=[H('Relay equipment', -3.5, 6, 'outer', 'E · Strip the relay equipment', 'Stripping the relay gear…', 2.6),
                  H('Gunners’ ammo crates', 4.2, -9.2, 'outer', 'E · Search the ammo crates', 'Searching the crates…')]),
    dict(id='aquifer_derrick', name='Aquifer derrick', centre=[-302, 140], yaw=35, tier=3, landmark='berms_derrick',
         props=[P('derrick', 0, 0, 0, main=True), P('tankT', 8, 5, 0), P('tankL', 9, 1, 90), P('solar', -9, 4, 200), P('solar', -9, 7.5, 200),
                P('powerbox', 5, -6, 180), P('utilbox', 6, -6.2, 180), P('dew', -6, -8, 30), P('fenceP', -12, -2, 90), P('fencePost', -12, -3.2, 0),
                P('fenceP', -12, 1.4, 80), P('voltage', 4, -8, 180), P('gas', 7, -5, 0), P('heapB', 13, -6, 20), P('crashed', -15, 8, 70)],
         encounter=dict(name='Derrick pack', spawns=[S('worker', 10, -2, 250), S('worker', -6, 10, 140), S('drone', 2, 12), S('lancer', -10, -10)]),
         salvage=[H('Pump control cabinet', 5.5, -5, 'outer', 'E · Strip the pump controls', 'Stripping the control cabinet…'),
                  H('Fallen drone', -15, 8, 'drone', 'E · Salvage the crashed drone', 'Salvaging the drone…', 2.6)]),
    dict(id='wash_scrapyard', name='Wash scrapyard', centre=[-292, -106], yaw=-15, tier=3, landmark='berms_scrapyard',
         props=[P('crane', 0, 0, 30, main=True), P('mining', -9, 5, 150), P('heapA', 7, 6, 10), P('heapB', 10, 1, 70), P('heapA', -12, -6, 200),
                P('shell', 4, -7, 300), P('deadworker', -4, -9, 120), P('crashed', 12, -6, 210), P('cradleB', -14, 2, 30), P('lpg', 15, 5, 90),
                P('cart', -6, 11, 20), P('rimA', 2, 9, 0), P('rimB', 3, 10, 60), P('cables', -2, 4, 150), P('chest', 8, -10, 160)],
         encounter=dict(name='Scrapyard pack', spawns=[S('worker', -4, 6, 180), S('worker', 9, -2, 260), S('drone', -10, -10), S('drone', 13, 9), S('lancer', 0, -14)]),
         salvage=[H('Mining droid carcass', -9, 3.5, 'wreck', 'E · Strip the mining droid carcass', 'Stripping the carcass…', 3.0),
                  H('Scrapyard heap', 7, 4.6, 'outer', 'E · Search the scrap heap', 'Searching the scrap heap…'),
                  H('Stripped worker shell', 4, -5.8, 'wreck', 'E · Strip the worker shell', 'Stripping the shell…')]),
    dict(id='mesa_roost', name='Mesa roost', centre=[-366, 86], yaw=40, tier=3, landmark='berms_mesa_roost',
         props=[P('rack', 0, 0, 0, main=True), P('cradle', -4, 3, 20), P('cradleB', 4, 3, -15), P('dock', -7, -2, 60), P('crashed', 6, -4, 120),
                P('crashed', -9, 6, 300), P('tdrone', 1, 4.5, 200), P('cells2', -2, -4, 0), P('cells1', 3, -6, 40), P('gantry', 9, 3, 90)],
         encounter=dict(name='Mesa drone roost', spawns=[S('drone', -3, 7), S('drone', 5, 8), S('drone', -8, -4), S('lancer', 2, -8)]),
         salvage=[H('Drone cradles', -0.5, 2.6, 'drone', 'E · Search the drone cradles', 'Searching the cradles…', 2.6)]),
    dict(id='tube_pylon', name='Fallen Tube pylon', centre=[-424, -96], yaw=-30, tier=4, landmark='berms_tube_pylon',
         props=[P('pylon', 0, 0, 0, main=True), P('cables', 8, 4, 30), P('junction', -6, 6, 90), P('crashed', 10, -5, 40), P('cradleB', -9, -5, 110),
                P('heapB', 13, 3, 0), P('sandL', -12, 8, 70), P('barricade', 6, 12, 15)],
         encounter=dict(name='Lancer roost · Tube pylon', spawns=[S('lancer', -6, 8), S('lancer', 8, -8), S('drone', 12, 6)]),
         salvage=[H('Tube conduit', -6, 5, 'outer', 'E · Strip the Tube conduit', 'Stripping the conduit…', 2.8),
                  H('Downed lancer', 10, -5, 'drone', 'E · Salvage the downed drone', 'Salvaging the drone…', 2.6)]),
    dict(id='west_outpost', name='West fans outpost', centre=[-486, -24], yaw=80, tier=5, landmark='berms_west_outpost',
         props=[P('pwNS', 0, 9, 0, main=True), P('pwNSi', 7.6, 9, 0), P('pwNSc', -7.6, 9, 0), P('pwBW', 12, 4.2, 90), P('pwBWb', 12, -1.2, 90),
                P('pwBWc', -12, 4.5, 90), P('tower', -9, -6, 30), P('sandH', 3, -6, 0), P('sandC', 6, -7, 30), P('sandH', -1, -7, 0),
                P('jersey', 9, -9, 20), P('jerseyB', -4, -11, -10), P('searchlight', -8, -3, 200), P('mcrateA', 2, 4, 0), P('mcrateB', 3.2, 4.2, 15),
                P('wcrate', -2, 5, 90), P('ammo', 0.5, 5.6, 0), P('radio', -1.2, 3.4, 30), P('gen', 6, 4, 0), P('lighttower', 9, 7, 180),
                P('flag', -5, 6.5, 0), P('notice', 4, 7.6, 180), P('barrelR', 7.5, 2, 0), P('barrelB', 8.3, 2.6, 0)],
         encounter=dict(name='Outpost holdouts', spawns=[S('gunner', 2, -4, 180), S('gunner', -6, -9, 200), S('lancer', 0, 14), S('worker', 9, -4, 200), S('worker', -12, -2, 150)]),
         salvage=[H('Warden arms crates', 2.6, 3.4, 'outpost', 'E · Search the Warden arms crates', 'Searching the arms crates…', 2.6),
                  H('Outpost radio bench', -1.6, 4.2, 'outpost', 'E · Strip the outpost radio', 'Stripping the radio…'),
                  H('Generator housing', 6, 3, 'outer', 'E · Strip the generator', 'Stripping the generator…')]),
    dict(id='south_ridge', name='South ridge roost', centre=[-352, -176], yaw=0, tier=4, landmark='berms_south_ridge',
         props=[P('rack', 0, 0, -20, main=True), P('cradle', 3, 3, 0), P('crashed', -5, 2, 80), P('lpg', 6, -3, 0), P('cells2', -2, -3, 30)],
         encounter=dict(name='Ridge drones', spawns=[S('drone', -4, 6), S('drone', 5, 7), S('lancer', 0, -9)]),
         salvage=[H('Ridge drone rack', 0.8, 1.6, 'drone', 'E · Search the drone rack', 'Searching the rack…')]),
    dict(id='north_dunes', name='North dunes wreck', centre=[-468, 132], yaw=-40, tier=4, landmark='berms_north_dunes',
         props=[P('shell', 0, 0, 40, main=True), P('heapA', 5, 3, 0), P('tarp', -4, 2, 30), P('crateD', -3, -3, 20), P('sdtyre', 3, -4, 0)],
         encounter=dict(name='Dune scavengers', spawns=[S('worker', 4, 7, 200), S('drone', -6, 6), S('gunner', -10, -8, 120)]),
         salvage=[H('Dune scrap heap', 4.6, 1.6, 'outer', 'E · Search the scrap heap', 'Searching the scrap heap…')]),
]

# trail cairns: Warden route markers between sites (every ~28 m), so a 500 m plain has readable ways through it
ROUTES = [
    [[-104, 12], [-126, 30], [-170, 44], [-222, 50], [-262, 48]],               # depot rise -> waystation
    [[-262, 48], [-300, 30], [-322, 20]],                                       # waystation -> relay knoll
    [[-262, 58], [-280, 100], [-298, 128]],                                     # waystation -> derrick
    [[-322, 4], [-380, -6], [-440, -18], [-478, -22]],                          # relay knoll -> west outpost
    [[-112, -62], [-160, -70], [-210, -82], [-262, -98], [-284, -104]],         # depot -> scrapyard (south)
]

# tutorial core changes (existing encounters): first contact moves out past the depot rise and becomes a pair;
# the depot nest gains a worker on its west approach and a drone over the yard
TUTORIAL = dict(
    first_contact=[dict(kind='drone', world=[-128, 21]), dict(kind='drone', world=[-134, 13])],
    depot_extra=[dict(kind='worker', world=[-90, -27], yaw=60), dict(kind='drone', world=[-71, -33], yaw=0)],
)


def main():
    hf = np.load(HERE / 'work/heightfield.npz')
    Hh = hf['H']; N, CELL, OX, OZ = hf['grid']; inF = hf['playable']; din = hf['d_in']
    gz, gx = np.gradient(Hh.astype(float), CELL); slope = np.degrees(np.arctan(np.hypot(gx, gz)))

    def idx(x, z): return int(round((z - OZ) / CELL)), int(round((x - OX) / CELL))
    def h(x, z): j, i = idx(x, z); return float(Hh[j, i])
    def sl(x, z, r):
        j, i = idx(x, z); rr = max(1, int(math.ceil(r))); return float(slope[j - rr:j + rr + 1, i - rr:i + rr + 1].max())
    def inside(x, z, margin=0):
        j, i = idx(x, z); return bool(inF[j, i]) and float(din[j, i]) >= margin
    def nudge(w, r):
        """Nearest walkable spot (slope under 22 deg, inside the floor) within 9 m."""
        for rad in np.arange(1.0, 9.5, 0.75):
            for a in np.linspace(0, 2 * math.pi, 16, endpoint=False):
                q = [round(w[0] + rad * math.cos(a), 2), round(w[1] + rad * math.sin(a), 2)]
                if inside(*q, 6) and sl(q[0], q[1], r) < 22: return q
        return w

    out = dict(version=1, note='Generated by layout.py; offsets in metres rotated by the site yaw.', sites=[], routes=[], tutorial=TUTORIAL)
    problems = []; report = []
    for s in SITES:
        cx, cz = s['centre']; c, sn = math.cos(math.radians(s['yaw'])), math.sin(math.radians(s['yaw']))
        def world(d):  # Unity yaw: +y rotation turns +Z toward +X
            dx, dz = d; return [round(cx + dx * c + dz * sn, 2), round(cz - dx * sn + dz * c, 2)]
        site = dict(s); site['props'] = []
        for p in s['props']:
            w = world(p['at']); pre = PRE.get(p['prefab'] + '.prefab'); fp = max(pre['size'][0], pre['size'][2]) / 2 if pre else 3.0
            q = dict(p, world=w, yaw=(p['yaw'] + s['yaw']) % 360, ground=round(h(*w), 2), slope=round(sl(w[0], w[1], fp), 1), missing=pre is None)
            if not inside(*w, 4): problems.append(f"{s['id']}: prop {p['prefab']} outside the floor at {w}")
            site['props'].append(q)
        if s.get('encounter'):
            enc = dict(s['encounter']); enc['spawns'] = []
            for sp in s['encounter']['spawns']:
                w = world(sp['at'])
                if sp['kind'] in ('worker', 'gunner') and sl(w[0], w[1], 1.0) > 26:
                    w = nudge(w, 1.0); site.setdefault('nudged', []).append(sp['kind'])
                e = dict(sp, world=w, yaw=(sp['yaw'] + s['yaw']) % 360, ground=round(h(*w), 2), slope=round(sl(w[0], w[1], 1.0), 1))
                if not inside(*w, 6): problems.append(f"{s['id']}: spawn outside/near the edge at {w}")
                if e['slope'] > 30 and sp['kind'] not in ('drone', 'lancer'): problems.append(f"{s['id']}: walker spawn on {e['slope']} deg at {w}")
                enc['spawns'].append(e)
            site['encounter'] = enc
        site['salvage'] = [dict(n, world=world(n['at']), ground=round(h(*world(n['at'])), 2)) for n in s['salvage']]
        site['centre_ground'] = round(h(cx, cz), 2)
        site['gate_distance'] = round(math.hypot(cx + 58, cz), 1)
        out['sites'].append(site)
        report.append((s['id'], site['gate_distance'], s['tier'], len(site['encounter']['spawns']) if site.get('encounter') else 0))
    # site spacing
    for a in SITES:
        for b in SITES:
            if a['id'] < b['id']:
                d = math.hypot(a['centre'][0] - b['centre'][0], a['centre'][1] - b['centre'][1])
                if d < 55: problems.append(f"{a['id']} and {b['id']} only {d:.0f} m apart")
    for r in ROUTES:
        pts = []
        for k in range(len(r) - 1):
            a, b = np.array(r[k], float), np.array(r[k + 1], float); L = float(np.hypot(*(b - a))); n = max(1, int(L // 28))
            for t in range(n): q = a + (b - a) * (t / n); pts.append([round(float(q[0]), 1), round(float(q[1]), 1)])
        pts.append(r[-1]); out['routes'].append(pts)
    (HERE / 'sites.json').write_text(json.dumps(out, indent=1) + '\n')
    (HERE / 'layout-check.json').write_text(json.dumps(dict(problems=problems, sites=[dict(id=i, gate_m=g, tier=t, droids=n) for i, g, t, n in report]), indent=1) + '\n')
    for i, g, t, n in report: print(f'{i:18s} {g:6.1f} m  tier {t}  droids {n}')
    print('problems:', len(problems)); [print('  ', p) for p in problems]
    # plot
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    x0, x1, z0, z1 = -580, -50, -240, 230
    j0, j1 = idx(x0, z0)[0], idx(x1, z1)[0]; i0, i1 = idx(x0, z0)[1], idx(x1, z1)[1]
    sub = Hh[j0:j1, i0:i1].astype(float); gz2, gx2 = np.gradient(sub)
    hs = np.clip(0.6 - 0.45 * gx2 - 0.65 * gz2, 0, 1)
    fig, ax = plt.subplots(figsize=(15, 13)); ax.imshow(hs, cmap='gray', origin='lower', extent=(x0, x1, z0, z1))
    poly = np.array(FP['playable'] + [FP['playable'][0]]); ax.plot(poly[:, 0], poly[:, 1], '-', color='orange', lw=1.2)
    col = dict(worker='red', drone='orange', gunner='magenta', lancer='purple')
    for s in out['sites']:
        ax.text(s['centre'][0], s['centre'][1] + 9, s['name'], fontsize=8, ha='center', color='navy')
        for p in s['props']: ax.plot(*p['world'], 's', ms=3, color='saddlebrown' if not p['missing'] else 'gray')
        if s.get('encounter'):
            for e in s['encounter']['spawns']: ax.plot(*e['world'], 'o', ms=6, color=col[e['kind']])
        for n in s['salvage']: ax.plot(*n['world'], '*', ms=9, color='gold')
    for r in out['routes']:
        r = np.array(r); ax.plot(r[:, 0], r[:, 1], '.', color='green', ms=5)
    for f in TUTORIAL['first_contact'] + TUTORIAL['depot_extra']: ax.plot(*f['world'], 'o', ms=6, color=col[f['kind']], mec='k')
    ax.set_xlim(x0, x1); ax.set_ylim(z0, z1); ax.grid(alpha=.25)
    fig.savefig(HERE / 'work/layout.png', dpi=70, bbox_inches='tight')


if __name__ == '__main__':
    main()
