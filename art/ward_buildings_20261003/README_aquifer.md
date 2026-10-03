# AQUIFER 3 pump station (SW quadrant) — 3 October 2026

Replaces `Ward district retrofit/Aquifer pump station` (a plain marbled box with a monopitch roof, a flat green door
panel and a pipe elbow; `audit/editor/audit_aquifer.png`). Lore: aquifer infrastructure — how Ward survives. Concept:
`concept/aquifer_concept_v1.png` (prompt `concept/aquifer_prompt.txt`). Scene root `Ward building: Aquifer 3`, instance
at world (−35, 0, −30.5), yaw 0 (street face north, 2.5 m from the mining droid's patrol line at z −28; moved 0.5 m south
of the old front so the droid clears the hoist), tanks behind at world z −39.5, well head east at world (−27.4, −31.5).

| Part | Construction |
| --- | --- |
| Pump hall | 9 × 6.4 m Ward ashlar hall, 6.26 m to a moulded cornice and parapet (Shop class `top()`), quoins, string course; riveted blackened-steel corner straps over the quoins at three heights plus heavier corner shoe plates; battle damage, soot over the windows, runoff, leak stain under the main's wall entry. |
| Front | Riveted double steel doors under a flat arch with keystone and glazed transom; a 0.95 m hoist beam with chain block and hook hung up high (pump columns come out through this door); barred ground and upper windows, louvred steel vents; stencils "AQUIFER 3" and "POTABLE - NO ENTRY"; Warden banner; two door lamps. |
| Roof | Clerestory ventilation monitor (steel frame, louvres on both long sides, pitched corrugated cap with ridge roll); AC unit. |
| Well head | Dressed stone kerb, flanged steel casing with bolts, red valve wheel, teal rising main (WB_PipeTeal) with flanges on two braced H-frame trestles into the east wall; well lamp on the east wall. |
| Tanks | Three riveted steel storage tanks (bone, teal, rust) on dressed round stone plinths: banded shells with rivet rows, conical roofs and vents, caged ladders, roof rails; the rust tank carries riveted patch plates over old shell holes; outlet pipes into the rear wall and a header along it. |
| Guard post | Sandbag walls (West Gate kit prefabs) by the well, where the old HESCO post stood. |
| Rear | Teal steel door with lamp, downpipe. Props: tool cart, drums, jerrycan (Street dressing kit). |

Colliders (13): Shop body and door pieces, well head, two trestles, three tanks, guard sandbags. Lamps: four shop-family
wall lamps on the Ward lighting clock. Triangles LOD0 98k (Blender) / 129k in Unity with lamps and props, LOD1 34k,
LOD2 0.2k. Review cameras (root `Ward buildings review cameras: Aquifer 3`): `cam_wb_aquifer_market`, `_front`, `_door`,
`_well`, `_tanks`, `_droid` (from the mining droid's patrol).

Known gaps: the walking mining droid still patrols the yard but nothing ties it to the pump any more (the old retrofit
had the "knelt droid as pump" idea, already replaced by the walker in Sep); the tanks' paint read dark grey in shade (fixed in round two: WB_Tank* materials, cylindrical UVs).
