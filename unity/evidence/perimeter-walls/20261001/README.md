# Perimeter walls — evidence (1 October 2026)

Carl (30 Sep): "walls look too clean, maybe some parts of the wall have fallen." The perimeter walls are now an
old, battle-scarred, repaired stone defence on the shared Ward masonry (the stone of Vanguard Hall, the shops, the hill
and the tree beds). Sources and run order: `art/perimeter_walls_20261001/README.md`. Unity pass:
`Assets/AthenHill/Editor/PerimeterWallsPass.cs`. Not yet reviewed or accepted by Carl.

## What changed in the scene

- New root **Ward perimeter walls**: 87 prefab instances of 32 modules (`Prefabs/PerimeterWalls/`), 479 m of wall:
  south and north walls 120 m each, the +X rampart 40.3 m south and 28.3 m north of the District gate arches plus the
  1.6 m slot between them, the strip wall 88 m, the -X Berms walls 39.4 m and 41.5 m (`install.json`).
- Retired (inactive, not deleted): 126 old visuals — `AuthoredWorld/BLD_boundary_wall*`, `_coping*`, `_pier*` (34),
  `_recess*` (34), `_side`, `BLD_west_wall*`, `_coping*`, `BLD_wall_buttress*`, `_inset*`, `_signal*`,
  `BLD_berms_gate_wall_*` and the six `Wall shadow proxy` objects (`install.json` → `retired`). Render chunks rebuilt.
- Kept unchanged: every wall collider (`COL_BLD_boundary_wall*`, `COL_BLD_west_wall*`, `COL_BLD_berms_gate_wall_*`,
  `COL_BLD_boundary_side`), so the collapses and the breach stay blocked. Added: nine low convex colliders on the rubble
  cones (south collapse, Berms collapse and breach).
- 22 review cameras under "Perimeter wall review cameras" (16 from the first run, 6 story-beat close-ups added).
- Rollback: `rollback/before-perimeter-walls.unity` (the scene before the install).

`verify-saved-scene.json` (11:42, `-nographics`): installed and active, 87/87 modules prefab-linked, uniform scale,
0 missing materials, nothing retired still active, all kept colliders active, chunk fingerprint matches.

## Kit, triangles, LODs

| Kind (module) | LOD0 | LOD1 | LOD2 | shadow mesh |
| --- | --- | --- | --- | --- |
| NS 7 m bay (intact / repair / impact) | 30–38k | 3.3–4.2k | 1.4–1.8k | 106–166 |
| NS 7 m collapse / collapse_n | 63k / 55k | 4.8k / 4.4k | 1.2k / 1.3k | 160 / 154 |
| EX 5 m bay (intact / repair / impact / siege) | 32–42k | 5.0–6.5k | 2.0–2.5k | 130–190 |
| BW 5 m bay (intact / coping / repair / impact) | 16–20k | 1.5–2.2k | 0.6–0.9k | 34–70 |
| BW 5 m breach / collapse | 43k / 30k | 4.0k / 2.9k | 1.0k / 0.9k | 178 / 166 |

