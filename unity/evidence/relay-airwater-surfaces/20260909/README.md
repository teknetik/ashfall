# Relay and Air + Water surfaces — 9 September 2026

This is the second slice of the user's expanded facade-material goal, following
the verified Field Supply/Finery pass. The [source record](../../../../art/relay_airwater_surfaces_20260909/README.md)
describes the live Blender authoring, full-resolution material reuse and recovery.

`baseline.json` records the immediately preceding saved scene and tested player
identity. The matched before views are retained in
`unity/evidence/facade-materials/20260909/after-native`, with
`relay-before-captures.json` and `air-water-before-captures.json`. These were
captured from that exact native build before modifying either shop.

`installation.json` records 479 source mesh/material replacements, 16 added
substrates, 14 localized projectors and unchanged gameplay/collision signatures.
`geometry-cost.json` records source triangle counts and the absence of new
textures. The scene was saved and reopened before `editor-review/` captures.
Those images show material placement in the existing lighting; native captures
and real-input verification remain the acceptance evidence.

The production boundary remains native Linux Unity 6000.6.0f1, URP 17.6 and
OpenGLCore. No game logic, input behavior, graphics pipeline, API or dependencies
are changed. All original source and rejected assets remain recoverable.

## Final native verification

`verification.json` records completed checks against `build-identity.json`.
Both Linux players built successfully with zero errors (development: three
warnings; release: one). The saved scene reopens with fresh render chunks.
`consistency-checks.json` confirms unchanged gameplay assemblies and package
files, the same scene in both builds, and a saved scene hash matching the build.
Blender and both Unity sessions were closed before launching the native test.

The measured, uncapped 1920×1080 traversal used the RTX 3060 / i9-10850K host,
NVIDIA 595.84, OpenGLCore, render scale 1, four-sample MSAA and all nine actors.
All 41 route destinations passed after a full unmeasured warm-up.

| Walking measurement | Result |
| --- | --- |
| Duration | 134.64 s |
| Average FPS | 166.92 |
| p50 / p95 / p99 | 5.03 / 11.44 / 15.40 ms |
| Maximum frame | 24.38 ms |
| Frames over 33 ms | 0 |
| Current average/p99 target | Passed |

Modal interactions were measured separately: 29.50 s, 213.94 FPS average,
p99 14.16 ms. One frame in the Grid/Lattice state took 213.07 ms; it remains
recorded rather than hidden by the walking result. All city-loop assertions
passed: dialogue, objectives, modal input, atomic buy/sell, Lattice destinations,
Ring Gate's offline response, pause, inventory, notes and settings. The native
release rendered and responded to real keys, with its development bridge absent.
The runtime logs contain no observed exceptions or shader errors.

RAM during warm-up was approximately 1.89 GiB RSS, with 2,836 MiB attributed to
the native process by NVIDIA and 3,828 MiB used across all GPU processes. This
is a point observation, not a traversal peak. Per-texture residency and GPU
frame time are unavailable. Submitted triangle counters include render passes;
they are not visible geometry counts or a new fixed art budget.

## Visual comparison

- `before-after.jpg`: matched Relay/Air + Water door views; original full frames
  and their camera/settings records remain in the capture reports.
- `field-finery-before-after.jpg`: earlier weathering baseline versus the final
  combined build, showing the first two facades remain updated.
- `first-person-detail.jpg`: cropped native detail views; originals are under
  `after-native/first-person-*.png`. Three first-person positions passed real
  movement, scroll zoom, mouse look and camera-overlap assertions.
- `lighting-review.jpg` and `after-native/material-lighting.json`: nine fixed
  native views at 08:00, noon and 16:00. Only noon is the matched baseline light.
- `after-native/store-walkthrough.mp4`: unmeasured warm-up, with the encoder
  stopped before timing. `relay-airwater-first-person.mp4` records close approaches.

The plaster, stone and coated hardware read as different worn materials, and
the larger spalls have recessed aggregate and irregular edges. Local deposits
follow services and drainage. The visual assessment in `verification.json`
scores the local surfaces, scale and construction at 4/5. Lighting remains 3/5:
deep morning/canopy shade still conceals some detail. Shared tile repetition
and the single Lattice interaction hitch remain limitations. These results
qualify this focused implementation and do not imply user acceptance or whole-game
AAA fidelity. The banked usage reset was not needed.
