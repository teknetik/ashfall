# The chosen night-life layout (executed by night_layout.py, which validates it and writes night-layout.json).
# Posts: the existing Ward utility post (merged-part runtime variant), head along yaw, a downward warm spot at the lamp.
# Brackets: the existing Ward utility wall fixture, snapped in Unity onto the wall surface found by a ray from (x, y, z)
# along into_yaw (so it sits on the real masonry, not on the old box collider).

# -- courtyard south of the hill: behind the mission terminals, lights the court, the terminals' backs and the Finery front
post("Lamp courtyard terminals", "courtyard", 8.0, -16.8, 90, note="court between the terminals, the Finery and the hall")
# -- Vanguard Hall east corner (refuse point) and the walk down to the Lattice court
post("Lamp hall corner", "hall corner", -2.5, -31.2, 90, note="hugs the hall's east wall, 1 m off the pier line")
# -- Lattice Jack court: the far side of the pad, so the gate reads framed by two pools with the hall corner lamp
post("Lamp Lattice court", "Lattice court", 5.1, -39.4, 270, note="east of the Lattice pad, clear of the bollards")
# -- hill-foot benches on the west side of the plinth, between the two benches
post("Lamp hill benches", "hill benches", -8.0, 0.2, 270, note="against the plinth between the benches, head over the west lane")
# -- West Gate spawn apron, both sides of the District gate arches, at the rampart foot
post("Lamp apron south", "spawn apron", 44.0, -14.0, 270, note="rampart foot south of the gate defences")
post("Lamp apron north", "spawn apron", 44.6, 18.5, 270, note="rampart foot north of the arches")
# -- south wall: the collapse (x 7-14) from its east side, and the lane behind the hall
post("Lamp south collapse", "south collapse", 14.3, -41.4, 270, note="east of the collapse rubble, head towards it")
bracket("Wall lamp south lane", "south wall", -22.0, 3.4, -42.3, 180, note="south wall inner face, the lane behind the hall")
bracket("Wall lamp south lane west", "south wall", -10.0, 3.4, -42.3, 180, note="south wall inner face behind the hall")
# -- north collapse behind the Quantum Tube (x -42..-49)
post("Lamp north collapse", "north collapse", -44.0, 39.6, 0, note="city side of the tube, head towards the collapse")
# -- East rampart feet (inner face x ~45.8), south and north of the apron
bracket("Wall lamp rampart south", "rampart foot", 44.8, 3.6, -26.0, 90, note="east rampart inner face by the nanofab yard")
# (no bracket north of the arches: the processing-hall ruin fills the rampart foot from z 28 to 40, and the apron north
#  post lights the free stretch; a first install put a bracket on the ruin's pale wall, removed by the relayout step)

# -- mission terminal screens: a small unshadowed cool fill in front of each screen (night only)
TERMINAL_FILLS = [
    dict(terminal="Mission Terminal Upgrade/Mission Terminal 01", local=[0.0, 1.32, 0.95], color=[0.45, 0.86, 1.0], intensity=0.75, range=3.0),
    dict(terminal="Mission Terminal Upgrade/Mission Terminal 02", local=[0.0, 1.32, 0.95], color=[0.45, 0.86, 1.0], intensity=0.75, range=3.0),
    dict(terminal="Mission Terminal Upgrade/Mission Terminal 03", local=[0.0, 1.32, 0.95], color=[0.45, 0.86, 1.0], intensity=0.75, range=3.0),
]

# -- ambient life: anchors are resolved in Unity from the named renderers (mesh vertices), so they sit on the real geometry
EFFECTS = [
    dict(kind="barrel_fire", name="Barrel fire", anchor="Ward street dressing/Market edge: rest spot/fire_barrel", note="inside the rim"),
    dict(kind="flue_smoke", name="Repairs flue smoke", renderer="Ward shops (north avenue)/Repairs/LOD0/Repairs_Metal_LOD0",
         near=[19.85, 4.83], radius=0.45, note="forge flue up the south wall, rain cap"),
    dict(kind="flue_smoke", name="Salvage stovepipe smoke", renderer="Ward shops (north avenue)/Salvage/LOD0/Salvage_Metal_LOD0",
         near=None, radius=0.3, note="roof shed stovepipe: the highest metal on the shop"),
    dict(kind="steam_puffs", name="Air + Water relief steam", renderer="Ward shop architecture/Air + Water filter fittings/AW_FilterHeader",
         near=[-17.71, -7.9], radius=0.35, note="relief on the filter header, puffs out from the wall"),
    dict(kind="exhaust_haze", name="Generator exhaust haze", anchor="Ward street dressing/East yard: generator and fuel/field_generator",
         note="faint exhaust over the yard generator"),
]
