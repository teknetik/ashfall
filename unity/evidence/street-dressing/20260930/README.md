# Street dressing — evidence, 30 September 2026

Source and method: [art/street_dressing_20260930](../../../../art/street_dressing_20260930/README.md). Working tree on
`main` after 417b7a9-era commits, with the uncommitted north-avenue and courtyard-tree work also present (same scene file).
Reference machine as recorded by the lookbook runs (Linux, RTX 3060 host, OpenGL core, 1920×1080, saved High preset,
TAA). Not yet accepted by Carl.

## Files

| Path | What |
| --- | --- |
| `audit.json` | Read-only scene inventory (renderers, colliders, markers) used for the layout (`StreetDressingAudit.cs`). |
| `baseline/` | Native lookbook of the old props before any change (13:00; old salvage cameras). |
| `audition-1/`, `audition-solo/`, `audition-solo2/` | Editor auditions of the kit in scene lighting (rows; one prop at a time from front and back). |
| `editor-before/`, `editor-after/`, `editor-after2/`, `compare-*.jpg`, `after2-sheet.jpg` | Matched editor captures from the 22 `cam_sd_*` review cameras before the install, after pass 1 (119 props) and after pass 2 (145 props, decals, bigger door pots, reworked sacks). |
| `native-1/` | Native lookbook, 13:00 and 20:30, pass 2 before the LOD/shadow optimisation, with frame-time profiles at `cam_hill`. |
| `native-final/` | Native lookbook of the final state (all `cam_sd_*` and the two tree-bed cameras, 13:00 and 20:30, contact sheets). |
| `ab-off-*`, `native-profile-*`, `ab-on2-*` | A/B frame time (the dressing root switched off in a separate build, then on, before and after optimisation). |
| `cityloop-native/`, `cityloop.out` | Real-input city loop on the final build: **CITY LOOP PASS** (spawn, walk, four conversations, Basic General trade, Lattice). |
| `install.json`, `verify-saved-scene.json`, `build-assets.json` | Install record (105 objects retired, 4 renderers hidden, 145 placed, 41 decals (cluster-based since the night review)), saved-scene verification, kit build (68 props, 0 unmapped materials). |
| `rollback/before-street-dressing.unity` | The scene before the install. Restoring it also needs the render chunks rebuilt (they were rebuilt without the retired props). |

## Verification of the saved scene

145 prefab-linked instances in 30 vignettes, 0 missing materials, 86 box colliders, 13 NPC sit points, 22 review cameras;
no retired object still active; the four slab renderers off; **render-chunk fingerprint matches** (no stale sources) and
the development build passes the stale-chunk guard.

## Frame time (native, 13:00, 8 s uncapped samples at a fixed camera)

| View | Dressing off | Pass 2, first build | Pass 2, optimised (final) |
| --- | --- | --- | --- |
| `cam_sd_avenue_east` | 59.8 FPS · p50 16.66 · p99 18.17 ms | 57.7 · 17.26 · 20.13 | 59.4 · 16.76 · 19.12 |
| `cam_hill` | 66.9 · 14.93 · 16.44 | 63.6 · 15.64 · 17.66 | 66.5 · 14.97 · 16.97 |
| `cam_sd_east_yard` (props fill the view) | 115.3 · 8.63 · 9.96 | — | 105.7 · 9.49 · 11.12 |

The first build cost ~0.6–0.7 ms median at the wide views. Optimisation (LOD1 at 20 % instead of 32 %, Meshy LOD1 18 %,
earlier LOD switches and culls, shadows only from LOD0 except pieces over 1.2 m, decal draw distance 30 m) brought it to
~0.04–0.1 ms at the wide views and ~0.9 ms where the props fill the frame. The p99 at `cam_sd_avenue_east` (18.2 ms
without the dressing) and `cam_hill` (16.4–17.0 ms) is above the 16.67 ms target with or without this work: the district
is not frame-time qualified at 13:00 from those views (the hill pass measured the same range this morning). GPU time is
unavailable in these runs (reported as null, not zero).

## Remaining defects and notes

- The pale grain sacks are tinted hessian over a cool linen scan; at distance they still read slightly grey.
- The Meshy handcart has four wheels (asked for two); kept, it reads as a cart.
- Fire barrel has no fire or light yet (a night-life touch for the crowd pass).
- Texture weight: the kit adds ~350 MB of source maps to the repository (2k base/normal copied unchanged; masks 1k/2k),
  in line with the hill pass. Build-side sizes are capped at 1k for hand-sized props by the importer.
- Litter and decals are deliberately sparse ("lived in, not messy"); density is easy to raise per vignette in `layout.py`.
