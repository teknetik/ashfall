# DOCS_SNIPPET — wall-foot sand and grounding (1 Oct 2026)

## For unity/EDITING.md — new section "Wall-foot sand and grounding (1 October 2026)"

**Ward wall-foot drifts** holds 334 prefab instances of an eight-piece sand kit (`Prefabs/WallFootDrifts/WFD_Run_L/M/S`,
`Run_Low`, `Corner_L/S`, `Post`, `Sheet`; LOD0–2, culled past ~60 m, no shadows or colliders) and 320 URP decal
projectors, grouped per building (`Relay Works` … `Thread + Hide`, `Basic General`, `Vanguard Hall`, `Hill plinth and
stairs`, `Posts`, `Shop alleys`), each group with a `Decals` child. Banks sit on the measured wall-foot lines, heavier on
faces into the west-south-west wind and in inside corners; step middles, doors, bays, props, routes and NPC points stay
clear. The drifts are not a render-chunk source: move, duplicate or delete instances directly (uniform scale only; keep
a bank's sand on its own level — not hanging off a porch edge).

- **Look:** sand material `Art/WallFootDrifts/Materials/WFD_Sand` (URP Lit; tint `_BaseColor`, 1.5 m tile). Decal
  materials `WFD_DecalFootBand` (ground film along the banks), `WFD_DecalWallSkirt` (contact grime and dust coat on
  walls), `WFD_DecalPost`, `WFD_DecalSheet`; per projector edit Fade Factor, Size and position (draw distance 40 m). They
  use `Art/WallFootDrifts/Shaders/WFD_Decal.shadergraph`, a copy of the Ward weathering decal graph with **angle fade on**
  (the shared graph has it off, which paints ground decals onto risers and props).
- **Geometry or layout:** `art/wall_foot_drifts_20261001` (`author_drift_kit.py`, `faces.py`, `probe_faces.py`,
  `layout.py`, `make_textures.py`), then **Athen Hill → Wall-foot drifts → Build assets** (prefabs and materials update
  in place). Re-placing everything needs `reinstall` (authoring only). `layout.py --check --audit <audit>` re-validates
  the installed placements against a fresh scene audit.
- Review cameras `cam_wfd_*` (**Wall-foot drift review cameras**); evidence `evidence/wall-foot-drifts/20261001`.
- **Rollback:** deactivate the root (or delete it and the review-camera root); the pre-install scene is
  `evidence/wall-foot-drifts/20261001/rollback/before-wall-foot-drifts.unity`. Nothing was retired.

## For AGENTS.md §3 baseline table — one row

| Wall-foot sand | 1 Oct 2026 (`art/wall_foot_drifts_20261001`, scene root **Ward wall-foot drifts**): 334 wind-laid sand banks (8-piece kit, LOD0–2, no shadows/colliders) on the measured feet of the eight shops, Basic General, Vanguard Hall, the hill plinth and stair cheeks, inside corners, step ends, posts and the shop alleys, plus 320 decals (sand film, wall dust/grime skirt, post collars, alley sheets; own angle-fading copy of the Ward decal graph). Heavier on west-south-west-facing faces; doors, step middles, props, routes and NPC points clear. Not yet accepted by Carl. |
