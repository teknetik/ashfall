# Basic General neon sign integration, 29 Sep 2026 (t_196932d9)

Status: installed and technically checked. Visual assessment PENDING: Carl is the acceptance owner. No GTA6-parity or visual-acceptance claim is made.
Per Carl's direction, no further tests were run after the single bounded native pass below.

## Source and provenance
- Original GLB (unmodified): meshy/basic-general-sign-20260929/Meshy_AI_Neon_Command_Sign_0929072950_texture.glb
  46,180,560 bytes, SHA-256 3f77f2c733b62dfc450924e79bb729403236c253cdbb6056abaf8103e3a04dd1. Meshy task ID not recorded in the file.
- Source: 1 mesh, 1,241,878 triangles, 1.900 x 0.614 x 0.121 m. Lettering "BASIC GENERAL" and "OPEN" is legible (not gibberish).
- Source defect: dark rectangle inside the C of BASIC. Patched in the runtime albedo (fix_artifact.py); raw bakes retained.
- Runtime asset: relief baked (Blender/Cycles, bake_sign.py) to a 22-triangle plate with 4096x1320 albedo/normal/metal-gloss and 2048x660 emission maps. 0 Meshy credits spent.
- Trade-off: silhouette is a flat plate; frame relief, letter depth and OPEN plate depth are normal-map detail only.
- Details: meshy/basic-general-sign-20260929/README.md; inspection renders in source-inspection/.

## Installation
- Prefab: unity/AthenHill/Assets/AthenHill/Art/Phase1/BasicGeneral/Sign20260929/BasicGeneralNeonSign.prefab (URP Lit, emission 0.55, no collider, no light, no video).
- Placement (sign-installed.json): position (8.0, 2.72, 16.94), uniform scale 1.3 (lossy 1.3/1.3/1.3). Bounds 2.47 x 0.80 x 0.16 m.
- Five old sign renderers retired (disabled, not deleted; 12,432 tris): Sign_enamel_face, BASIC_GENERAL_sign, Open_indicator_housing, Open_indicator_face, Open_lettering. Old sign therefore recoverable by re-enabling them.
- Show Sources / Rebuild Render Chunks ran in the install pass. Scene saved and reopened (sign-verify-saved-scene.json): sign present, uniform scale, retired renderers 0 enabled, frontage colliders unchanged, 6 frozen gameplay colliders OK, chunk fingerprint matches, counter dressing present, Mira root at (8.0, 0.5, 15.8).
- Editor passes: Editor/BasicGeneralSignPass.cs, BasicGeneralSignReport.cs, BasicGeneralSignReport2.cs.

## Builds (both succeeded, 0 errors, 346 warnings, built from the uncommitted working tree over 0b4496ad)
- Development: /home/teknetik/code/ao2/unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64 (9,194,112,525 bytes)
- Release: /home/teknetik/code/ao2/unity/AthenHill/Builds/Linux/AthenHill.x86_64 (9,097,099,755 bytes)
- Scene SHA-256 after install: dfa130d5e795060dc4bfbd16c143e5b0d8444a7ac2acf2873fc5c4e4e320b4eb

Launch: cd /home/teknetik/code/ao2/unity/AthenHill/Builds/Linux && ./AthenHill.x86_64 -force-glcore -screen-width 1920 -screen-height 1080 -screen-fullscreen 0
Route: spawn at the west gate, walk the avenue, then south down the hill to Basic General at about x=8, z=19.

## Native checks actually performed (development build, real input, one launch)
- Stills: fixed-camera front, door and side-left at noon/dusk/night (after-native/*.png).
- Player-height views at 1920x1080 (after-playerheight-report.json): lane far (8.07, 23.95), street (8.00, 20.07), close (8.00, 19.12). Sign is visible and "BASIC GENERAL / OPEN" is readable in both street and close views; camera overlaps empty.
- Route and trade (mira-trade-route.json): walked spawn area -> stair -> avenue -> Basic General porch, reached all 11 waypoints with no stall. Bought flask (credits 25 -> 21, flask +1), sold scrap (credits 21 -> 22, scrap -1), closed modal, walked away.
- Development Player.log: no exception or shader errors (the only grep hits were GL extension names).
- Release build (release-native/report.json): launched, 1920x1080 window, renders (screenshot stddev 107.9), development bridge absent (QA folder empty), no exception lines, no development-build marker.

## Not done / remaining defects
- Visual acceptance not made; Carl to judge. In the noon shots the sign reads clearly and does not clip the roof beams, but sun/shade, dusk and night were captured only as stills and not scored.
- Flat-plate silhouette (relief baked to normals).
- Emissive orange lettering is 0.55 intensity; not tuned against the palette at dusk/night.
- Before/after matrix reused stale-144133 or stale-144342 partial baseline; no matched before/after comparison images, no MP4, no local render-cost measurement, no full Mira E-key interact from a scripted release run (trade exercised on the development build only).
- Render Chunk asset files regenerated (git shows Chunk_89_SignPaint deleted etc.); expected from the rebuild.

## Rollback
- rollback/before-basic-general-sign.unity (scene before the sign) and rollback/before-sign-saved-by-install.unity (SHA baseline 34d448cb...). Or re-enable the five retired renderers and disable the sign instance.
