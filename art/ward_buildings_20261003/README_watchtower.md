# Warden corner watchtowers ×4 — 3 October 2026

Replace `Ward district retrofit/Watchtower 1…4` (steel lattice legs carrying a flat olive box; on the skyline of most
views). Concept: `concept/tower_concept_v1.png` (prompt `concept/tower_prompt.txt`). One prefab (`Watchtower`), four
instances under `Ward building: watchtowers`, each tucked into its wall corner 0.15 m off the wall faces, door to the city:

| Instance | Root (door-face centre) | Yaw |
| --- | --- | --- |
| Watchtower NW (1) | (−55.45, 0, 39.15) | 180 |
| Watchtower SW (2) | (−55.45, 0, −39.15) | 0 |
| Watchtower NE (3) | (43.45, 0, 39.15) | 180 |
| Watchtower SE (4) | (43.45, 0, −39.15) | 0 |

Construction: 4.4 × 4.4 m ashlar shaft to 9.37 m with quoins, a battered talus of dressed rough blocks with hipped
corner pieces (cut for the door), a steel door in a stone surround with step, firing slits at two levels, riveted
blackened-steel bands (2.75 / 6.2 / 8.95 m) and corner angles, a patched shell hole (riveted plate, heavy impact
cluster), soot. Observation cabin corbelled 0.62 m out on triangular knee brackets: riveted blackened steel plate,
armour shutters propped open over interior-mapped glazed slits (WS_Glass), sill ledge with sandbags, hipped steel roof
with standing seams, searchlight on a yoke (lit lens, night-only 24° spot aimed down into the yard), antenna mast with
a red beacon and guys. Warden banner down the city face; a caged ladder up the city face (ground → landing at 5.6 m →
cabin floor) so it clears the corner walls on every tower; "WARDEN POST" stencil; door lamp; sandbag wall by the door.

Colliders (10 per tower): shaft (Shop body/door pieces), talus body + two front talus pieces (door gap), ladder,
sandbags. Lights: door lamp + searchlight per tower, both on the clock (8 total; far ones are culled by the circuit).
Triangles LOD0 62k (Blender) / 77k in Unity with props, LOD1 17k, LOD2 80. Review cameras (root `Ward buildings review
cameras: watchtowers`): `cam_wb_tower_nw`, `_sw`, `_ne`, `_se`, `_door` (SW tower), `_cabin` (NW cabin from below).

Known gaps: the cabin interior is a dark box behind interior-mapped glass; the banner is plain red (no emblem UVs); the
four towers were identical — fixed in round two (four variants, README_round2.md).
