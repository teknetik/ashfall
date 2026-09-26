# Ward quality iteration — 26 September 2026

**Paused at the user's request. The district does not meet the requested contemporary AAA target.**
Start with [HANDOFF.md](HANDOFF.md) for the final source/build/process state,
unverified work, known staged-script error and suggested resumption order.
Independent review still prefers the official ARK references. A candidate winning
an internal comparison is an improvement, not final art acceptance. No whole-game
quality, complete gameplay or performance qualification is claimed.

This work continues the current saved Unity district, including the later street
and orange-tree additions. It does not regenerate the city, revive the retired
browser game, change the graphics API or re-enable rejected district shops. The
large pre-existing working tree is retained; evidence identifies the actual build
rather than treating the repository commit as a clean source baseline.

## Work and independent review

- Gameplay specialist: player/camera presentation interpolation, persistence of
  Reduced Motion, source review, EditMode checks and native timing diagnostics.
- Rendering specialist: URP ground/grass light and depth-pass corrections,
  source-preserving leaf-edge repair, and controlled leaf-lighting auditions.
- Independent visual critic: candidate labels concealed until preferences and
  scores are written; defects and rejections retained.

The critic did not receive candidate mappings for the anonymous shadow and leaf
reviews. Cross-game identities remain recognizable, and ARK promotional settings
are unknown. These are independent visual preferences, not a scientifically blind
cross-game experiment or equivalent-hardware comparison.

## Verified so far

- Live Unity 6000.6.0f1 EditMode suite: **50 passed, 0 failed, 0 skipped**.
  See [the final raw test results](movement/proxy-reparent/final-editmode-results.json) and [movement/README.md](movement/README.md). This is
  source/build evidence; real-input native motion review is outstanding.
- Four Linux development builds succeeded. The first diagnostic run exposed a
  JSON serialization defect in the new cascade snapshot; it was corrected and
  rebuilt. That failed run remains in `candidate-native/`.
- Current build 04 succeeded in 53.46 seconds, with 0 errors and 346 warnings.
  See `development-build-04.json` and `candidate-build-04-identity.json`.
  Build 03 evidence in `candidate-native-03/` uses RTX 3060 12 GB, i9-10850K, NVIDIA 610.57.04,
  OpenGLCore, full 1920×1080, render scale 100%, MSAA 4, all nine actors,
  VSync off and uncapped timing. The Editor remains open. Background rendering
  is an explicit development-only static-capture option.
- The release build succeeded with 0 errors/352 warnings in 153.38 seconds.
  Its headless negative-control check stayed alive and ignored both QA flags,
  leaving the diagnostic command untouched and emitting no bridge files.
  See `release-build-01.json`, `release-build-01-identity.json` and
  `release-gate-01/report.json`. This gate does not verify visible release play.
  All 352 warnings were exported; most are pre-existing Sentis compute variants.
  The direct build menu now also copies the existing UI font licence to output.
- The release subsequently rendered three nonblank, full 1920×1080 captures from
  its own window on NVIDIA OpenGL 4.5. No input or focus changes were sent;
  diagnostic flags remained ignored, and the owned process exited cleanly.
  See [the visible release report](release-static-01/report.json). This verifies
  static release rendering, not gameplay input, motion or frame-time targets.
- The saved scene change is limited to parenting the existing player shadow proxy
  beneath the interpolated visual. `scene-change-scope.json` verifies the original
  scene equals the pre-proxy backup; its three hierarchy hunks preserve all earlier
  scene work. No collision, gameplay root or route was replaced.
- `native-shadow-verified-viewport/` contains 18 full-viewport 1920×1080 captures
  at matched saved cameras/daylight: 18 m/one cascade versus 96 m/four cascades.
  Daylight is frozen; actors, dust and foliage remain animated.
- `native-current-build04/` contains twelve full 1920×1080 views of the saved
  build-04 leaf material, district, player and guard. An earlier build-04 launch
  lacked a display and produced an invalid offscreen capture; its failure is
  retained in `candidate-native-04/capture-limitations.json`. The launcher now
  requires an explicit or inherited X display before creating a player process.
  A later viewport drift aborted `tree-shadow-coverage-04/` before samples;
  the owned window was resized with an explicit absolute size and revalidated.

The earlier 18 native images inside `candidate-native-02/` have a black top strip
and clipped HUD. Hyprland's tiled window supplied 1896×1040 pixels while Unity
reported the requested 1920×1080. Floating and sizing only the test window fixed
the backbuffer. See its `capture-limitations.json`; those earlier images are not
normal-UI or full-viewport acceptance evidence.

## Current art findings

The anonymous shadow review preferred longer shadows in both wide views and tied
the close hero view. The first timed hill comparison nevertheless fell from about
75 FPS to 42 FPS with 96 m/four cascades. That candidate cannot become the default
on this evidence. Static diagnostics are retained under `static-shadow-timing-01/`;
they do not replace a warmed moving route or establish GPU milliseconds when the
GPU counter is unavailable.

