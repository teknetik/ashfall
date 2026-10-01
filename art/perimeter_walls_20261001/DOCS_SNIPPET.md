# Docs snippet: perimeter walls (1 Oct 2026) — for the orchestrator to merge

## unity/EDITING.md section

### Perimeter walls (1 Oct 2026)

The north/south curtain walls, the +X rampart either side of the District gate arches (and the slot between them), the
strip wall beyond it and the -X Outer Berms walls are a modular kit on the Ward masonry: 32 module prefabs in
`Prefabs/PerimeterWalls/PW_<kind>_<variant>_<length>.prefab`, 87 instances under the scene root **Ward perimeter walls**
(one child per wall). Each prefab is a LODGroup (LOD0 bevelled and chipped ashlar within ~16 m, LOD1 to ~45 m, flat-block
LOD2 beyond) plus one ShadowsOnly massing mesh used at every LOD (inset 9 cm behind the lit faces, so the stone never
self-shadows and shadows never pop between LODs); fittings, field repairs and rubble cones cast their own shadows.

- Sources: `art/perimeter_walls_20261001` (`pw_layout.py` → `layout.json`; `author_perimeter_walls.py` → the GLBs in
  `Art/PerimeterWalls/Models`, ~1 min for all kinds; `pw_validate.py` checks every module footprint against a scene
  audit). Rebuild assets: `PerimeterWallsPass.RunBatch --steps build,verify` (menu Athen Hill → Perimeter walls).
- Editing: move, swap or delete module instances in the Scene view (uniform transforms only; modules run along local +X,
  city face +Z, origin on the wall centreline at the paving). They are **not** render-chunk sources. To swap a bay, drag
  another `PW_*` prefab of the same length into its place.
- Collision is unchanged: the saved boxes `AuthoredWorld/COL_BLD_boundary_wall*`, `COL_BLD_west_wall*`,
  `COL_BLD_berms_gate_wall_*` and `COL_BLD_boundary_side` still enclose the city, so the visual collapses and the siege
  breach stay blocked. Nine low convex colliders sit on the rubble cones.
- Retired (inactive, kept for rollback): the old `AuthoredWorld/BLD_boundary_*`, `BLD_west_wall*`, `BLD_wall_buttress*`,
  `BLD_wall_inset*`, `BLD_wall_signal*`, `BLD_berms_gate_wall_*` visuals and the `Wall shadow proxy` objects
  (`install.json` lists them). Scene before the install: `unity/evidence/perimeter-walls/20261001/rollback/`.
- Story beats: the District gate flanks (shell craters, soot, a broken merlon, stitched cracks), the south wall collapse at
  x 7–14, the north wall collapse at x -42..-49 behind the Quantum Tube, and the West Gate portal flank of the Berms wall
  (shell damage, a collapse, then the old siege breach closed with HESCO, sandbags and a welded sheet screen).
- Review cameras `cam_pw_*` (22, under "Perimeter wall review cameras") for `unity/tools/lookbook.py`.
- Gotcha: a shadow-only proxy that coincides with the lit stone faces puts the whole wall in its own shadow (URP biases do
  not cover it); keep proxies inset behind the faces.

## AGENTS.md baseline-table row

| Perimeter walls | 1 Oct 2026 (`art/perimeter_walls_20261001`, scene root **Ward perimeter walls**): 87 instances of a 32-module Ward-masonry kit (north/south curtain walls with merlons and piers, the +X rampart with buttresses and wall walk either side of the District gate, the strip wall, the -X Berms walls): weathered, repaired, broken-parapet and shell-damaged bays, two collapsed tops and the old siege breach by the West Gate portal closed with HESCO and welded sheet. LOD0–2 + inset shadow massing; saved wall colliders unchanged; old wall visuals inactive. Not yet accepted by Carl. |
