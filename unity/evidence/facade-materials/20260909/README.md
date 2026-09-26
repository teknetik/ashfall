# Facade materials and damage refinement — 9 September 2026

This pass implements the user's three requested improvements on Field Supply
and Finery: more surface variation, correctly scaled fine relief, and less
angular damage. It retains the earlier accepted weathering motifs and usable
building envelopes. The [source record](../../../../art/facade_materials_20260909/README.md)
describes authoring, bakes, provenance and recovery.

## Authoritative state and baseline

`baseline.json` records the starting Git revision and saved scene hash, and verifies
that the existing development player's scene data matches the previous weathering
evidence. The matched before captures are in
`unity/evidence/building-weathering/20260909/after-native`. They are reused because
their build identity was verified, not merely because they look similar.
`before-scene.unity` preserves the immediate scene for recovery comparison.
`build-identity.json` records the revised scene, source export and both tested
native player identities. These qualify this working-tree snapshot.

`installation.json` records all 348 source mesh/material replacements, the 258
retained but disabled overlays, and unchanged gameplay/collision signatures.
`saved-import-check.json` confirms the reopened saved scene, fresh render chunks,
full 4K textures, linear normal/packed data, mip levels, streaming and anisotropy.
`original-lightmap-uv-check.json` confirms that no existing UV1 data was discarded.
No runtime gameplay code, engine version, graphics API or pipeline changed.

## Visual evidence

- `editor-review/`: initial Unity material review before building.
- `after-native/field_supply-captures.json` and `finery-captures.json`: completed
  matched 1080p capture plans, six views per building and the seven standard
  district views plus courtyard/door comparisons.
- `after-native/material-lighting.json`: fixed close views at 08:00, 12:00 and
  16:00 using the existing authored day/night system. Those views inspect light
  response; only the noon captures are the matched before/after comparison.
- `after-native/weathering-proximity.json`: real keyboard approaches, wheel zoom
  into first person, mouse look, camera overlap checks and the close walkthrough.
- `after-native/store-walkthrough.mp4`: the unmeasured traversal warm-up only;
  recording stopped before timing the measured route.

The native images show faded/mottled plaster and small surface failures, rough
exposed mineral areas, more varied stone and textured shutter paint/rust. The
former polygon flakes and thick black fracture ribbons have been removed from
the visible scene. Actual geometry retains larger losses and worn edges; fine
relief lives in the normal maps. Large construction planes remain flat after
correcting an intermediate Blender shading defect.

These are local improvements to the two requested facades. The broader district,
lighting, character animation and cloth retain their existing quality limits.
The 4K material tile is shared, so some repetition remains possible over long
walls; the existing localized deposits and distinct damage placements break it up.
No user acceptance of this subsequent revision is inferred from acceptance of
the earlier concept or weathering pass.

## Native qualification

`development-build.json` and `release-build.json` report successful builds with
zero build errors (one and three warnings respectively). Existing warnings remain
in `editor.log`. `authoring-processes-closed.json` verifies that the Blender and
Unity processes started for this task had actually stopped before this timing run.

`verification.json` records the completed checks and measured results. The actual
RTX 3060 / i9-10850K host, NVIDIA 595.84 driver, OpenGLCore API, native 1920×1080,
render scale 1, four-sample MSAA and nine-actor roster are recorded by the player.
The uncapped walking route and modal interaction timing are reported separately.
Unavailable counters remain unavailable; submitted triangles include render
passes and are not a visible-triangle budget.

`geometry-cost.json` records the net increase of 141,964 source triangles after
replacing the selected meshes and hiding the old overlays. Texture and mesh
memory cost is assessed in the native results. Timing from the earlier pass had
an Editor process resident, so it is not a controlled before/after performance
comparison with this run.

Measured traversal: 134.47 s, 163.84 FPS average; p50 5.05 ms, p95 11.44 ms, p99 13.08 ms, maximum 206.09 ms (one hitch). The initial interrupted measurement is preserved separately; the completed repeat follows the same verified warm-up. Both first-person approaches, all 29 city-loop checks and the release smoke passed. See `verification.json` for honest local visual scores and remaining shade/frame-pacing defects.