The leaf repair preserves the original 4096² alpha and opaque RGB values and
extends neighboring leaf color into pale partial-alpha edges. Original maps are
unchanged. The critic preferred the repaired version in all four Editor views,
but rejected dark, poorly separated shaded clusters and noisy fine edges.
See [critic/anonymous-leaf-review.md](critic/anonymous-leaf-review.md), its locked
scores, the mapping, and `art/quality_20260926/tree-edge-padding-v1/` at repo root.
The repaired map is installed in build 03, with the original map and material
backup retained. `native-leaf-shade-v2/` contains twelve separate-frame native
captures with MSAA 4, full texture mip 0 and three-second settling. Texture
streaming is globally disabled, so desired mip −1 is not a residency failure.
The failed first capture attempt is retained in `native-leaf-shade-v1/`.

The native critic slightly preferred ambient transmission .15/.25 over zero in
three close views and tied the hill view. Dense dark clusters remain unresolved,
with no whole-point quality score increase. The source material now uses .15, the smaller setting tied for the same modest
benefit. Build 03 stored zero; its diagnostic captures tested .15 explicitly.
Build 04 and release 01 now contain the saved value; current-build native capture
and qualification are recorded separately from build 03 diagnostic overrides.
A normal material Inspector now exposes wind and both transmission controls;
Unity resolved its GUI, preserved the existing Lit keywords and reported no
shader messages. See `tree-inspector-apply-result.json`. `critic/anonymous-native-leaf-shade-review.md`
and its locked JSON precede disclosure of the randomized labels. An earlier
Editor batch produced an unexplained inconsistent hill control and is explicitly
inconclusive; it cannot select the native material value.

`tree-shadow-timing-03/` records 18 current-build static intervals with original
versus preserved LOD1 shadow-only geometry. Visible geometry is unchanged. At
48 m/two cascades, reduced shadows reached 63.28 FPS/p99 17.08 ms on the hill and
60.96 FPS/p99 17.67 ms on the avenue. Both still miss the p99 target. Longer shadow
settings and cheaper shadow geometry remain development auditions, not defaults.
GPU timing and draw-call counters were unavailable, not zero-cost. These intervals
are not a warmed moving route and do not qualify the build.

Build-04 shadow coverage was stopped after its control fell to about 10 FPS
(`tree-shadow-coverage-04b/`), despite verified 1920×1080 and similar submitted
geometry to the earlier 74 FPS control. The cleanup failure and successful
subsequent restoration are retained. `ambient-cost-04b/` compared the same view
at ambient transmission .15 and zero: both remained about 10 FPS, so this
setting does not explain the slowdown in that run. Cause remains unresolved;
these results cannot promote a new shadow profile.

A fresh build-04 process recovered to 69.03 FPS average, but p99 was 31.51 ms
with four hitches above 33 ms over 10.02 seconds. It still fails qualification;
the earlier slowdown's exact cause remains unproven. See
`fresh-control-04/report.json`. No real-input test began before the user stopped
the work. The owned player was subsequently closed with clock/camera restored,
no pending command and no held input. Recovered Blender and its private Xvfb
server were also closed after preserving the complete authored source.

Remaining broad defects include repetitive facades, empty paving, inconsistent
close-range material detail, character and animation limitations, vegetation
integration and temporal stability. The ARK reference is still visibly stronger.

The ground audit also found that `Paving_NormalSource.png` is byte-identical to
the colour texture. Its normal importer turns colour variation into surface
relief. Original source files remain untouched. The Blender-authored joint height,
normal and roughness candidate `periodic-v2` is now saved outside Unity and ready
only for a controlled native audition. The critic's pinhole cleanup was applied;
small periodic-edge artifacts still need native grazing-light inspection.
No paving candidate or planned ground camera is installed. The unexecuted import
request has a known inaccessible-API compile error documented in the handoff.
See [the ground audit](ground-audit/README.md) and
[mask criticism](critic/paving-mask-v1.md).

## Evidence still required

The desktop session was locked during the earlier attempts; no session lock was
bypassed. It was observed unlocked later, and native input verification can now
proceed when the user requests continuation. No input test began after unlock.
A temporary,
private Xvfb server was extracted from a checksum-verified Arch package into
`/tmp`, without installing packages or changing system configuration. Its
llvmpipe renderer produced roughly 0.5 FPS; original controls, city-loop and route
checks failed with recorded timing/state limitations. Two GPU-backed Zink trials
also failed their renderer gate with repeated allocation errors, including a
black capture. They are not accepted input, art or performance evidence. All four
trial players were quit. See [isolated attempt log](headless-functional/ATTEMPTS.md).
A runtime-UI-bound correction for a stale hotbar test coordinate is staged;
its assertions and timings are preserved, but it still needs a valid native run.

Pending checks include stairs/thresholds/jumping, camera collision and first-person
zoom, modal input blocking, conversations/trading/travel, Reduced Motion relaunch,
moving foliage/LOD/shadows, saved/reopened scene,
and a warmed representative 1080p traversal with average ≥60 FPS and p99≤16.67 ms.
Static-camera timing, compilation and still images cannot substitute for them.

Original scene/settings and build identity records are in `original/` and
`baseline-identity.json`. The previous native build is recoverable at
`unity/AthenHill/Builds/.archive-quality-20260926-original`. Do not attribute older
route or performance passes to the new build.
