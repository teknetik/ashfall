# Docs snippet — Ward rooftops (1 Oct 2026)

For the orchestrator to merge. Not yet accepted by Carl.

## unity/EDITING.md section

## Ward rooftops and service lines (1 October 2026)

**Ward rooftops** (scene root) breaks the shop cornices where the avenue sees them. It has one child per shop roof
(*Relay Works roof*, *Air + Water roof*, … *Thread + Hide roof*) whose transform equals that shop's root, so the pieces under
it are in the shop's own frame (origin = facade centre at paving level, +Z towards the avenue), and **Service lines**
(world space): two conductors across each cross street between roof masts, short lines across the two narrow alleys and
four conduit drops from the masts down the side walls into junction boxes. Pieces are prefab instances of
`Prefabs/Rooftops/RT_<id>.prefab` (tanks, dew/condensate net, PV frame, cowls, turbine vents, whip, dish, service-line
masts, guard rails, shade frame, caged ladders, wall hooks, junction boxes; LOD0/LOD1, shadows only on the two tanks) plus
three street-kit props on the Salvage terrace (shadows off as instance overrides). Nothing was retired and no render-chunk
source changed; there are no lights.

- Move, add or delete deck pieces in the Scene view (keep them inside the parapets and 1.8 m from the Repairs flue and
  Salvage stovepipe smoke). The **spans and drops are meshes generated from the layout**, so moving a mast or junction box
  means editing `art/rooftops_20261001/layout.py` (which validates decks, roof furniture, smoke, windows/doors, routes and
  roof clearance), then `author_cables.py` (Blender) and **Athen Hill → Rooftops → Build assets**; rebuilt prefabs update the
  instances. Kit geometry: `author_roof_kit.py`; maps: `make_textures.py`.
- Materials: the shops' `VH_*`/`WS_*` and the street kit's `SD_Sack`/`SD_Rope` (shared, so their Inspector edits apply here
  too) plus `Art/Rooftops/Materials/RT_DewNet` (alpha-clipped, double-sided net; *Base Map* tiling 4 = 0.25 m tiles),
  `RT_SolarCell` and `RT_Ceramic`.
- Ladders carry a box collider over their bottom 2.2 m; on the roofs only the three street-kit props keep their own boxes.
- **Install (one time)** refuses to run twice (authoring: `RooftopsPass.Reinstall()` replaces the root from `layout.json`);
  **Verify saved scene** writes `evidence/rooftops/20261001/verify-saved-scene.json`. Review cameras `cam_rt_*` (under
  *Rooftops review cameras*): four along the avenue rows and two into the cross streets, all at 1.62 m.
  Evidence, rollback scene and remaining defects: `evidence/rooftops/20261001/README.md`.

## AGENTS.md baseline-table row

| Rooftops and service lines | 1 Oct 2026 (`art/rooftops_20261001`, scene root **Ward rooftops**): one or two pieces per shop roof that break the cornices from the avenue and say how Ward lives (Finery and Thread + Hide water tanks, Air + Water dew/condensate nets, Tool Exchange PV panels, Relay whip, Repairs dish, Field Supply ridge vents, Salvage shade terrace with rail, Finery and Thread + Hide rails, cowls), service lines on pin-insulator masts across both cross streets and the alleys, conduit drops into junction boxes, two caged ladders. 44 instances, LOD0 67k tris (LOD1 28k), shadows on the two tanks only, no lights; clear of the night-life smoke columns. Not yet accepted by Carl. |
