# Docs snippet: basin mountains (1 Oct 2026) — for the orchestrator to merge

## unity/EDITING.md section (add under "Mountains and terrain")

### Basin mountains (1 Oct 2026)

The backdrop ring outside the walls is now the scene root **Basin mountains**: a prefab instance of
`Art/Terrain/BasinMountains/BasinMountains.glb` with eight chunks `BasinMountains_00…07` (the old sector split,
185,257 triangles in all), material `Materials/Terrain/SandstoneBasinV3.mat` (shader Ward Desert Terrain V2). The old
`Desert Landscape/DesertBasin_00…07` chunks stay in the scene inactive for rollback, with `SandstoneBasinV2.mat`. The
basin is render-only (no colliders) and is not a render-chunk source.

- **Sources** in `art/basin_mountains_20261001` (`run_all.sh`: numpy heightfield with stream-power erosion, strata benches
  and talus → RTIN mesh → Blender glb, about 2 min through the capped wrappers). The layout is the 8 Sep generator's
  (front escarpment, crest ring, distant ring). Re-export rather than editing the glb; chunk borders are shared vertices,
  so never edit one chunk alone.
- **Outer Berms edge**: inside the Berms ground footprint (X −104…−60, Z −54…48) and 0.75 m around it the new surface
  equals the old basin exactly (the Berms ground mesh was built as that surface + 4 cm), so the toe is untouched; the new
  terrain blends in by 7 m. The Berms ground itself still carries the old basin's facets on its west and south slopes (up
  to 11 m); rebuilding it from the new basin is a Berms ground task.
- **Haze** (V3 material Inspector, values in `art/basin_mountains_20261001/material.json`): the V2 shader has five new
  haze-shape properties whose defaults reproduce the old haze: *Far haze starts* / *Density beyond the far start* (V3:
  100 m / 0.28, so the haze matches the Berms ground out to 138 m and thins beyond), *Haze height falloff* / *Height
  falloff base* (32 m above 6 m: ridge tops keep their form at noon), *High-sun haze tint* (a linear multiplier used only
  under a high, strong sun). `_RockSlope` 0.06 (V2: 0.075) exposes more rock on the new slopes.
- **Review cameras**: `cam_bm_*` under **Basin mountains review cameras** (player height on the Berms ground, rebuilt by
  `--steps addcams` from `art/basin_mountains_20261001/review_cameras.json`); skyline views use `cam_hill`,
  `cam_avenue`, `cam_courtyard`, `cam_westgate_mouth`, `cam_berms_road`, `cam_berms_overview`.
- **Rebuild / reinstall**: `BasinMountainsPass.RunBatch --steps material` re-applies `material.json` (overwrites
  Inspector edits on V3); `--steps verify` checks the saved scene; `install` refuses to run twice. Rollback: deactivate
  **Basin mountains** and reactivate the eight `Desert Landscape` children, or restore
  `unity/evidence/basin-mountains/20261001/rollback/`.

## AGENTS.md baseline-table row

| Basin mountains | 1 Oct 2026 (`art/basin_mountains_20261001`, scene root **Basin mountains**): the backdrop ring re-authored from the original layout as an eroded heightfield (stream-power valleys and gullies, strata benches aligned with the shader's beds, talus, rock outcrops), adaptively meshed (185k triangles in the eight original sectors, shared borders), Berms ground toe kept exact; Ward Desert Terrain V2 with new haze-shape controls (thinner far and high haze, high-sun tint) on SandstoneBasinV3. Old DesertBasin chunks inactive. Not yet accepted by Carl. |