Totals over all 87 instances (never all on screen): LOD0 2.32M, LOD1 267k, LOD2 107k, shadow massing 8.4k
(`build-assets.json`, `verify-saved-scene.json`). LOD0 within ~16 m, LOD1 to ~45 m, LOD2 beyond (cuts from each
LODGroup's size at 60° FOV with the PC LOD bias 2). The stone casts shadows only through the ShadowsOnly massing mesh,
inset 9 cm behind the lit faces; fittings, repairs and rubble cast their own.

## Frame time (A/B)

Alternating runs of two pinned development builds made from one snapshot of the saved scene (walls root on / off, the
old wall visuals retired in both, so "off" is the walls' whole cost), 1920×1080, High preset, 13:00, 8 s profile per run
(`ab/`, `ab/summary.json`, `ab/conditions.txt`). RTX 3060 12 GB, OpenGL, render scale 100 %, VSync off in QA.

| Camera | On: avg fps / p50 / p95 / p99 / max (ms) | Off: avg fps / p50 / p95 / p99 / max | Δ p50 | Δ triangles |
| --- | --- | --- | --- | --- |
| cam_hill (wide) | 68.3 / 14.68 / 15.16 / 16.37 / 17.85 | 69.5 / 14.46 / 15.00 / 15.96 / 17.44 | +0.22 ms | +107k |
| cam_pw_south_lane (walls fill the frame, player height) | 153.4 / 6.32 / 7.46 / 7.71 / 10.17 | 169.9 / 5.72 / 7.04 / 7.28 / 8.78 | +0.60 ms | +257k |

Per-run fps: hill on 68.7, 67.9 / off 70.0, 69.0; south lane on 153.5, 153.2 / off 171.7, 168.0. GPU time: unavailable.
cam_gate runs were dropped: two off-arm runs were killed by the programme's VRAM watchdog (11.85 GB with the desktop),
leaving one on-arm run (158 fps) and no comparison.

## City loop

`cityloop/` (`$O/native.sh cityloop`, final development build of 09:59 containing the walls): **CITY LOOP PASS**
(spawn, the four NPC dialogues, Basic General trade, Lattice transition).

## Captures

- Native before (30 Sep 23:50 build, old walls): `native-before/` (23 cameras × 13:00, 20:30; `sheet-h*.jpg`).
- Native after (pw-ab-on build, final kit): `native-after/` (29 cameras × 13:00, 20:30; `sheet-h*.jpg`).
- `compare-before-after-h13.jpg`: matched pairs (south lane, rampart, north foot, south foot, outside the Berms wall,
  Berms south, the Ring grid, the District gate). `story-beats-h13.jpg`: the south collapse, the north collapse behind the
  Quantum Tube, the HESCO breach from inside and outside, the siege flank of the District gate, the rampart close-up.
- Editor iterations (MainCamera clone): `editor-before/`, `editor-after-1/` (self-shadowing bug), `editor-after-2/`,
  `editor-after-3/` (final story beats). `native-after-1/` is an intermediate native set (before the stepped-break fix).

Best before/after pairs (13:00): `native-before/cam_pw_south_lane-h13.00.png` → `native-after/cam_pw_south_lane-h13.00.png`;
`cam_pw_east_south`; `cam_pw_south_foot` (now the south collapse rubble); `cam_pw_outer_west` (Berms breach screen and
rubble outside); `cam_grid`.

## Layout check

`art/perimeter_walls_20261001/pw_validate.py` against `audit-before.json` (scene audit 07:14): 0 blocking overlaps
(nothing on a route, NPC point, landmark or collider). Remaining "visual" overlaps are rubble/sand touching Poly Haven
scatter rocks and shrubs outside the Berms wall, the maple/pine canopies over the Berms north pilasters, the rampart
buttresses at z 32 and 37 against the processing-hall ruin / Watchtower 3 bounding boxes (the old buttresses stood there
too), and sand pockets against tower legs.

## Scores (0–5, at player height and the wide views, 13:00)

| Category | Before | After | Notes |
| --- | --- | --- | --- |
| Composition / silhouette | 2 | 4 | merlons, piers, buttresses and breaks give the skyline rhythm; repetition still visible on long straight runs |
| Scale | 3 | 4 | 0.45–0.55 m courses, 2 m+ thick rampart reads; NS top 5.53 m (was 5.26) |
| Material detail | 1 | 3–4 | the Ward masonry at LOD0 (eroded arrises, chips, runoff, rust, scars); rubble cones and sheet screens are tiling textures |
| Lighting / depth | 2 | 3 | correct self-shadowing now; walls read darker than the old pale boxes, very dark at night (moonlight) |
| Density / storytelling | 1 | 4 | siege flanks, two collapses, the HESCO breach, repairs, stitched cracks, sand and weeds at the feet |
| Temporal stability | U | U | no moving walkthrough reviewed |

## Remaining defects (honest)

1. Close-range cost: +0.6 ms p50 where the walls fill the frame (above the ~0.5 ms guide; the wide view is +0.22 ms).
2. Night: the new walls are much darker than the old pale boxes under moonlight (cam_pw_south_collapse 20:30 is near
   black). No wall lamps were added; that belongs with the night-lighting stream.
3. The NS pier at x 49 pokes ~5 cm out of the rampart's outer face in the strip behind the arches (as the old pier did).
4. The rubble cones are a tiling debris texture on a smooth mound plus authored stones; close up they read as a heap of
   sand-coloured gravel more than masonry rubble. No scanned rubble was used.
5. Welded sheet screens are flat boxes (no corrugation geometry, no weld beads at LOD1+).
6. The crater bowls are flat-ish rubble planes behind knocked-out blocks; no partial (diagonally broken) face blocks.
7. Repetition: 6 instances each of intact a/b/c on the north/south runs; visible from raised views along a run.
8. LOD transitions and shadow pops were not reviewed in motion; no walkthrough video.
9. The "QUANTUM TUBE AUTHORITY" stencil decal on the rampart still projects, but onto the new block pattern it reads
   fainter than before.
10. The kit was reviewed at 13:00 and 20:30 only; sunrise/sunset not checked.
