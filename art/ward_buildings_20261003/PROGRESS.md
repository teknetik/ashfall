# Ward buildings (3 Oct 2026) — progress log

Resume notes for another session. Brief: replace the Ward buildings that still need replacing (AUDIT.md ranks them).
Wrappers: `$O=/home/teknetik/.local/state/ward-programme` (`$O/unity.sh`, `$O/blender.sh`); Unity pass
`Assets/AthenHill/Editor/WardBuildingsPass.cs`; layout `layout.json`; Blender `author_buildings.py -- <key>`;
review renders `review_buildings.py -- <Model> views=...`; contact sheets `sheet.py`. Run order in README.md.
No player builds / native tests here (the main session runs the combined batch).

## Done (all installed in the saved scene, verified -nographics: 0 missing materials, prefab linked, chunk
## fingerprint matches, retired groups inactive, 0 route/NPC/landmark marker conflicts)
- 22:39 scene audit + lookbook sheets + 6 editor audit captures → `AUDIT.md`.
- Concepts (Codex image_gen): nanofab, tower, hall, aquifer (`concept/*_concept_v1.png`, prompts beside them).
- 23:20 **Nanofab 2** (rank 1) — `README_nanofab.md`, cameras `cam_wb_nanofab_*`.
- 23:35 **Watchtowers ×4** (rank 3) — `README_watchtower.md`, cameras `cam_wb_tower_*`.
- 23:28 **Processing 11 ruin** (rank 2) — `README_hall.md`, cameras `cam_wb_hall_*`.
- 00:10 **AQUIFER 3** (rank 4) — `README_aquifer.md`, cameras `cam_wb_aquifer_*`.
- 23:59 **Quantum Tube nodes + conduit** (rank 5) and **container homes** (rank 6) — `README_tube_and_homes.md`,
  cameras `cam_wb_tube_*`, `cam_wb_home_*`.
- 00:05 stencils made light (painted, no bevel): −70k LOD0 triangles across the set; hall windows now round-arched with
  voussoir rings (broken where the wall top fell); nanofab process lines up into the module.
- 00:14 final verify: all 10 roots installed and active, 0 missing materials, 0 marker conflicts, chunk fingerprint
  matches; collider AABB overlaps only where the west towers' taluses meet the Berms wall colliders (both solid).
- 00:20 rank 8 (shop retrofits layer) checked with 6 captures: nothing floats.
- Evidence JSON: `unity/evidence/ward-buildings/20261003/` (build-assets, install, verify-saved-scene, rollback copies).

## Round two (3 Oct, 02:15–) — see README_round2.md
- 02:20 defects judged from the on2 native lookbook; extra found: `cam_wb_aquifer_market` inside a market cloth.
- 02:25 four watchtower variants (A hip / B corrugated / A gable / B canvas, damage on each tower's free face, numbers).
- 02:27 cylindrical UVs in the masonry kit (opt-in) + WB_Cyl*/WB_Tank* sheet-steel paints (VH_Paint's streaky map was
  the cause of both the cylinder streaks and the dark tanks); conduit hatches on both sides.
- 02:27 Processing 11 salvage works (scaffold, tarp, floodlight, pallets, cordon, permit board, shear legs, skip, steel, bench).
- 02:33 first Unity batch blocked by another session's in-progress script edit (FirstPersonRifleView.cs compile errors);
  re-run 02:45 after it cleared.
- 02:37 audit re-check → West Gate bastions replace the retrofit `Gate defences` at the spawn (Lattice hoop left, reason
  in README_round2.md).
- 02:46 build + reinstall watchtower/hall + install gatebastion + cameras + verify: all roots installed, 0 missing
  materials, prefab links complete, all lights on the circuit, chunk fingerprint matches, retired groups inactive.
- 02:51–03:05 editor captures (review2/), fixes (south bastion moved 0.35 m off `qa_motion_wall`, softer gabion mesh,
  ochre tarp, lighter bastion/hall props), view budget (`round2/view-budget.json`).
- Edit Mode: 254/255 — the one failure is `FPHandsV2Tests.ViewModelUsesTheGripHandsAndHidesTheOldArms` ("Sequence
  contains more than one element": the scene now holds two FirstPersonViewModel components), from the parallel
  first-person view-model work, not from this pass (no Ward building contains that component).

## Next (if time / next session)
- Rank 7 Lattice hoop: gameplay object from render-chunk sources (needs ShowSources → retire → Rebuild chunks and a
  Lattice-transition check); consider a Meshy hero piece. Still open after round two.
- Hydroponics pump tanks (inside `Ward hydroponics/Retrofit planters and tank fittings`, a mixed retrofit mesh): plain
  grey/rust cylinders; could take the AQUIFER tank treatment.
- Round two gaps: README_round2.md "Known gaps".

## For the main session's combined native batch (round two additions)
- Lookbook the 15 new `cam_wb2_*` cameras plus `cam_wb_tower_*`, `cam_wb_hall_*`, `cam_wb_aquifer_market/tanks`,
  `cam_wb_nanofab_east`, `cam_wb_tube_span_w` at 13:00 and 20:30; A/B at `cam_gate` / `cam_hill` / the apron views
  (new LOD0: towers 59–72k each, hall 162k (+20k) + props, two bastions 34k + ≈62k props each; +3 night-only lamps).
- City loop: the spawn apron gained the two bastions (south one 0.35 m from `qa_motion_wall`); walk from the West Gate
  spawn north and south along the rampart and confirm nothing snags; range tutorial unaffected.

## For the main session's combined native batch (round one)
- Lookbook every `cam_wb_*` camera (35) at 13:00 and 20:30; A/B vs the previous batch build (new LOD0 meshes:
  nanofab 119k, hall 142k, aquifer 103k, 4 towers 64k each, 2 nodes 19k, 9 conduit bays 3–7k, 5 homes 6–8k;
  +21 clocked lights (wall lamps, searchlights, porch lights), 4 always-on interior/status lights).
- City loop + range tutorial (no routes changed; the mining droid patrol passes 1.25 m in front of AQUIFER 3).

## Found on the way (not this pass's to fix)
- `WS_LedCyan` (Art/WardShops/Materials) has lost its `_EMISSION` keyword (m_ValidKeywords empty, lightmap flags 0):
  the Tool Exchange display LEDs do not glow. This pass uses its own `WB_LedCyan`/`WB_ScreenCyan`.
