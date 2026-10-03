# Nanofab 2 workshop (SE yard) — 3 October 2026

Replaces `Ward district retrofit/Nanofab workshop` (26 Sep: a flat teal "glass" box with a white cap, five ribs, a flat
grey door slab and two plain containers in front; `audit/editor/audit_nanofab.png`). Lore: the colony's one working
nanofab ("NANOFAB 2"). Concept: `concept/nanofab_concept_v1.png` (prompt `concept/nanofab_prompt.txt`). Scene root
`Ward building: Nanofab 2`, instance at world (36, 0, −28), yaw 0 (street face north, toward the spawn apron), on the
old 14 × 10 m footprint (world x 29…43, z −28…−38).

| Part | Construction |
| --- | --- |
| Ground storey | Ward ashlar 0–4.75 m with quoins and a string course (5.0 m), rough plinth course, battle damage (kit `ScarSet` scatter plus six heavy impact clusters on the street piers, under the patched panel and on the rear), soot plumes over the bay and a west window, runoff under every sill/lintel/band. |
| Corner piers | 1.05 m ashlar piers projecting 0.3 m on all four corners to 9.05 m, courses alternately owning the corner like quoins, weathered chamfered caps; riveted blackened steel bands at 1.25 / 4.92 / 7.05 / 8.75 m (the West Gate arch look); torn Warden banners on the two street piers. |
| Upper module | Sci-fi retrofit clean-room skin 5.0–8.45 m: graphite composite panels (WS_PanelDark, a few WB_CompositeScorched burned and WB_CompositeFresh replaced), raised borders and corner bolts, riveted steel sill/head beams and posts every 2.4 m, a proud cyan status strip (WB_LedCyan) in a dark channel, louvred vents, two blown-out panels behind riveted patch plates; painted stencils "NANOFAB 2" (street) and "FAB 2" (rear). |
| Loading bay | 4.5 × 3.9 m opening in the stone with stone reveals, riveted box lintel, hazard-striped steel channel frame with bump guards, roller box and a half-raised slatted shutter (bottom bar at 2.05 m). Behind it a lit steel-lined room (deck floor, safety line, LED bar) with the fabricator: plinth, four-post gantry with yellow cross beam and cyan LED bars, glazed print chamber with LED rings and a glowing bed, servo arm, console with screen, feedstock canisters. Two always-on interior point lights ("Unclocked lights"). A collider stops the player at the shutter line. |
| Door side | Single steel personnel door in a stone surround, steel canopy on tie rods, access panel with a cyan screen, conduit, junction box, barred window, "NO NAKED FLAME" stencil, downpipe. |
| Roof | Three fan housings with grilles, duct run to a 7.2 m exhaust stack with rust bands, platform, railing and ladder; roof hatch; rusted AC unit. |
| East | Process-gas bank: four bone/red cylinders with colour bands on a rough stone plinth, strapped to the wall, gas lines into the wall under the string course; lamp. |
| West | Corrugated lean-to on three rust-steel posts over a scrap-sorting bay (Street dressing crates, drums, hand truck, field generator mounted as props). |
| Rear | Olive steel door, barred window, lamp, AC unit, power box and conduit, downpipe. |

Colliders (17): body + front piers/over-door/door pieces from the Shop class, four pier boxes, gas bank, lean-to posts
and stock. Lamps: four PH_WallLamp shop-family lamps (bay west, between bay and door, rear door, gas bank) on the Ward
lighting clock (practical + night-only). Triangles LOD0 113k (Blender) / 146k in Unity with lamps and props.
Review cameras (root `Ward buildings review cameras: Nanofab 2`): `cam_wb_nanofab_apron` (from the spawn apron),
`_front`, `_bay`, `_door`, `_east` (the gap to the rampart), `_west` (lean-to).

Known gaps: the gas cylinders' paint texture streaked on the curved faces (fixed in round two: cylindrical UVs, WB_Cyl* materials); the interior is a shallow set
(4.2 m), not enterable; the fabricator is authored geometry, not a hero asset; no decals (rust/grime come from the
masonry shader and the WB materials).
