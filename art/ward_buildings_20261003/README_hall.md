# Processing 11 ruin (NE yard) — 3 October 2026

Replaces `Ward district retrofit/Processing hall ruin` (grey precast columns, marbled concrete panels, a bare truss and
rubble cones). Lore-neutral: a pre-war ore processing hall shelled long ago and never rebuilt. Concept:
`concept/hall_concept_v1.png` (prompt `concept/hall_prompt.txt`). Scene root `Ward building: Processing 11 ruin`,
instance at world (36, 0, 33), yaw 0 (local = world − (36, 0, 33)); footprint world x 28…44, z 27.6…38.4, kept clear of
the NE watchtower's door and ladder.

Construction (`Ruin` class): a 0.8 m double-faced ashlar city wall (south) with a broken stepped top (8.1 m in the west,
falling to 2.2 m at the east end), three tall barred windows (some bars missing, two bent) with through-stone sills and
flat arches with keystones, a 3.4 × 4.3 m cart door under a riveted steel lintel with a worn threshold, three punched
shell holes, soot plumes over the openings, heavy impact clusters, a Warden banner and a painted "PROCESSING 11" stencil;
a west wall stepping down to the north with a window; five ashlar piers (1.1 m, riveted steel bands; two snapped with
knocked-off top courses and rubble lodged on top) and a toppled sixth lying in a line of fallen courses; crane rails on
steel corbels, one snapped end hanging; a stranded yellow crane bridge with trolley, chains and hook block; one intact
roof truss, one sagged onto a broken pier, purlins, a few corrugated sheets (one hanging loose, three fallen); a fallen
bent truss segment; rubble heaps of loose blocks under the broken tops and sand mounds.

Colliders (17): wall pieces (with the door gap), west wall, piers, toppled pier, heaps, fallen truss. No lights (a ruin;
night is dark here). Triangles LOD0 153k, LOD1 30k, LOD2 0.2k. Review cameras (root `Ward buildings review cameras:
Processing 11`): `cam_wb_hall_apron` (from the spawn apron), `_city`, `_door`, `_inside`, `_east`, `_wall` (shell holes).

Known gaps: the windows are flat-arched, not round (the concept's round arches need spandrel stones); the hall's north
side is open toward the wall and the Quantum Tube conduit; no conveyor spine (the old one ran into the rampart).
