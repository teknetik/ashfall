# Phase 3 — authored city integration

2026-09-07. The Blender world is integrated and its movement/collision gate
passes. This milestone accepts the authored asset pipeline and city layout;
final reference-match and target-laptop qualification remain Phase 6 gates.

## Assets and ownership

Live Blender MCP authored the blockout, tree, twin west arches, shops and Basic
General, Vanguard Hall, Lattice Jack, Ring Gates, prop kit and distant cliffs in
that order. Versioned scenes and repeatable authoring scripts are in `blender/`.
The source inputs use metres, Three Y-up/north -Z, converted to Blender Z-up.
Texture paths in saved scenes are relative. No marketplace or extracted assets.

`public/assets/world.glb` has 64,178 render triangles, nine materials, six
embedded generated textures and 262 separate COL proxies. Its manifest enables
all eight landmark groups. The runtime batches render geometry into ten groups;
keeps the ground halfspace; removes all replaced greybox geometry and collision;
and extracts final world-space box/cylinder proxies before creating physics.

The generated texture source resolution is 1254 square, including native RGBA
foliage. This is not a claim of 2k source detail. Original images, prompts and
provenance are retained in `refs/materials/`. Alpha-tested foliage casts cutout
shadows. The daylight environment is a single prefiltered analytic sky map,
with one sun and hemisphere fill, no GI.

The importer validates manifests, tags, transforms, material data and collider
shapes. Ownership cleanup covers shared textures/ImageBitmaps, late load
completion and HMR shutdown. Explicit time changes rebake the environment;
normal render frames do not. The native GPU exercised 16→15→16 without errors.

## Verification

- Production TypeScript/Vite build passes. The single JS bundle still raises
  Vite's size advisory (about 3.51 MB raw / 1.27 MB gzip); release splitting and
  loading presentation remain tracked for Phase 7.
- Full headed Chromium/Metal regression: `tools/phase3-support/runs/2026-09-07T09-59-38.809Z-14868/report.json`.
  Real uninterrupted 54.9-second gate→hill→Ring Gate→Lattice Jack route,
  880 checked movement samples, no teleports, falls or penetration.
- Shop stage/steps, gate tunnel, camera obstruction/recovery, wall slide,
  blur/release, pause/reset and touch controls pass. Zero application, page or
  network errors. Six fixed 1080p captures plus responsive evidence are saved.
- That route build measured 120 fps, 28 draws and 113,177 rendered triangles
  on an Apple M4 Max. Counts include shadows. Subsequent tree/cliff changes
  preserve collision; final geometry captures and equivalence are recorded in
  the follow-up QA report linked from `docs/progress.md`.
- Seven focused lifecycle/environment tests pass with actual Three resource
  objects and controlled loading/GPU fixtures (`npm run verify:lifecycle`).
- Historical Phase 1 captures and reports remain unchanged.

## Art review and remaining final gates

All six Blender cameras were rendered after each completed asset stage. The
independent critic accepts Phase 3 authored-world readiness. Geometry-only
reference scores are hill 3/5, avenue 3/5 and gate 4/5. They are not final beauty
scores. The revised tree has connected secondary forks and varying leaf sprays;
the revised background has steep broken cliff tops rather than tiered cones.

Phase 6 must broaden the tree's low lateral canopy, replace the flat green
platform appearance with a collision-consistent grassy knoll, vary selected
shop upper profiles, improve bark scale/roughness, and deepen golden-hour sky,
lighting and material contrast. Fixed-camera transforms stay recorded and
unchanged. Hill/avenue/gate palette, silhouette and light must reach at least
4/5 before final acceptance. NPCs, verbs, final HUD and audio are still pending.

Native M4 Max performance is evidence for this machine, not a medium-laptop
qualification. The 58–60 fps / 80 draws / 250k triangles final contract remains.
