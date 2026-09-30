# Ward masonry kit (30 Sep 2026)

Shared Blender (5.2, headless) helpers for Ward's authored stone buildings, extracted from the Vanguard Hall script
and extended after Carl's review of the hall ("walls in full shade look flat, stone edges are too clean close up, the
rain stains are too faint") and his follow-up ("everything needs a little more weathering, dirt, grime and general
'this place saw a battle take place long ago'", with the West Gate arches as the look he likes).

Used by `art/vanguard_hall_20260930/author_vanguard_hall.py` and `art/hall_district_20260930/author_ward_shops.py`
(and `author_ward_signs.py` for its geometry builder). See the module docstring of `ward_masonry.py`.

What the kit writes for **Athen Hill/Masonry Lit** (Art/VanguardHall/Shaders):

| Channel | Meaning | Source |
| --- | --- | --- |
| COLOR.rgb | per-block tint × broad 2–4 m drift × wall-foot soil splash × soot plumes | `stone_tint`, `Part.build(macro, splash)`, `ScarSet.plume` |
| COLOR.a | sky occlusion, ray traced against the building and ground (rays start 9 cm out) | `AOBaker` |
| UV1.x | rain runoff weight under drip edges (cornices, sills, string courses, scuppers, lamps, plates) | `DripSet` |
| UV1.y | worn arris: 1 on bevel faces, 0.75 on the dressed margin next to them | `ashlar_block`, `Part.finalize` |
| UV2.x | rust trails under steel (corbels, brackets, lamps, awning arms, lintels) | `DripSet(kind="rust")` |
| UV2.y | old battle damage (impact clusters): dense pitting, shrapnel scars, cracks | `ScarSet.impact`, `scatter_impacts` |

Geometry (LOD0): dressed blocks get a 1–4.5 cm inset margin, a slightly cushioned face, bevelled arrises split every
15 cm (< 2.4 m above the ground) or 30 cm (< 4.2 m) and eroded with 3D noise; chips and spalls dig out corners
(more at the wall foot); mortar sits 2.6 cm behind the faces. Meshes are probe-lit only (UV1/UV2 carry wear data).

`make_streak_texture.py` writes `Art/VanguardHall/Textures/WardRunoff_Streaks.png` (R grime runoff, G mineral deposit,
B rust trails; tileable, sampled in world space).

Gotchas found while building it (30 Sep): `bmesh.ops.bevel`'s `faces` output includes the neighbours it reshapes (tag
new faces through a temporary material index instead); `bmesh.ops.inset_individual` needs `face.normal_update()` first
or it insets by zero; open edges cannot be bevelled (keep the bed faces at LOD0); a chip that tilts a whole face
behind the mortar plane reads as a dark blotch.
