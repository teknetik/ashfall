# District retrofit — 26 September 2026

Scene change: `Ward district retrofit` prefab instance + `Ward retrofit review cameras`
(`cam_retrofit_*`) added by `AthenHill.Editor.WardRetrofitPass.RunAll`; source record in
[art/ward_retrofit_20260926](../../../../art/ward_retrofit_20260926/README.md).
`pass.json` records colliders (88), practical lights (36) and triangles per group.
No existing object was moved, disabled or deleted; render chunks were not touched.

## Evidence

- `editor-before/` — Editor stills of the saved scene at commit 31720d5 (clock default hour).
- `editor-after/` — same cameras plus zone/close-up cameras after install (`review-shots.json`).
- `before-after.jpg` — west row, east row, Ring Gate axis, West Gate.
- Linux development player built successfully after install (batch `LinuxBuild.Development`).
- Decal lettering was mirrored in the first install and imported prop rotations were ignored
  (glTF quaternion mode); both fixed before the final captures.

## Walking mining droid

`mining-droid.json` records the import (legacy `idle` 3.2 s / `walk` 1.2 s, 60,706 tris,
10 bones) and route. `native-droid/` holds frames from the development player run windowed
through the QA bridge at `cam_retrofit_aquifer` (the window manager tiled it to 936×1040):
the droid trots the yard and turns at the corner; the player log has no exceptions.
That camera was afterwards moved clear of a utility pole (scene only; the build predates it).

## Not yet done

- Native 1080p route/city-loop checks (`tools/native_check.py`) and warmed traversal
  performance on the RTX 3060 — not run; they take over the desktop display.
- No acceptance scores assigned; Editor stills are look-development evidence only.
