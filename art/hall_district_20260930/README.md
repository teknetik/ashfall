# Hall district rebuild — shops, signs, grime (30 September 2026)

Carl (30 Sep 2026), after the Vanguard Hall rebuild:
1. "Fix the Hall's own weak spots: walls in full shade look flat, stone edges are too clean close up, and the rain
   stains are too faint."
2. "Rebuild the neighbouring buildings to the same standard: modelled stone, proper doorways, lamps on the city's
   day/night timing. That way the Hall doesn't stand alone."
3. "I don't like the signs so much. I designed one I like a little more in Meshy for General. See if you can do better."
4. "If you rebuild the tool shop remember sci-fi not woodworking shop from the 90s as it looks now."
5. "Everything needs a little more weathering, dirt, grime and general 'this place saw a battle take place long ago'.
   I think it's the West Gate, where the player spawns … I like its look."

## Targets (generated with Codex image_gen; not yet shown to or accepted by Carl)

- `concept/street-concept-a.png` (`prompt-street.txt`, refs `ref-hall-concept.png`, `ref-ingame-west-row.png`).
- `concept/sign-family-concept-a.png` (`prompt-signs.txt`, ref `ref-carl-basic-general-sign.png` = Carl's Meshy sign).

## What was built

Five shops on the existing standard parcels (facade 18.1 m from the avenue axis, 7.6 m wide, 6.9 m deep; the kept
porch/step colliders define the 0.5 m porch and single 0.25 m step), all from `author_ward_shops.py` on the shared
masonry kit (`art/ward_masonry_kit`):

| Shop | Parcel (world) | Construction |
| --- | --- | --- |
| Relay Works | (−18.1, −18), yaw 90 | two storeys, quoins, workshop roller shutter under a riveted steel beam, red service door, three upper windows, comms mast and dish, rooftop AC |
| Air + Water | (−18.1, −9), yaw 90 | two storeys, flat-arch double steel doors, barred windows, roof water tank; the accepted 29 Sep filter bank stays mounted on the plain south wall |
| Tool Exchange | (−18.1, 9), yaw 90 | low workshop, glazed display alcove lined in dark steel with cyan LED strips and a Meshy sci-fi set (nanofab bench, powered tool wall, servo arm, drone, plasma cutter), glazed access door, cyan status strip and panel |
| Finery | (18.1, −18), yaw −90 | tallest (8 m + cornice with dentils), glazed double doors under a flat arch, two big shop windows, teal louvred shutters, patched canvas awning |
| Field Supply | (18.1, −9), yaw −90 | stone ground floor, corrugated steel gable roof with louvred vent, loading shutter under a tie-rod canopy, teal door |

Every shop: rear service door with lamp, side windows, cornice or eave course, parapet/coping, downpipes, conduit,
junction boxes, sand drifts, three warm wall lamps (practical + night-only lights on the Ward lighting clock),
LOD0 55–74k / LOD1 13–17k triangles, box colliders with open door recesses (0.4 m deep, walkable).

Signs (`author_ward_signs.py`): folded riveted steel box with chamfered corners and weather cap, recessed graphite panel,
modelled amber channel letters (emissive, on the light clock), slim cyan status strip and lamp, standoff brackets and a
conduit feed. Basic General keeps Carl's layout (name over a red OPEN lightbox) at his sign's position.

Weathering/battle wear (kit + shader, applied to the hall and the shops): ray-traced vertex occlusion, cushioned faces,
eroded and chipped arrises, deeper spalls, runoff and rust channels, impact clusters (pitting, shrapnel scars, cracks),
soot plumes above chosen openings, heavier wall-foot dirt, darker grime-packed joints.

## Run order

1. `blender -b --python-exit-code 1 -P author_ward_shops.py [-- shop ...]` → `unity/AthenHill/Assets/AthenHill/Art/WardShops/Models/<Shop>_LOD0/1.glb` + `<shop>.json`, `shops-source.blend`.
2. `blender -b --python-exit-code 1 -P author_ward_signs.py` → `Art/WardShops/Signs/Sign_<key>.glb` + `signs.json`, `signs-source.blend`.
3. Unity (Editor/WardShopsPass.cs), menu **Athen Hill → Ward shops**: *Build assets* (materials + prefabs), *Dry-run
   install*, *Install rebuilt shops* (one-time), *Keep Air + Water filter bank*, *Fit Tool Exchange display props*,
   *Install signs*, *Refresh models and materials* (after re-running 1–2), *Verify saved scene*.
4. Hall: `art/vanguard_hall_20260930/author_vanguard_hall.py`, then **Athen Hill → Vanguard Hall → Apply weathering pass**.

Fonts: `fonts/README.md`. Meshy props: `meshy/tool-exchange-scifi-20260930/README.md`. Evidence:
`unity/evidence/hall-district/20260930/README.md`.
